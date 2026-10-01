from datetime import UTC, datetime, timedelta

import pytest
from fastapi.testclient import TestClient
from sqlalchemy import select
from sqlalchemy.orm import Session, sessionmaker

from noshow_db.models.service import Message
from overbooking_service.dependencies import get_now
from overbooking_service.main import app

NOW = datetime(2026, 11, 2, 9, 0, tzinfo=UTC)
BODY = {
    "appointment_id": 501,
    "patient_id": 1,
    "email": "patient@example.com",
    "appointment_start": "2026-11-10T09:30:00+03:00",
}


@pytest.fixture(autouse=True)
def fixed_now(client: TestClient) -> None:
    app.dependency_overrides[get_now] = lambda: NOW


def book(client: TestClient, **overrides) -> list[dict]:
    response = client.post("/events/appointment-booked", json={**BODY, **overrides})
    assert response.status_code == 200
    return response.json()["messages"]


def stored(session_factory: sessionmaker[Session]) -> list[Message]:
    with session_factory() as session:
        return list(session.scalars(select(Message).order_by(Message.id)))


def utc(value: str) -> datetime:
    # SQLite drops the time zone; stored times are UTC
    parsed = datetime.fromisoformat(value)
    return parsed.replace(tzinfo=UTC) if parsed.tzinfo is None else parsed


def test_booking_schedules_confirmation_and_reminder(client: TestClient):
    messages = book(client)
    assert [m["kind"] for m in messages] == ["confirmation", "reminder"]
    assert all(m["status"] == "pending" for m in messages)
    assert utc(messages[0]["send_at"]) == NOW
    # 24 hours before 06:30 UTC on 10 November
    assert utc(messages[1]["send_at"]) == datetime(2026, 11, 9, 6, 30, tzinfo=UTC)


def test_message_text_uses_local_appointment_time(
    client: TestClient, session_factory: sessionmaker[Session]
):
    book(client)
    confirmation, reminder = stored(session_factory)
    assert confirmation.email == "patient@example.com"
    assert confirmation.subject == "Appointment confirmed"
    assert "10 November 2026, 09:30" in confirmation.body
    assert reminder.subject == "Appointment reminder"


def test_no_reminder_when_appointment_is_too_close(client: TestClient):
    start = (NOW + timedelta(hours=5)).isoformat()
    messages = book(client, appointment_start=start)
    assert [m["kind"] for m in messages] == ["confirmation"]


def test_repeated_event_does_not_duplicate_messages(
    client: TestClient, session_factory: sessionmaker[Session]
):
    book(client)
    again = book(client)
    assert len(again) == 2
    assert len(stored(session_factory)) == 2


def test_cancel_cancels_pending_messages(
    client: TestClient, session_factory: sessionmaker[Session]
):
    book(client)
    with session_factory() as session:
        confirmation = session.scalars(select(Message).where(Message.kind == "confirmation")).one()
        confirmation.status = "sent"
        session.commit()

    response = client.post("/events/appointment-cancelled", json={"appointment_id": 501})
    assert response.json() == {"cancelled": 1}
    assert [m.status for m in stored(session_factory)] == ["sent", "cancelled"]


def test_cancel_unknown_appointment_cancels_nothing(client: TestClient):
    response = client.post("/events/appointment-cancelled", json={"appointment_id": 999})
    assert response.status_code == 200
    assert response.json() == {"cancelled": 0}


@pytest.mark.parametrize(
    "overrides",
    [
        {"appointment_start": "2026-11-01T09:00:00+00:00"},
        {"appointment_start": "2026-11-10T09:30:00"},
        {"email": "not-an-email"},
        {"appointment_id": 0},
    ],
)
def test_invalid_booking_event_returns_422(client: TestClient, overrides: dict):
    response = client.post("/events/appointment-booked", json={**BODY, **overrides})
    assert response.status_code == 422
