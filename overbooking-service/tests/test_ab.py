from collections import Counter
from datetime import UTC, date, datetime, timedelta

import pytest
from fastapi.testclient import TestClient
from sqlalchemy import select
from sqlalchemy.orm import Session, sessionmaker

from noshow_db.models.core import Appointment, Doctor, Patient, Slot
from noshow_db.models.service import AbAssignment
from overbooking_service.ab import Group, assign_group, two_proportion_test
from overbooking_service.config import AbTestSettings
from overbooking_service.dependencies import get_ab_settings, get_now
from overbooking_service.main import app

NOW = datetime(2026, 11, 2, 9, 0, tzinfo=UTC)
SALT = "reminder-ab-v1"
# Groups of patients 1 and 2 under SALT
CONTROL_PATIENT, REMINDER_PATIENT = 1, 2
BODY = {
    "appointment_id": 501,
    "email": "patient@example.com",
    "appointment_start": "2026-11-10T09:30:00+03:00",
}


@pytest.fixture(autouse=True)
def ab_enabled(client: TestClient) -> None:
    app.dependency_overrides[get_now] = lambda: NOW
    app.dependency_overrides[get_ab_settings] = lambda: AbTestSettings(enabled=True, salt=SALT)


def book(client: TestClient, patient_id: int, **overrides) -> dict:
    body = {**BODY, "patient_id": patient_id, **overrides}
    response = client.post("/events/appointment-booked", json=body)
    assert response.status_code == 200
    return response.json()


def assignments(session_factory: sessionmaker[Session]) -> list[AbAssignment]:
    with session_factory() as session:
        return list(session.scalars(select(AbAssignment).order_by(AbAssignment.id)))


def test_group_is_deterministic():
    assert assign_group(CONTROL_PATIENT, SALT) is Group.CONTROL
    assert assign_group(REMINDER_PATIENT, SALT) is Group.REMINDER
    assert all(assign_group(i, SALT) is assign_group(i, SALT) for i in range(1, 100))


def test_groups_are_balanced():
    counts = Counter(assign_group(i, SALT) for i in range(1, 10_001))
    assert 4_800 < counts[Group.REMINDER] < 5_200


def test_salt_changes_assignment():
    groups = [assign_group(i, SALT) for i in range(1, 101)]
    assert groups != [assign_group(i, "other-salt") for i in range(1, 101)]


def test_two_proportion_test():
    z, p_value = two_proportion_test(30, 100, 20, 100)
    assert z == pytest.approx(1.633, abs=1e-3)
    assert p_value == pytest.approx(0.1025, abs=1e-4)


@pytest.mark.parametrize("counts", [(0, 0, 5, 10), (5, 10, 0, 0), (0, 10, 0, 10), (10, 10, 5, 5)])
def test_two_proportion_test_without_variance(counts):
    assert two_proportion_test(*counts) is None


def test_control_group_gets_no_reminder(client: TestClient, session_factory: sessionmaker[Session]):
    data = book(client, CONTROL_PATIENT)
    assert data["ab_group"] == "control"
    assert [m["kind"] for m in data["messages"]] == ["confirmation"]
    [assignment] = assignments(session_factory)
    assert (assignment.appointment_id, assignment.patient_id, assignment.group) == (
        501,
        CONTROL_PATIENT,
        "control",
    )


def test_reminder_group_gets_reminder(client: TestClient, session_factory: sessionmaker[Session]):
    data = book(client, REMINDER_PATIENT)
    assert data["ab_group"] == "reminder"
    assert [m["kind"] for m in data["messages"]] == ["confirmation", "reminder"]
    assert [a.group for a in assignments(session_factory)] == ["reminder"]


def test_appointment_too_close_for_reminder_is_not_assigned(
    client: TestClient, session_factory: sessionmaker[Session]
):
    data = book(client, REMINDER_PATIENT, appointment_start="2026-11-02T15:00:00+03:00")
    assert data["ab_group"] is None
    assert [m["kind"] for m in data["messages"]] == ["confirmation"]
    assert assignments(session_factory) == []


def test_repeated_event_keeps_group(client: TestClient, session_factory: sessionmaker[Session]):
    first = book(client, CONTROL_PATIENT)
    second = book(client, CONTROL_PATIENT)
    assert second == first
    assert len(assignments(session_factory)) == 1


def test_disabled_test_sends_reminders_without_assignment(
    client: TestClient, session_factory: sessionmaker[Session]
):
    app.dependency_overrides[get_ab_settings] = lambda: AbTestSettings(enabled=False, salt=SALT)
    data = book(client, CONTROL_PATIENT)
    assert data["ab_group"] is None
    assert [m["kind"] for m in data["messages"]] == ["confirmation", "reminder"]
    assert assignments(session_factory) == []


def test_default_settings_come_from_config():
    settings = get_ab_settings()
    assert settings.enabled
    assert settings.salt == SALT


def seed_outcomes(session: Session, outcomes: dict[str, list[bool | None]]) -> None:
    session.add_all(
        [
            Doctor(id=1, full_name="Doctor"),
            Slot(
                id=1,
                doctor_id=1,
                start_at=NOW,
                end_at=NOW + timedelta(minutes=20),
                max_patients=100,
            ),
        ]
    )
    appointment_id = 0
    for group, values in outcomes.items():
        for attended in values:
            appointment_id += 1
            session.add_all(
                [
                    Patient(
                        id=appointment_id,
                        full_name="Patient",
                        email=f"p{appointment_id}@example.com",
                        age=40,
                        gender="F",
                    ),
                    Appointment(
                        id=appointment_id,
                        patient_id=appointment_id,
                        slot_id=1,
                        appointment_date=date(2026, 11, 2),
                        booking_date=date(2026, 11, 1),
                        attended=attended,
                    ),
                    AbAssignment(
                        appointment_id=appointment_id, patient_id=appointment_id, group=group
                    ),
                ]
            )
    # Assignment of a cancelled appointment whose row was deleted
    session.add(AbAssignment(appointment_id=999, patient_id=999, group="control"))
    session.commit()


def test_summary_compares_no_show_rates(client: TestClient, session_factory: sessionmaker[Session]):
    with session_factory() as session:
        seed_outcomes(
            session,
            {
                "reminder": [True] * 8 + [False] * 2 + [None],
                "control": [True] * 6 + [False] * 4 + [None, None],
            },
        )
    response = client.get("/ab/summary")
    assert response.status_code == 200
    data = response.json()
    assert data["groups"] == [
        {"group": "reminder", "appointments": 10, "no_shows": 2, "no_show_rate": 0.2},
        {"group": "control", "appointments": 10, "no_shows": 4, "no_show_rate": 0.4},
    ]
    assert data["difference"] == pytest.approx(0.2)
    z, p_value = two_proportion_test(4, 10, 2, 10)
    assert (data["z"], data["p_value"]) == (pytest.approx(z), pytest.approx(p_value))


def test_empty_summary(client: TestClient):
    data = client.get("/ab/summary").json()
    assert [g["appointments"] for g in data["groups"]] == [0, 0]
    assert data["difference"] is None
    assert data["z"] is None and data["p_value"] is None
