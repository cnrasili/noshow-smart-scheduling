from collections.abc import Iterator
from datetime import UTC, datetime, timedelta

import pytest
from sqlalchemy import select
from sqlalchemy.orm import Session, sessionmaker

from noshow_db.models.core import Patient
from noshow_db.models.service import Message
from overbooking_service.dispatcher import dispatch_due

NOW = datetime(2026, 11, 9, 7, 0, tzinfo=UTC)
START = datetime(2026, 11, 10, 6, 30, tzinfo=UTC)
PATIENT_NUMBER = "93779.52927"


class FakeSender:
    def __init__(self, fail: bool = False) -> None:
        self.fail = fail
        self.sent: list[tuple[str, str]] = []

    def send(self, patient_number: str, text: str) -> None:
        if self.fail:
            raise ConnectionRefusedError("SMS gateway unavailable")
        self.sent.append((patient_number, text))


def add(
    session: Session,
    kind: str,
    send_at: datetime,
    status: str = "pending",
    appointment_start: datetime = START,
    patient_id: int = 1,
) -> None:
    session.add(
        Message(
            appointment_id=1,
            patient_id=patient_id,
            kind=kind,
            body="Body",
            appointment_start=appointment_start,
            send_at=send_at,
            status=status,
            attempts=0,
        )
    )
    session.commit()


def statuses(session: Session) -> dict[str, str]:
    return {m.kind: m.status for m in session.scalars(select(Message))}


@pytest.fixture
def session(session_factory: sessionmaker[Session]) -> Iterator[Session]:
    with session_factory() as session:
        # Patient 1 comes from the dataset; patient 2 has no patient number
        session.add_all(
            [
                Patient(
                    patient_number=PATIENT_NUMBER,
                    full_name=f"Hasta {PATIENT_NUMBER}",
                    email=f"{PATIENT_NUMBER}@hasta.sehirhastanesi.example",
                    age=33,
                    gender="F",
                ),
                Patient(full_name="Patient 2", email="p2@example.com", age=40, gender="M"),
            ]
        )
        session.commit()
        yield session


def test_sends_due_messages_only(session: Session):
    add(session, "confirmation", NOW - timedelta(minutes=1))
    add(session, "reminder", NOW + timedelta(hours=1))
    sender = FakeSender()

    assert dispatch_due(session, sender, NOW, max_attempts=3) == 1
    assert sender.sent == [(PATIENT_NUMBER, "Body")]
    assert statuses(session) == {"confirmation": "sent", "reminder": "pending"}


def test_message_without_patient_number_fails_at_once(session: Session):
    add(session, "confirmation", NOW, patient_id=2)
    sender = FakeSender()

    assert dispatch_due(session, sender, NOW, max_attempts=3) == 0
    message = session.scalars(select(Message)).one()
    assert (message.status, message.attempts) == ("failed", 1)
    assert message.error == "Patient has no patient number"
    assert sender.sent == []


def test_sent_message_is_not_sent_again(session: Session):
    add(session, "confirmation", NOW)
    sender = FakeSender()
    dispatch_due(session, sender, NOW, max_attempts=3)
    dispatch_due(session, sender, NOW + timedelta(minutes=1), max_attempts=3)
    assert len(sender.sent) == 1


def test_cancelled_message_is_not_sent(session: Session):
    add(session, "reminder", NOW, status="cancelled")
    sender = FakeSender()
    assert dispatch_due(session, sender, NOW, max_attempts=3) == 0
    assert sender.sent == []


def test_message_for_started_appointment_expires(session: Session):
    add(session, "reminder", NOW - timedelta(days=1), appointment_start=NOW)
    sender = FakeSender()
    assert dispatch_due(session, sender, NOW, max_attempts=3) == 0
    assert statuses(session) == {"reminder": "expired"}


def test_failed_send_is_retried_until_max_attempts(session: Session):
    add(session, "confirmation", NOW)
    sender = FakeSender(fail=True)

    dispatch_due(session, sender, NOW, max_attempts=2)
    message = session.scalars(select(Message)).one()
    assert (message.status, message.attempts) == ("pending", 1)
    assert message.error == "SMS gateway unavailable"

    dispatch_due(session, sender, NOW, max_attempts=2)
    session.refresh(message)
    assert (message.status, message.attempts) == ("failed", 2)
