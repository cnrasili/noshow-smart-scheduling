from datetime import UTC, datetime, time, timedelta

import pytest

from noshow_db.models.core import Appointment, DoctorSchedule, Slot
from web_backend.clinic import CLINIC_TZ, today


@pytest.fixture
def doctor(make_doctor):
    return make_doctor()


@pytest.fixture
def doctor_headers(doctor, login):
    return login("doctor@example.com")


def _slot(db, doctor_id: int, start: datetime) -> Slot:
    start = start.astimezone(UTC)
    slot = Slot(doctor_id=doctor_id, start_at=start, end_at=start + timedelta(minutes=20))
    db.add(slot)
    db.commit()
    return slot


def _appointment(db, patient_id: int, slot: Slot) -> Appointment:
    start = slot.start_at.replace(tzinfo=UTC) if slot.start_at.tzinfo is None else slot.start_at
    day = start.astimezone(CLINIC_TZ).date()
    appointment = Appointment(
        patient_id=patient_id,
        slot_id=slot.id,
        appointment_date=day,
        booking_date=min(day, today()),
    )
    db.add(appointment)
    db.commit()
    return appointment


def test_calendar_lists_the_days_slots_with_patients(
    db, client, doctor, doctor_headers, make_patient
):
    day = today() + timedelta(days=3)
    morning = _slot(db, doctor.id, datetime.combine(day, time(9, 0), CLINIC_TZ))
    _slot(db, doctor.id, datetime.combine(day, time(9, 20), CLINIC_TZ))
    _slot(db, doctor.id, datetime.combine(day + timedelta(days=1), time(9, 0), CLINIC_TZ))
    _appointment(db, make_patient(name="Ayse Demo").id, morning)

    response = client.get(
        "/doctors/me/calendar", params={"date": day.isoformat()}, headers=doctor_headers
    )

    assert response.status_code == 200
    calendar = response.json()
    assert [len(entry["appointments"]) for entry in calendar] == [1, 0]
    entry = calendar[0]["appointments"][0]
    assert entry["patient_name"] == "Ayse Demo"
    assert (entry["patient_age"], entry["patient_gender"]) == (30, "F")
    assert entry["booking_date"] == min(day, today()).isoformat()
    assert entry["attended"] is None


def test_calendar_shows_only_own_slots(db, client, doctor_headers, make_doctor):
    other = make_doctor(email="other@example.com")
    _slot(db, other.id, datetime.combine(today(), time(9, 0), CLINIC_TZ))

    assert client.get("/doctors/me/calendar", headers=doctor_headers).json() == []


def test_patients_cannot_open_the_calendar(client, make_patient, login):
    make_patient()

    response = client.get("/doctors/me/calendar", headers=login("patient@example.com"))

    assert response.status_code == 403


@pytest.mark.parametrize("attended", [True, False])
def test_doctor_marks_attendance_after_start(
    db, client, doctor, doctor_headers, make_patient, attended
):
    slot = _slot(db, doctor.id, datetime.now(UTC) - timedelta(minutes=30))
    appointment = _appointment(db, make_patient().id, slot)

    response = client.patch(
        f"/appointments/{appointment.id}/attendance",
        json={"attended": attended},
        headers=doctor_headers,
    )

    assert response.status_code == 200
    assert response.json()["attended"] is attended
    db.refresh(appointment)
    assert appointment.attended is attended


def test_attendance_cannot_be_marked_before_start(db, client, doctor, doctor_headers, make_patient):
    slot = _slot(db, doctor.id, datetime.now(UTC) + timedelta(hours=2))
    appointment = _appointment(db, make_patient().id, slot)

    response = client.patch(
        f"/appointments/{appointment.id}/attendance",
        json={"attended": True},
        headers=doctor_headers,
    )

    assert response.status_code == 422


def test_doctor_cannot_mark_other_doctors_appointments(
    db, client, doctor_headers, make_doctor, make_patient
):
    other = make_doctor(email="other@example.com")
    slot = _slot(db, other.id, datetime.now(UTC) - timedelta(minutes=30))
    appointment = _appointment(db, make_patient().id, slot)

    response = client.patch(
        f"/appointments/{appointment.id}/attendance",
        json={"attended": True},
        headers=doctor_headers,
    )

    assert response.status_code == 404


def test_doctor_reads_weekly_working_hours(db, client, doctor, doctor_headers):
    db.add_all(
        [
            DoctorSchedule(
                doctor_id=doctor.id, weekday=2, start_time=time(13, 0), end_time=time(16, 0)
            ),
            DoctorSchedule(
                doctor_id=doctor.id, weekday=0, start_time=time(9, 0), end_time=time(12, 0)
            ),
        ]
    )
    db.commit()

    response = client.get("/doctors/me/schedule", headers=doctor_headers)

    assert response.json() == [
        {"weekday": 0, "start_time": "09:00:00", "end_time": "12:00:00"},
        {"weekday": 2, "start_time": "13:00:00", "end_time": "16:00:00"},
    ]


def _agenda(client, headers, date_from, date_to):
    return client.get(
        "/doctors/me/agenda",
        params={"date_from": date_from.isoformat(), "date_to": date_to.isoformat()},
        headers=headers,
    )


def test_agenda_lists_every_day_with_slots_and_appointments(
    db, client, doctor, doctor_headers, make_patient
):
    start = today() + timedelta(days=1)
    busy = start + timedelta(days=10)
    first = _slot(db, doctor.id, datetime.combine(busy, time(9, 20), CLINIC_TZ))
    _slot(db, doctor.id, datetime.combine(busy, time(9, 0), CLINIC_TZ))
    _slot(db, doctor.id, datetime.combine(start, time(9, 0), CLINIC_TZ))
    regular = _appointment(db, make_patient(name="Ayse Demo").id, first)
    extra = _appointment(db, make_patient(email="ali@example.com", name="Ali Demo").id, first)

    response = _agenda(client, doctor_headers, start, start + timedelta(days=13))

    assert response.status_code == 200
    days = response.json()
    assert [d["date"] for d in days] == [(start + timedelta(days=n)).isoformat() for n in range(14)]
    by_date = {d["date"]: d for d in days}
    assert by_date[start.isoformat()]["slot_count"] == 1
    assert by_date[start.isoformat()]["appointments"] == []
    assert by_date[(start + timedelta(days=2)).isoformat()]["slot_count"] == 0
    busy_day = by_date[busy.isoformat()]
    assert busy_day["slot_count"] == 2
    assert [(a["id"], a["patient_name"], a["extra"]) for a in busy_day["appointments"]] == [
        (regular.id, "Ayse Demo", False),
        (extra.id, "Ali Demo", True),
    ]
    assert "email" not in str(busy_day)


def test_agenda_shows_only_own_slots(db, client, doctor_headers, make_doctor, make_patient):
    other = make_doctor(email="other@example.com", name="Dr. Other")
    day = today() + timedelta(days=2)
    _appointment(
        db, make_patient().id, _slot(db, other.id, datetime.combine(day, time(9), CLINIC_TZ))
    )

    days = _agenda(client, doctor_headers, day, day).json()

    assert days == [{"date": day.isoformat(), "slot_count": 0, "appointments": []}]


@pytest.mark.parametrize("length", [-1, 31])
def test_agenda_rejects_reversed_or_long_ranges(client, doctor_headers, length):
    start = today()

    response = _agenda(client, doctor_headers, start, start + timedelta(days=length))

    assert response.status_code == 422


def test_patients_cannot_open_the_agenda(client, make_patient, login):
    make_patient()
    headers = login("patient@example.com")

    assert _agenda(client, headers, today(), today()).status_code == 403
