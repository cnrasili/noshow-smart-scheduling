from datetime import UTC, datetime, timedelta

import pytest
from sqlalchemy import func, select

from noshow_db.models.core import Appointment, Slot
from web_backend.clinic import CLINIC_TZ, today


@pytest.fixture
def doctor(make_doctor):
    return make_doctor()


@pytest.fixture
def make_slot(db, doctor):
    def make(hours_from_now: float) -> Slot:
        start = datetime.now(UTC).replace(microsecond=0) + timedelta(hours=hours_from_now)
        slot = Slot(doctor_id=doctor.id, start_at=start, end_at=start + timedelta(minutes=20))
        db.add(slot)
        db.commit()
        return slot

    return make


@pytest.fixture
def patient_headers(make_patient, login):
    make_patient()
    return login("patient@example.com")


def _book(client, headers, slot_id):
    return client.post("/appointments", json={"slot_id": slot_id}, headers=headers)


def test_doctors_are_listed_for_signed_in_users(client, doctor, patient_headers) -> None:
    response = client.get("/doctors", headers=patient_headers)

    assert response.status_code == 200
    assert response.json() == [{"id": doctor.id, "full_name": "Dr. Test", "specialty": "General"}]
    assert client.get("/doctors").status_code == 401


def test_patient_books_an_empty_slot(client, db, make_slot, patient_headers) -> None:
    slot = make_slot(hours_from_now=48)

    response = _book(client, patient_headers, slot.id)

    assert response.status_code == 201
    body = response.json()
    assert body["doctor_name"] == "Dr. Test"
    assert body["doctor_specialty"] == "General"
    assert body["attended"] is None
    assert body["booking_date"] == today().isoformat()
    expected_day = slot.start_at.replace(tzinfo=UTC).astimezone(CLINIC_TZ).date()
    assert body["appointment_date"] == expected_day.isoformat()
    assert db.scalar(select(func.count()).select_from(Appointment)) == 1


def test_slot_listing_shows_bookings(client, make_slot, make_patient, login, patient_headers):
    booked = make_slot(hours_from_now=24)
    free = make_slot(hours_from_now=25)
    make_slot(hours_from_now=-1)
    _book(client, patient_headers, booked.id)

    other_headers = login(make_patient(email="other@example.com").email)
    slots = client.get(
        "/slots", params={"doctor_id": booked.doctor_id}, headers=other_headers
    ).json()

    # The past slot is hidden; a booked slot stays bookable below its capacity of two
    assert [(s["id"], s["booked_count"], s["available"], s["booked_by_me"]) for s in slots] == [
        (booked.id, 1, True, False),
        (free.id, 0, True, False),
    ]
    mine = client.get("/slots", params={"doctor_id": booked.doctor_id}, headers=patient_headers)
    assert mine.json()[0]["booked_by_me"] is True


def test_same_slot_cannot_be_booked_twice(client, make_slot, patient_headers) -> None:
    slot = make_slot(hours_from_now=24)
    _book(client, patient_headers, slot.id)

    response = _book(client, patient_headers, slot.id)

    assert response.status_code == 409
    assert response.json()["detail"] == "You already booked this slot"


def test_unknown_and_past_slots_cannot_be_booked(client, make_slot, patient_headers) -> None:
    past = make_slot(hours_from_now=-1)

    assert _book(client, patient_headers, 999).status_code == 404
    assert _book(client, patient_headers, past.id).status_code == 422


def test_doctors_cannot_book(client, make_slot, login) -> None:
    slot = make_slot(hours_from_now=24)

    assert _book(client, login("doctor@example.com"), slot.id).status_code == 403


def test_patient_lists_and_cancels_own_appointment(client, db, make_slot, patient_headers):
    later = make_slot(hours_from_now=72)
    sooner = make_slot(hours_from_now=24)
    _book(client, patient_headers, later.id)
    appointment_id = _book(client, patient_headers, sooner.id).json()["id"]

    listed = client.get("/patients/me/appointments", headers=patient_headers).json()
    assert [a["slot_id"] for a in listed] == [sooner.id, later.id]

    response = client.delete(f"/appointments/{appointment_id}", headers=patient_headers)
    assert response.status_code == 204
    assert db.scalar(select(func.count()).select_from(Appointment)) == 1


def test_patients_cannot_cancel_others_appointments(
    client, make_slot, make_patient, login, patient_headers
):
    slot = make_slot(hours_from_now=24)
    appointment_id = _book(client, patient_headers, slot.id).json()["id"]
    other_headers = login(make_patient(email="other@example.com").email)

    response = client.delete(f"/appointments/{appointment_id}", headers=other_headers)

    assert response.status_code == 404


def test_started_appointments_cannot_be_cancelled(client, db, make_slot, patient_headers):
    slot = make_slot(hours_from_now=24)
    appointment_id = _book(client, patient_headers, slot.id).json()["id"]
    slot.start_at = datetime.now(UTC) - timedelta(minutes=5)
    slot.end_at = slot.start_at + timedelta(minutes=20)
    db.commit()

    response = client.delete(f"/appointments/{appointment_id}", headers=patient_headers)

    assert response.status_code == 422
