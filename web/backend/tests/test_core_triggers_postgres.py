# Checks the PostgreSQL triggers of the core tables; needs a disposable database
import os
import subprocess
import sys
import threading
from collections.abc import Iterator
from datetime import UTC, date, datetime
from pathlib import Path

import pytest
from sqlalchemy import Engine, create_engine, text
from sqlalchemy.exc import IntegrityError

TEST_DATABASE_URL = os.getenv("NOSHOW_TEST_DATABASE_URL")
DB_DIR = Path(__file__).resolve().parents[3] / "db"

pytestmark = pytest.mark.skipif(not TEST_DATABASE_URL, reason="NOSHOW_TEST_DATABASE_URL is not set")

SLOT_DAY = date(2026, 11, 10)
NOV_2 = date(2026, 11, 2)


@pytest.fixture(scope="module")
def engine() -> Iterator[Engine]:
    db_engine = create_engine(TEST_DATABASE_URL)
    with db_engine.begin() as conn:
        conn.execute(text("DROP SCHEMA public CASCADE"))
        conn.execute(text("CREATE SCHEMA public"))
    subprocess.run(
        [sys.executable, "-m", "alembic", "upgrade", "head"],
        cwd=DB_DIR,
        env={**os.environ, "DATABASE_URL": TEST_DATABASE_URL},
        check=True,
        capture_output=True,
    )
    yield db_engine
    db_engine.dispose()


@pytest.fixture
def slot_id(engine: Engine) -> int:
    """A two-patient slot at 09:30 Istanbul time with three registered patients."""
    with engine.begin() as conn:
        conn.execute(
            text("TRUNCATE appointments, slots, doctors, patients RESTART IDENTITY CASCADE")
        )
        for number in (1, 2, 3):
            conn.execute(
                text(
                    "INSERT INTO patients (full_name, email, age, gender) "
                    "VALUES (:name, :email, 30, 'F')"
                ),
                {"name": f"Patient {number}", "email": f"p{number}@example.com"},
            )
        conn.execute(text("INSERT INTO doctors (full_name) VALUES ('Dr. Test')"))
        return conn.execute(
            text(
                "INSERT INTO slots (doctor_id, start_at, end_at) "
                "VALUES (1, :start, :end) RETURNING id"
            ),
            {
                "start": datetime(2026, 11, 10, 6, 30, tzinfo=UTC),
                "end": datetime(2026, 11, 10, 7, 0, tzinfo=UTC),
            },
        ).scalar_one()


def _book(conn, slot_id: int, patient_id: int, appointment_date: date = SLOT_DAY) -> None:
    conn.execute(
        text(
            "INSERT INTO appointments (patient_id, slot_id, appointment_date, booking_date) "
            "VALUES (:patient_id, :slot_id, :appointment_date, :booking_date)"
        ),
        {
            "patient_id": patient_id,
            "slot_id": slot_id,
            "appointment_date": appointment_date,
            "booking_date": NOV_2,
        },
    )


def test_slot_rejects_patients_beyond_capacity(engine: Engine, slot_id: int) -> None:
    with engine.begin() as conn:
        _book(conn, slot_id, 1)
        _book(conn, slot_id, 2)

    with pytest.raises(IntegrityError, match="is full"), engine.begin() as conn:
        _book(conn, slot_id, 3)


def test_concurrent_bookings_cannot_exceed_capacity(engine: Engine, slot_id: int) -> None:
    with engine.begin() as conn:
        _book(conn, slot_id, 1)

    errors: list[Exception] = []

    def book_third_patient() -> None:
        try:
            with engine.begin() as conn:
                _book(conn, slot_id, 3)
        except IntegrityError as error:
            errors.append(error)

    with engine.connect() as first:
        first.begin()
        _book(first, slot_id, 2)
        second = threading.Thread(target=book_third_patient)
        second.start()
        second.join(timeout=1)
        # The second booking waits for the lock on the slot row
        assert second.is_alive()
        first.commit()
    second.join(timeout=5)

    assert len(errors) == 1
    with engine.connect() as conn:
        count = conn.execute(text("SELECT count(*) FROM appointments")).scalar_one()
    assert count == 2


def test_appointment_date_must_match_slot_date(engine: Engine, slot_id: int) -> None:
    with pytest.raises(IntegrityError, match="does not match"), engine.begin() as conn:
        _book(conn, slot_id, 1, date(2026, 11, 11))


def test_slot_date_uses_clinic_timezone(engine: Engine) -> None:
    with engine.begin() as conn:
        conn.execute(
            text("TRUNCATE appointments, slots, doctors, patients RESTART IDENTITY CASCADE")
        )
        conn.execute(
            text(
                "INSERT INTO patients (full_name, email, age, gender) "
                "VALUES ('Patient', 'p@example.com', 30, 'F')"
            )
        )
        conn.execute(text("INSERT INTO doctors (full_name) VALUES ('Dr. Test')"))
        # 22:30 UTC on 9 November is 01:30 on 10 November in Istanbul
        late_slot = conn.execute(
            text(
                "INSERT INTO slots (doctor_id, start_at, end_at) "
                "VALUES (1, '2026-11-09 22:30+00', '2026-11-09 23:00+00') RETURNING id"
            )
        ).scalar_one()
        _book(conn, late_slot, 1, SLOT_DAY)


def test_booked_slot_cannot_move_to_another_date(engine: Engine, slot_id: int) -> None:
    with engine.begin() as conn:
        _book(conn, slot_id, 1)

    with pytest.raises(IntegrityError, match="another date"), engine.begin() as conn:
        conn.execute(
            text("UPDATE slots SET start_at = start_at + interval '1 day' WHERE id = :id"),
            {"id": slot_id},
        )


def test_slot_capacity_cannot_drop_below_bookings(engine: Engine, slot_id: int) -> None:
    with engine.begin() as conn:
        _book(conn, slot_id, 1)
        _book(conn, slot_id, 2)

    with pytest.raises(IntegrityError, match="more than max_patients"), engine.begin() as conn:
        conn.execute(text("UPDATE slots SET max_patients = 1 WHERE id = :id"), {"id": slot_id})


def test_booking_date_cannot_be_after_appointment_date(engine: Engine, slot_id: int) -> None:
    with pytest.raises(IntegrityError, match="ck_appointments_booked_before_date"):
        with engine.begin() as conn:
            conn.execute(
                text(
                    "INSERT INTO appointments "
                    "(patient_id, slot_id, appointment_date, booking_date) "
                    "VALUES (1, :slot_id, :day, :booked)"
                ),
                {"slot_id": slot_id, "day": SLOT_DAY, "booked": date(2026, 11, 11)},
            )
