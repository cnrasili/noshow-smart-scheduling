from datetime import date

import pytest
from fastapi.testclient import TestClient
from sqlalchemy import select
from sqlalchemy.orm import Session, sessionmaker

from noshow_db.models.service import BookingDecision
from overbooking_service.data_source import SlotBooking, SlotState
from overbooking_service.dependencies import (
    get_data_source,
    get_predictor,
    get_rule,
    get_slot_source,
)
from overbooking_service.features import PatientRecord
from overbooking_service.main import app
from overbooking_service.rules import OverbookingRule

SLOT_DATE = date(2026, 11, 10)
BOOKED = date(2026, 11, 1)
BODY = {"patient_id": 1, "slot_id": 10, "booking_date": "2026-11-02"}

# Patient id -> no-show probability; the fake model reads it from the age feature
RISKS = {1: 0.34, 2: 0.41, 3: 0.12, 4: 0.50}


class FakePredictor:
    version = "fake-v0"

    def predict(self, features: dict[str, float]) -> float:
        return RISKS[int(features["age"])]


class FakePatients:
    def get_patient(self, patient_id: int) -> PatientRecord | None:
        if patient_id not in RISKS:
            return None
        return PatientRecord(patient_id, patient_id, "F", False, False, False, False, 0)

    def get_history(self, patient_id: int) -> list:
        return []


class FakeSlots:
    """In-memory slots for tests."""

    def __init__(self) -> None:
        self.overbooks = 0
        self.slots = {
            10: SlotState(10, 1, SLOT_DATE, 2, ()),
            11: SlotState(11, 1, SLOT_DATE, 2, (SlotBooking(2, BOOKED),)),
            12: SlotState(12, 1, SLOT_DATE, 2, (SlotBooking(3, BOOKED),)),
            13: SlotState(13, 1, SLOT_DATE, 2, (SlotBooking(2, BOOKED), SlotBooking(4, BOOKED))),
            14: SlotState(14, 1, SLOT_DATE, 2, (SlotBooking(99, BOOKED),)),
            15: SlotState(15, 1, SLOT_DATE, 1, (SlotBooking(2, BOOKED),)),
        }

    def get_slot(self, slot_id: int) -> SlotState | None:
        return self.slots.get(slot_id)

    def count_overbooks(self, doctor_id: int, slot_date: date) -> int:
        return self.overbooks


@pytest.fixture
def slots(client: TestClient) -> FakeSlots:
    fake = FakeSlots()
    app.dependency_overrides[get_slot_source] = lambda: fake
    app.dependency_overrides[get_data_source] = FakePatients
    app.dependency_overrides[get_predictor] = FakePredictor
    app.dependency_overrides[get_rule] = lambda: OverbookingRule(
        threshold=0.30, daily_overbook_limit=2
    )
    return fake


def post(client: TestClient, **overrides) -> dict:
    response = client.post("/booking-decision", json={**BODY, **overrides})
    assert response.status_code == 200
    return response.json()


def test_empty_slot_is_normal_booking(client: TestClient, slots: FakeSlots):
    data = post(client)
    assert data == {"allow": True, "overbook": False, "p_noshow": 0.34, "reason": "Slot is empty"}


def test_high_risk_booked_slot_is_overbooked(client: TestClient, slots: FakeSlots):
    slots.overbooks = 1
    data = post(client, slot_id=11)
    assert data["allow"] and data["overbook"]
    assert data["reason"] == "Slot is booked; booked patient risk 0.41 >= 0.30; daily overbooks 1/2"


def test_low_risk_booked_slot_is_rejected(client: TestClient, slots: FakeSlots):
    data = post(client, slot_id=12)
    assert not data["allow"]
    assert data["reason"] == "Slot is booked; booked patient risk 0.12 < 0.30"


def test_daily_limit_rejects_overbook(client: TestClient, slots: FakeSlots):
    slots.overbooks = 2
    data = post(client, slot_id=11)
    assert not data["allow"]
    assert "daily overbook limit reached (2/2)" in data["reason"]


def test_full_slot_is_rejected(client: TestClient, slots: FakeSlots):
    data = post(client, slot_id=13)
    assert not data["allow"]
    assert data["reason"] == "Slot is full (2/2 patients)"


def test_slot_capacity_comes_from_slot(client: TestClient, slots: FakeSlots):
    data = post(client, slot_id=15)
    assert not data["allow"]
    assert data["reason"] == "Slot is full (1/1 patients)"


def test_patient_already_in_slot_is_rejected(client: TestClient, slots: FakeSlots):
    data = post(client, patient_id=2, slot_id=11)
    assert not data["allow"]
    assert data["reason"] == "Patient is already booked in this slot"


def test_decision_is_logged(
    client: TestClient, slots: FakeSlots, session_factory: sessionmaker[Session]
):
    post(client, slot_id=11)
    with session_factory() as session:
        logged = session.scalars(select(BookingDecision)).one()
    assert (logged.patient_id, logged.slot_id) == (1, 11)
    assert logged.allow and logged.overbook
    assert logged.p_noshow == 0.34
    assert logged.booked_p_noshow == 0.41
    assert logged.threshold == 0.30
    assert logged.model_version == "fake-v0"


@pytest.mark.parametrize(
    ("overrides", "status"),
    [
        ({"slot_id": 999}, 404),
        ({"patient_id": 99}, 404),
        ({"booking_date": "2026-11-11"}, 422),
        ({"slot_id": 0}, 422),
        ({"slot_id": 14}, 503),
    ],
)
def test_error_responses(client: TestClient, slots: FakeSlots, overrides: dict, status: int):
    response = client.post("/booking-decision", json={**BODY, **overrides})
    assert response.status_code == status


def test_unknown_slot_in_database_returns_404(client: TestClient):
    response = client.post("/booking-decision", json=BODY)
    assert response.status_code == 404


def test_default_rule_comes_from_config():
    rule = get_rule()
    assert rule.threshold == 0.30
    assert rule.daily_overbook_limit == 2
