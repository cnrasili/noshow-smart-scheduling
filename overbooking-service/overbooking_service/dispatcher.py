from datetime import datetime

from sqlalchemy import select, update
from sqlalchemy.orm import Session

from noshow_db.models.core import Patient
from noshow_db.models.service import Message
from overbooking_service.messages import Status
from overbooking_service.sender import MessageSender

NO_RECIPIENT = "Patient has no patient number"


def dispatch_due(session: Session, sender: MessageSender, now: datetime, max_attempts: int) -> int:
    """Send pending messages whose time has come; return the number sent."""
    # Messages for appointments that already started are not sent
    session.execute(
        update(Message)
        .where(Message.status == Status.PENDING, Message.appointment_start <= now)
        .values(status=Status.EXPIRED)
        .execution_options(synchronize_session=False)
    )
    session.commit()

    due = session.execute(
        select(Message, Patient.patient_number)
        .outerjoin(Patient, Patient.id == Message.patient_id)
        .where(Message.status == Status.PENDING, Message.send_at <= now)
        .order_by(Message.send_at)
        .with_for_update(of=Message, skip_locked=True)
    ).all()

    sent = 0
    for message, patient_number in due:
        message.attempts += 1
        if patient_number is None:
            # SMS are addressed by the dataset patient number; retrying cannot help
            message.status = Status.FAILED
            message.error = NO_RECIPIENT
            session.commit()
            continue
        try:
            sender.send(patient_number, message.body)
        except OSError as exc:
            message.error = str(exc)[:255]
            if message.attempts >= max_attempts:
                message.status = Status.FAILED
        else:
            message.status = Status.SENT
            message.sent_at = now
            message.error = None
            sent += 1
        # Commit each message so a sent message is never sent again
        session.commit()
    return sent
