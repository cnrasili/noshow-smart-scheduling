from datetime import UTC, datetime, timedelta
from typing import Annotated

from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy import select, update
from sqlalchemy.exc import IntegrityError
from sqlalchemy.orm import Session

from noshow_db.models.service import AbAssignment, Message
from overbooking_service.ab import Group, assign_group
from overbooking_service.config import AbTestSettings, ReminderSettings
from overbooking_service.dependencies import (
    get_ab_settings,
    get_now,
    get_reminder_settings,
    get_session,
)
from overbooking_service.messages import Kind, Status, render
from overbooking_service.schemas import (
    AppointmentBooked,
    AppointmentCancelled,
    CancelledMessages,
    ScheduledMessage,
    ScheduledMessages,
)

router = APIRouter(prefix="/events")


def _scheduled(messages: list[Message], ab_group: str | None) -> ScheduledMessages:
    return ScheduledMessages(
        messages=[
            ScheduledMessage(kind=m.kind, send_at=m.send_at, status=m.status) for m in messages
        ],
        ab_group=ab_group,
    )


def _existing_group(session: Session, appointment_id: int) -> str | None:
    return session.scalar(
        select(AbAssignment.group).where(AbAssignment.appointment_id == appointment_id)
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
    ab_test: Annotated[AbTestSettings, Depends(get_ab_settings)],
    now: Annotated[datetime, Depends(get_now)],
    session: Annotated[Session, Depends(get_session)],
) -> ScheduledMessages:
    if body.appointment_start <= now:
        raise HTTPException(422, "appointment_start must be in the future")

    # Repeated events do not create duplicate messages
    existing = _existing(session, body.appointment_id)
    if existing:
        return _scheduled(existing, _existing_group(session, body.appointment_id))

    start = body.appointment_start.astimezone(UTC)
    send_times = {Kind.CONFIRMATION: now}
    reminder_at = start - timedelta(hours=reminders.hours_before)
    group = None
    if reminder_at > now:
        # Only appointments that can get a reminder take part in the A/B test
        if ab_test.enabled:
            group = assign_group(body.patient_id, ab_test.salt)
            session.add(
                AbAssignment(
                    appointment_id=body.appointment_id, patient_id=body.patient_id, group=group
                )
            )
        if group != Group.CONTROL:
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
        return _scheduled(
            _existing(session, body.appointment_id), _existing_group(session, body.appointment_id)
        )
    return _scheduled(messages, group)


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
