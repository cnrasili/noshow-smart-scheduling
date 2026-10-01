from collections.abc import Iterator
from datetime import UTC, datetime, timedelta

import pytest
from sqlalchemy import select
from sqlalchemy.orm import Session, sessionmaker

from noshow_db.models.service import Message
from overbooking_service.dispatcher import dispatch_due

NOW = datetime(2026, 11, 9, 7, 0, tzinfo=UTC)
START = datetime(2026, 11, 10, 6, 30, tzinfo=UTC)


class FakeSender:
    def __init__(self, fail: bool = False) -> None:
        self.fail = fail
        self.sent: list[tuple[str, str, str]] = []

    def send(self, to: str, subject: str, body: str) -> None:
        if self.fail:
            raise ConnectionRefusedError("SMTP server unavailable")
        self.sent.append((to, subject, body))


def add(
    session: Session,
    kind: str,
    send_at: datetime,
    status: str = "pending",
    appointment_start: datetime = START,
) -> None:
    session.add(
        Message(
            appointment_id=1,
            patient_id=1,
            kind=kind,
            email="patient@example.com",
            subject=kind.title(),
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
        yield session


def test_sends_due_messages_only(session: Session):
    add(session, "confirmation", NOW - timedelta(minutes=1))
    add(session, "reminder", NOW + timedelta(hours=1))
    sender = FakeSender()

    assert dispatch_due(session, sender, NOW, max_attempts=3) == 1
    assert sender.sent == [("patient@example.com", "Confirmation", "Body")]
    assert statuses(session) == {"confirmation": "sent", "reminder": "pending"}


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
    assert message.error == "SMTP server unavailable"

    dispatch_due(session, sender, NOW, max_attempts=2)
    session.refresh(message)
    assert (message.status, message.attempts) == ("failed", 2)
