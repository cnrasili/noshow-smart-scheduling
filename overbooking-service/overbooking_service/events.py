from datetime import UTC, datetime, timedelta
from typing import Annotated

from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy import select, update
from sqlalchemy.exc import IntegrityError
from sqlalchemy.orm import Session

from noshow_db.models.service import Message
from overbooking_service.config import ReminderSettings
from overbooking_service.dependencies import get_now, get_reminder_settings, get_session
from overbooking_service.messages import Kind, Status, render
from overbooking_service.schemas import (
    AppointmentBooked,
    AppointmentCancelled,
    CancelledMessages,
    ScheduledMessage,
    ScheduledMessages,
)

router = APIRouter(prefix="/events")


def _scheduled(messages: list[Message]) -> ScheduledMessages:
    return ScheduledMessages(
        messages=[
            ScheduledMessage(kind=m.kind, send_at=m.send_at, status=m.status) for m in messages
        ]
    )


def _existing(session: Session, appointment_id: int) -> list[Message]:
    return list(
        session.scalars(
            select(Message).where(Message.appointment_id == appointment_id).order_by(Message.id)
        )
    )


@router.post("/appointment-booked")
def appointment_booked(
    body: AppointmentBooked,
    reminders: Annotated[ReminderSettings, Depends(get_reminder_settings)],
    now: Annotated[datetime, Depends(get_now)],
    session: Annotated[Session, Depends(get_session)],
) -> ScheduledMessages:
    if body.appointment_start <= now:
        raise HTTPException(422, "appointment_start must be in the future")

    # Repeated events do not create duplicate messages
    existing = _existing(session, body.appointment_id)
    if existing:
        return _scheduled(existing)

    start = body.appointment_start.astimezone(UTC)
    send_times = {Kind.CONFIRMATION: now}
    reminder_at = start - timedelta(hours=reminders.hours_before)
    if reminder_at > now:
        send_times[Kind.REMINDER] = reminder_at

    messages = []
    for kind, send_at in send_times.items():
        # Texts use the appointment time as sent by the booking application
        subject, text = render(kind, body.appointment_start)
        messages.append(
            Message(
                appointment_id=body.appointment_id,
                patient_id=body.patient_id,
                kind=kind,
                email=body.email,
                subject=subject,
                body=text,
                appointment_start=start,
                send_at=send_at,
                status=Status.PENDING,
                attempts=0,
            )
        )
    session.add_all(messages)
    try:
        session.commit()
    except IntegrityError:
        # A concurrent event created the messages first
        session.rollback()
        return _scheduled(_existing(session, body.appointment_id))
    return _scheduled(messages)


@router.post("/appointment-cancelled")
def appointment_cancelled(
    body: AppointmentCancelled, session: Annotated[Session, Depends(get_session)]
) -> CancelledMessages:
    result = session.execute(
        update(Message)
        .where(Message.appointment_id == body.appointment_id, Message.status == Status.PENDING)
        .values(status=Status.CANCELLED)
    )
    session.commit()
    return CancelledMessages(cancelled=result.rowcount)
