import os
import subprocess
import sys
from datetime import time, timedelta

import pytest
from sqlalchemy import select

from noshow_db.models.core import DoctorSchedule, Slot
from web_backend import slots
from web_backend.clinic import as_utc, today
from web_backend.seed import seed
from web_backend.slots import DEFAULT_SLOT_MINUTES, generate_slots, read_slot_minutes


def _lengths(db) -> set[timedelta]:
    return {as_utc(slot.end_at) - as_utc(slot.start_at) for slot in db.scalars(select(Slot))}


@pytest.mark.parametrize("value", [None, "", "  "])
def test_default_slot_length(value) -> None:
    assert read_slot_minutes(value) == DEFAULT_SLOT_MINUTES == 20


@pytest.mark.parametrize(("value", "minutes"), [("15", 15), (" 30 ", 30), ("5", 5), ("120", 120)])
def test_configured_slot_length(value, minutes) -> None:
    assert read_slot_minutes(value) == minutes


@pytest.mark.parametrize("value", ["abc", "15.5", "4", "121", "0", "-20"])
def test_invalid_slot_length_is_rejected(value) -> None:
    with pytest.raises(ValueError, match="SLOT_MINUTES must be a whole number of minutes"):
        read_slot_minutes(value)


def _start_backend(slot_minutes: str) -> subprocess.CompletedProcess:
    return subprocess.run(
        [
            sys.executable,
            "-c",
            "import web_backend.main, web_backend.slots as s; print(s.SLOT_MINUTES)",
        ],
        env={**os.environ, "SLOT_MINUTES": slot_minutes},
        capture_output=True,
        text=True,
    )


def test_backend_reads_slot_minutes_at_startup() -> None:
    result = _start_backend("15")

    assert result.returncode == 0, result.stderr
    assert result.stdout.strip() == "15"


def test_backend_does_not_start_with_an_invalid_slot_length() -> None:
    result = _start_backend("twenty")

    assert result.returncode != 0
    assert "SLOT_MINUTES must be a whole number of minutes from 5 to 120" in result.stderr


@pytest.fixture
def thirty_minute_slots(monkeypatch) -> None:
    monkeypatch.setattr(slots, "SLOT_MINUTES", 30)


@pytest.mark.usefixtures("thirty_minute_slots")
def test_generated_slots_use_the_configured_length(db, make_doctor) -> None:
    doctor = make_doctor()
    db.add(DoctorSchedule(doctor_id=doctor.id, weekday=0, start_time=time(9), end_time=time(12)))
    db.commit()
    monday = today() + timedelta(days=7 - today().weekday())

    created = generate_slots(db, doctor.id, monday, monday)
    db.commit()

    assert len(created) == 6
    assert _lengths(db) == {timedelta(minutes=30)}


@pytest.mark.usefixtures("thirty_minute_slots")
def test_doctor_generation_uses_the_configured_length(client, db, make_doctor, login) -> None:
    doctor = make_doctor()
    db.add(DoctorSchedule(doctor_id=doctor.id, weekday=0, start_time=time(9), end_time=time(12)))
    db.commit()
    monday = (today() + timedelta(days=7 - today().weekday())).isoformat()

    response = client.post(
        "/doctors/me/slots/generate",
        json={"date_from": monday, "date_to": monday},
        headers=login("doctor@example.com"),
    )

    assert response.json() == {"created": 6}
    assert _lengths(db) == {timedelta(minutes=30)}


@pytest.mark.usefixtures("thirty_minute_slots")
def test_seeded_slots_use_the_configured_length(db) -> None:
    seed(db)

    assert _lengths(db) == {timedelta(minutes=30)}


@pytest.mark.usefixtures("thirty_minute_slots")
def test_existing_slots_keep_their_length(db) -> None:
    seed(db)
    before = _lengths(db)
    slots.SLOT_MINUTES = 15

    seed(db)

    # Every working interval is already covered, so no overlapping shorter slot is added
    assert before == _lengths(db) == {timedelta(minutes=30)}
