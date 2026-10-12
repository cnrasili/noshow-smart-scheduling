# Booked and cancelled events sent to the overbooking service (faked in conftest)
from datetime import UTC, datetime, timedelta

import httpx2
import pytest
from sqlalchemy import func, select

from noshow_db.models.core import Appointment, Slot


@pytest.fixture
def slot(db, make_doctor) -> Slot:
    doctor = make_doctor()
    start = datetime(2030, 3, 4, 6, 20, tzinfo=UTC)
    slot = Slot(doctor_id=doctor.id, start_at=start, end_at=start + timedelta(minutes=20))
    db.add(slot)
    db.commit()
    return slot


@pytest.fixture
def patient(make_patient, login):
    patient = make_patient(email="ayse@example.com")
    return patient, login("ayse@example.com")


def _book(client, headers, slot_id):
    return client.post("/appointments", json={"slot_id": slot_id}, headers=headers)


def test_booking_reports_the_appointment_with_clinic_time(client, overbooking, slot, patient):
    patient_row, headers = patient
    overbooking.allow()

    appointment_id = _book(client, headers, slot.id).json()["id"]

    assert overbooking.events == [
        {
            "path": "/events/appointment-booked",
            "appointment_id": appointment_id,
            "patient_id": patient_row.id,
            "email": "ayse@example.com",
            # 06:20 UTC is 09:20 in the clinic; the offset tells the service the time zone
            "appointment_start": "2030-03-04T09:20:00+03:00",
        }
    ]


def test_cancellation_reports_the_appointment(client, overbooking, slot, patient):
    _, headers = patient
    overbooking.allow()
    appointment_id = _book(client, headers, slot.id).json()["id"]

    assert client.delete(f"/appointments/{appointment_id}", headers=headers).status_code == 204

    assert overbooking.events[-1] == {
        "path": "/events/appointment-cancelled",
        "appointment_id": appointment_id,
    }


def test_rejected_booking_sends_no_event(client, overbooking, slot, patient):
    _, headers = patient
    overbooking.reject()

    assert _book(client, headers, slot.id).status_code == 409
    assert overbooking.events == []


@pytest.mark.parametrize(
    "event_response",
    [
        None,
        lambda: httpx2.Response(422, json={"detail": "appointment_start must be in the future"}),
    ],
    ids=["unreachable", "422"],
)
def test_failed_events_keep_the_booking_and_cancellation(
    client, db, overbooking, slot, patient, event_response
):
    _, headers = patient
    decision = {"allow": True, "overbook": False, "p_noshow": 0.2, "reason": "ok"}

    def respond(body: dict) -> httpx2.Response:
        if "slot_id" in body:
            return httpx2.Response(200, json=decision)
        if event_response is None:
            raise httpx2.ConnectError("Overbooking service stopped")
        return event_response()

    overbooking.respond = respond

    booked = _book(client, headers, slot.id)
    assert booked.status_code == 201
    assert db.scalar(select(func.count()).select_from(Appointment)) == 1

    cancelled = client.delete(f"/appointments/{booked.json()['id']}", headers=headers)
    assert cancelled.status_code == 204
    assert db.scalar(select(func.count()).select_from(Appointment)) == 0
    assert [e["path"] for e in overbooking.events] == [
        "/events/appointment-booked",
        "/events/appointment-cancelled",
    ]
