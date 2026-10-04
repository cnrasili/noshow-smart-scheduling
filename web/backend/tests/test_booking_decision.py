# Booking through the overbooking service's /booking-decision (faked in conftest)
from datetime import UTC, datetime, timedelta

import httpx2
import pytest
from sqlalchemy import func, select

from noshow_db.models.core import Appointment, Slot
from web_backend.clinic import today


@pytest.fixture
def slot(db, make_doctor) -> Slot:
    doctor = make_doctor()
    start = datetime.now(UTC).replace(microsecond=0) + timedelta(days=2)
    slot = Slot(doctor_id=doctor.id, start_at=start, end_at=start + timedelta(minutes=20))
    db.add(slot)
    db.commit()
    return slot


@pytest.fixture
def first_patient(make_patient, login):
    patient = make_patient(email="first@example.com")
    return patient, login("first@example.com")


@pytest.fixture
def second_patient(make_patient, login):
    patient = make_patient(email="second@example.com")
    return patient, login("second@example.com")


def _book(client, headers, slot_id):
    return client.post("/appointments", json={"slot_id": slot_id}, headers=headers)


def _count(db) -> int:
    return db.scalar(select(func.count()).select_from(Appointment))


def test_service_is_asked_with_patient_slot_and_booking_date(
    client, db, overbooking, slot, first_patient
):
    patient, headers = first_patient
    overbooking.allow()

    response = _book(client, headers, slot.id)

    assert response.status_code == 201
    assert overbooking.decisions == [
        {
            "path": "/booking-decision",
            "patient_id": patient.id,
            "slot_id": slot.id,
            "booking_date": today().isoformat(),
        }
    ]


def test_allowed_overbook_adds_a_second_patient(
    client, db, overbooking, slot, first_patient, second_patient
):
    overbooking.allow()
    _book(client, first_patient[1], slot.id)
    overbooking.allow(overbook=True)

    response = _book(client, second_patient[1], slot.id)

    assert response.status_code == 201
    assert _count(db) == 2


def test_rejected_booking_creates_no_appointment(
    client, db, overbooking, slot, first_patient, second_patient
):
    overbooking.allow()
    _book(client, first_patient[1], slot.id)
    overbooking.reject()

    response = _book(client, second_patient[1], slot.id)

    assert response.status_code == 409
    assert response.json()["detail"] == "Slot is not available"
    assert _count(db) == 1


@pytest.mark.parametrize(
    "failure",
    [
        None,
        lambda _: httpx2.Response(503, json={"detail": "Patient data cannot be read"}),
        lambda _: httpx2.Response(200, json={"unexpected": True}),
    ],
    ids=["unreachable", "503", "bad-body"],
)
def test_empty_slot_is_booked_when_service_is_unavailable(
    client, db, overbooking, slot, first_patient, failure
):
    overbooking.respond = failure

    response = _book(client, first_patient[1], slot.id)

    assert response.status_code == 201
    assert len(overbooking.decisions) == 1
    assert _count(db) == 1


def test_timeout_counts_as_unavailable(client, db, overbooking, slot, first_patient):
    def timeout(_):
        raise httpx2.ReadTimeout("Service too slow")

    overbooking.respond = timeout

    assert _book(client, first_patient[1], slot.id).status_code == 201


def test_booked_slot_is_not_overbooked_when_service_is_unavailable(
    client, db, overbooking, slot, first_patient, second_patient
):
    overbooking.allow()
    _book(client, first_patient[1], slot.id)
    overbooking.respond = None

    response = _book(client, second_patient[1], slot.id)

    assert response.status_code == 409
    assert response.json()["detail"] == "Slot is already booked"
    assert _count(db) == 1


def test_full_slot_is_rejected_without_asking_the_service(
    client, db, overbooking, slot, first_patient, second_patient, make_patient, login
):
    overbooking.allow(overbook=True)
    _book(client, first_patient[1], slot.id)
    _book(client, second_patient[1], slot.id)
    third_headers = login(make_patient(email="third@example.com").email)
    asked = len(overbooking.decisions)

    response = _book(client, third_headers, slot.id)

    assert response.status_code == 409
    assert response.json()["detail"] == "Slot is full"
    assert len(overbooking.decisions) == asked


def test_full_slot_is_listed_as_unavailable(
    client, overbooking, slot, first_patient, second_patient
):
    overbooking.allow(overbook=True)
    _book(client, first_patient[1], slot.id)
    _book(client, second_patient[1], slot.id)

    listed = client.get("/slots", params={"doctor_id": slot.doctor_id}, headers=first_patient[1])

    assert [(s["booked_count"], s["available"]) for s in listed.json()] == [(2, False)]
