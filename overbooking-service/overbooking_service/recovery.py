import logging
from datetime import datetime, timedelta
from zoneinfo import ZoneInfo

from sqlalchemy import exists, select
from sqlalchemy.exc import IntegrityError
from sqlalchemy.orm import Session

from noshow_db.models.core import Appointment, Slot
from noshow_db.models.service import Message
from overbooking_service.config import AbTestSettings, ReminderSettings
from overbooking_service.events import schedule_messages
from overbooking_service.kpi import as_utc
from overbooking_service.schemas import AppointmentBooked

logger = logging.getLogger(__name__)


def recover_lost_bookings(
    session: Session,
    now: datetime,
    lookback: timedelta,
    timezone: ZoneInfo,
    reminders: ReminderSettings,
    ab_test: AbTestSettings,
) -> int:
    """Schedule messages for recent future appointments that have none; return how many."""
    candidates = session.scalars(
        select(Appointment.id)
        .join(Slot, Slot.id == Appointment.slot_id)
        .where(
            Slot.start_at > now,
            Appointment.created_at >= now - lookback,
            ~exists().where(Message.appointment_id == Appointment.id),
        )
        .order_by(Appointment.id)
    ).all()

    recovered = 0
    for appointment_id in candidates:
        # The row lock makes a cancellation wait, so its event finds the new messages
        row = session.execute(
            select(Appointment.patient_id, Slot.start_at)
            .join(Slot, Slot.id == Appointment.slot_id)
            .where(Appointment.id == appointment_id)
            .with_for_update(of=Appointment)
        ).first()
        if row is None:
            # Cancelled since the search
            session.rollback()
            continue
        patient_id, start_at = row
        booking = AppointmentBooked(
            appointment_id=appointment_id,
            patient_id=patient_id,
            # Texts show the clinic's local time, as in the booked event
            appointment_start=as_utc(start_at).astimezone(timezone),
        )

        schedule_messages(session, booking, now, reminders, ab_test)
        try:
            session.commit()
        except IntegrityError:
            # The booked event arrived meanwhile and scheduled the messages
            session.rollback()
        else:
            recovered += 1

    if recovered:
        logger.info("Lost booked events recovered: %d", recovered)
    return recovered
