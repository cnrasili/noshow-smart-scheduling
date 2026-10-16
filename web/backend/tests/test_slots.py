import itertools
from datetime import UTC, date, datetime, time, timedelta

import pytest
from sqlalchemy import func, select

from noshow_db.models.core import DoctorSchedule, Slot
from web_backend.clinic import CLINIC_TZ, as_utc, today
from web_backend.slots import generate_slots

MONDAY = date(2026, 11, 9)


@pytest.fixture
def doctor(db, make_doctor):
    """Doctor working Monday 09:00-12:00 and Wednesday 13:00-14:10."""
    doctor = make_doctor()
    db.add_all(
        [
            DoctorSchedule(
                doctor_id=doctor.id, weekday=0, start_time=time(9, 0), end_time=time(12, 0)
            ),
            DoctorSchedule(
                doctor_id=doctor.id, weekday=2, start_time=time(13, 0), end_time=time(14, 10)
            ),
        ]
    )
    db.commit()
    return doctor


def _starts(db) -> list[datetime]:
    return [as_utc(start) for start in db.scalars(select(Slot.start_at).order_by(Slot.start_at))]


def test_working_day_is_split_into_back_to_back_slots(db, doctor) -> None:
    generate_slots(db, doctor.id, MONDAY, MONDAY, slot_minutes=20)
    db.commit()

    starts = _starts(db)
    assert len(starts) == 9
    assert starts[0] == datetime(2026, 11, 9, 9, 0, tzinfo=CLINIC_TZ)
    assert starts[-1] == datetime(2026, 11, 9, 11, 40, tzinfo=CLINIC_TZ)
    slot = db.scalars(select(Slot).order_by(Slot.start_at)).first()
    assert as_utc(slot.end_at) - as_utc(slot.start_at) == timedelta(minutes=20)


def test_slots_are_stored_in_utc(db, doctor) -> None:
    generate_slots(db, doctor.id, MONDAY, MONDAY)
    db.commit()

    # Istanbul is UTC+3 all year
    assert _starts(db)[0] == datetime(2026, 11, 9, 6, 0, tzinfo=UTC)


def test_days_without_working_hours_get_no_slots(db, doctor) -> None:
    tuesday = MONDAY + timedelta(days=1)
    assert generate_slots(db, doctor.id, tuesday, tuesday) == []


def test_remainder_shorter_than_a_slot_is_unused(db, doctor) -> None:
    wednesday = MONDAY + timedelta(days=2)
    generate_slots(db, doctor.id, wednesday, wednesday, slot_minutes=20)
    db.commit()

    # 13:00-14:10 fits three 20-minute slots; 14:00-14:10 stays empty
    assert [start.astimezone(CLINIC_TZ).time() for start in _starts(db)] == [
        time(13, 0),
        time(13, 20),
        time(13, 40),
    ]


def test_generation_can_be_repeated_without_duplicates(db, doctor) -> None:
    week_end = MONDAY + timedelta(days=6)
    first = generate_slots(db, doctor.id, MONDAY, week_end)
    db.commit()
    second = generate_slots(db, doctor.id, MONDAY, week_end)
    db.commit()

    assert len(first) == 12
    assert second == []
    assert db.scalar(select(func.count()).select_from(Slot)) == 12


def test_other_doctors_are_not_affected(db, doctor, make_doctor) -> None:
    other = make_doctor(email="other@example.com")

    generate_slots(db, other.id, MONDAY, MONDAY)

    assert db.scalar(select(func.count()).select_from(Slot)) == 0


def _next_monday() -> date:
    # One to seven days ahead, so eight days before it is always in the past
    return today() + timedelta(days=7 - today().weekday())


def test_doctor_generates_own_slots(client, db, doctor, login) -> None:
    monday = _next_monday()
    response = client.post(
        "/doctors/me/slots/generate",
        json={"date_from": monday.isoformat(), "date_to": monday.isoformat()},
        headers=login("doctor@example.com"),
    )

    assert response.status_code == 200
    assert response.json() == {"created": 9}


@pytest.mark.parametrize(
    ("offset_from", "offset_to"),
    [(-8, 0), (2, 1), (0, 62)],
    ids=["past", "reversed", "too-long"],
)
def test_invalid_generation_ranges_are_rejected(
    client, doctor, login, offset_from, offset_to
) -> None:
    monday = _next_monday()
    response = client.post(
        "/doctors/me/slots/generate",
        json={
            "date_from": (monday + timedelta(days=offset_from)).isoformat(),
            "date_to": (monday + timedelta(days=offset_to)).isoformat(),
        },
        headers=login("doctor@example.com"),
    )

    assert response.status_code == 422


def test_patients_cannot_generate_slots(client, make_patient, login) -> None:
    make_patient()
    monday = _next_monday()

    response = client.post(
        "/doctors/me/slots/generate",
        json={"date_from": monday.isoformat(), "date_to": monday.isoformat()},
        headers=login("patient@example.com"),
    )

    assert response.status_code == 403


def test_a_new_slot_length_does_not_overlap_existing_slots(db, doctor) -> None:
    generate_slots(db, doctor.id, MONDAY, MONDAY, slot_minutes=30)
    db.commit()
    # Remove the last slot (11:30-12:00) so only that gap can be filled
    db.delete(db.scalars(select(Slot).order_by(Slot.start_at.desc())).first())
    db.commit()

    created = generate_slots(db, doctor.id, MONDAY, MONDAY, slot_minutes=15)
    db.commit()

    assert [as_utc(slot.start_at).astimezone(CLINIC_TZ).time() for slot in created] == [
        time(11, 30),
        time(11, 45),
    ]
    slots = db.scalars(select(Slot).order_by(Slot.start_at)).all()
    for earlier, later in itertools.pairwise(slots):
        assert as_utc(earlier.end_at) <= as_utc(later.start_at)
