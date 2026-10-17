from collections.abc import Callable, Iterator
from datetime import UTC, date, datetime, time, timedelta

import pytest
from fastapi.testclient import TestClient
from sqlalchemy import create_engine, select
from sqlalchemy.orm import Session, sessionmaker
from sqlalchemy.pool import StaticPool

import noshow_db.models  # noqa: F401
from noshow_db.base import Base
from noshow_db.models.core import Appointment, Doctor, Patient, Slot
from overbooking_service.config import settings
from overbooking_service.dependencies import get_data_source, get_session
from overbooking_service.features import PastAppointment, PatientRecord
from overbooking_service.main import app


class FakeDataSource:
    """In-memory patient data for tests."""

    def __init__(self) -> None:
        self.patients = {
            1: PatientRecord(1, 30, "F", False, False, False, False, 0),
        }
        self.history = {
            1: [
                PastAppointment(date(2026, 1, 10), attended=True),
                PastAppointment(date(2026, 3, 5), attended=False),
            ],
        }

    def get_patient(self, patient_id: int) -> PatientRecord | None:
        return self.patients.get(patient_id)

    def get_history(self, patient_id: int) -> list[PastAppointment]:
        return self.history.get(patient_id, [])


CLINIC_PATIENTS = 8


def make_clinic(session: Session, today: date) -> None:
    """The department's schedule, patients, slots and bookings, like the web backend seed.

    The department works on weekdays 08:00-12:00 in 16 slots of 15 minutes, from three weeks
    before today to two weeks after it. Every other slot of the last past working day is booked.
    """
    tz = settings.clinic_timezone
    # The department's schedule is its one record in doctors
    session.add(Doctor(full_name="General Practice"))
    session.add_all(
        Patient(
            full_name=f"Patient {n}",
            email=f"patient{n}@demo.local",
            age=30 + n,
            gender="F",
        )
        for n in range(1, CLINIC_PATIENTS + 1)
    )
    session.flush()
    days = [today + timedelta(days=d) for d in range(-21, 15)]
    days = [day for day in days if day.weekday() < 5]
    for day in days:
        start = datetime.combine(day, time(8), tz)
        session.add_all(
            Slot(
                doctor_id=1,
                start_at=(start + timedelta(minutes=15 * k)).astimezone(UTC),
                end_at=(start + timedelta(minutes=15 * (k + 1))).astimezone(UTC),
            )
            for k in range(16)
        )
    session.flush()

    last_past = max(day for day in days if day < today)
    first = datetime.combine(last_past, time(8), tz).astimezone(UTC)
    slots = session.scalars(
        select(Slot).where(Slot.start_at >= first).order_by(Slot.start_at).limit(16)
    ).all()
    for patient_id, slot in enumerate(slots[::2], start=1):
        session.add(
            Appointment(
                patient_id=patient_id,
                slot_id=slot.id,
                appointment_date=last_past,
                booking_date=last_past - timedelta(days=5),
            )
        )
    session.commit()


@pytest.fixture(scope="session")
def clinic() -> Callable[[Session, date], None]:
    return make_clinic


@pytest.fixture
def session_factory() -> sessionmaker[Session]:
    engine = create_engine(
        "sqlite://", connect_args={"check_same_thread": False}, poolclass=StaticPool
    )
    Base.metadata.create_all(engine)
    return sessionmaker(bind=engine)


@pytest.fixture
def client(
    session_factory: sessionmaker[Session], monkeypatch: pytest.MonkeyPatch
) -> Iterator[TestClient]:
    # Background dispatcher would use the real database
    monkeypatch.setattr(settings.reminders, "enabled", False)

    def override_session() -> Iterator[Session]:
        with session_factory() as session:
            yield session

    app.dependency_overrides[get_session] = override_session
    app.dependency_overrides[get_data_source] = FakeDataSource
    with TestClient(app) as test_client:
        yield test_client
    app.dependency_overrides.clear()
