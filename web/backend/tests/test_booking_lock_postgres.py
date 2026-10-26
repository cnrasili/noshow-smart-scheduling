# Checks that concurrent bookings of one department day keep the daily overbook limit;
# needs a disposable PostgreSQL database
import os
import subprocess
import sys
import threading
import time
from collections.abc import Iterator
from datetime import UTC, date, datetime, timedelta
from pathlib import Path

import pytest
from fastapi import BackgroundTasks, HTTPException
from sqlalchemy import Engine, create_engine, text
from sqlalchemy.orm import Session

from noshow_db.models.core import UserAccount
from web_backend.appointments import BookingRequest, book
from web_backend.clinic import CLINIC_TZ, today
from web_backend.overbooking import BookingDecision

TEST_DATABASE_URL = os.getenv("NOSHOW_TEST_DATABASE_URL")
DB_DIR = Path(__file__).resolve().parents[3] / "db"

pytestmark = pytest.mark.skipif(not TEST_DATABASE_URL, reason="NOSHOW_TEST_DATABASE_URL is not set")

# The overbooking service's limit per department day
DAILY_OVERBOOK_LIMIT = 4


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


class SlowOverbookingService:
    """Counts the day's overbooks from committed appointments, like the overbooking service.

    It answers slowly, so a booking decided at the same time would see the same count.
    """

    def __init__(self, engine: Engine, day: date) -> None:
        self.engine = engine
        self.day = day

    def booking_decision(self, patient_id: int, slot_id: int, booking_date: date):
        with self.engine.connect() as conn:
            overbooks = conn.execute(
                text(
                    "SELECT coalesce(sum(n - 1), 0) FROM ("
                    "  SELECT count(*) AS n FROM appointments"
                    "  WHERE appointment_date = :day GROUP BY slot_id"
                    ") AS per_slot"
                ),
                {"day": self.day},
            ).scalar_one()
        time.sleep(0.5)
        allow = overbooks < DAILY_OVERBOOK_LIMIT
        return BookingDecision(allow=allow, overbook=allow, p_noshow=0.6, reason="test")

    def appointment_booked(self, *_) -> bool:
        return True


def _setup_day(engine: Engine, day: date) -> list[int]:
    """Five two-patient slots: three already overbooked, two with one patient each.

    Returns the ids of the two half-full slots.
    """
    with engine.begin() as conn:
        conn.execute(
            text(
                "TRUNCATE appointments, slots, user_accounts, doctors, patients "
                "RESTART IDENTITY CASCADE"
            )
        )
        for number in range(1, 11):
            conn.execute(
                text(
                    "INSERT INTO patients (patient_number, full_name, email, age, gender) "
                    "VALUES (:number, :name, :email, 30, 'F')"
                ),
                {"number": str(number), "name": f"Hasta {number}", "email": f"p{number}@test"},
            )
        conn.execute(text("INSERT INTO doctors (full_name) VALUES ('General Practice')"))
        slot_ids = []
        for hour in range(9, 14):
            start = datetime.combine(day, datetime.min.time(), CLINIC_TZ) + timedelta(hours=hour)
            slot_ids.append(
                conn.execute(
                    text(
                        "INSERT INTO slots (doctor_id, start_at, end_at) "
                        "VALUES (1, :start, :end) RETURNING id"
                    ),
                    {"start": start.astimezone(UTC), "end": start + timedelta(minutes=15)},
                ).scalar_one()
            )
        booked = [(slot_ids[0], 1), (slot_ids[0], 2), (slot_ids[1], 3), (slot_ids[1], 4)]
        booked += [(slot_ids[2], 5), (slot_ids[2], 6), (slot_ids[3], 7), (slot_ids[4], 8)]
        for slot_id, patient_id in booked:
            conn.execute(
                text(
                    "INSERT INTO appointments (patient_id, slot_id, appointment_date, "
                    "booking_date) VALUES (:patient_id, :slot_id, :day, :booked)"
                ),
                {"patient_id": patient_id, "slot_id": slot_id, "day": day, "booked": today()},
            )
    return slot_ids[3:]


def test_concurrent_overbooks_keep_the_daily_limit(engine: Engine) -> None:
    day = today() + timedelta(days=5)
    half_full = _setup_day(engine, day)
    service = SlowOverbookingService(engine, day)
    results: list[int] = []

    def book_as(patient_id: int, slot_id: int) -> None:
        account = UserAccount(role="patient", patient_id=patient_id)
        with Session(engine) as db:
            try:
                book(BookingRequest(slot_id=slot_id), account, db, service, BackgroundTasks())
                results.append(201)
            except HTTPException as error:
                results.append(error.status_code)

    threads = [
        threading.Thread(target=book_as, args=(9, half_full[0])),
        threading.Thread(target=book_as, args=(10, half_full[1])),
    ]
    for thread in threads:
        thread.start()
    for thread in threads:
        thread.join(timeout=10)

    assert sorted(results) == [201, 409]
    with engine.connect() as conn:
        overbooks = conn.execute(
            text(
                "SELECT coalesce(sum(n - 1), 0) FROM ("
                "  SELECT count(*) AS n FROM appointments GROUP BY slot_id"
                ") AS per_slot"
            )
        ).scalar_one()
    assert overbooks == DAILY_OVERBOOK_LIMIT
