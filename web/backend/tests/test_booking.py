from datetime import UTC, datetime, timedelta

import pytest
from sqlalchemy import func, select

from noshow_db.models.core import Appointment, Slot
from web_backend.clinic import CLINIC_TZ, today


@pytest.fixture
def doctor(make_department):
    return make_department()


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


def test_no_doctor_list_is_served(client, doctor, patient_headers) -> None:
    assert client.get("/doctors", headers=patient_headers).status_code == 404


def test_patient_books_an_empty_slot(client, db, make_slot, patient_headers) -> None:
    slot = make_slot(hours_from_now=48)

    response = _book(client, patient_headers, slot.id)

    assert response.status_code == 201
    body = response.json()
    assert not [field for field in body if field.startswith("doctor")]
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
    slots = client.get("/slots", headers=other_headers).json()

    # The past slot is hidden; a booked slot stays free ("Müsait") below its capacity of two,
    # and nothing tells how many patients it has
    assert slots == [
        {
            "id": booked.id,
            "start_at": slots[0]["start_at"],
            "end_at": slots[0]["end_at"],
            "available": True,
            "booked_by_me": False,
        },
        {
            "id": free.id,
            "start_at": slots[1]["start_at"],
            "end_at": slots[1]["end_at"],
            "available": True,
            "booked_by_me": False,
        },
    ]
    mine = client.get("/slots", headers=patient_headers).json()
    # The patient's own slot is not free for them
    assert (mine[0]["available"], mine[0]["booked_by_me"]) == (False, True)


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

    assert _book(client, login("aile.hekimligi"), slot.id).status_code == 403


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
