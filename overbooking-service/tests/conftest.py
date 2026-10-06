from collections.abc import Callable, Iterator
from datetime import UTC, date, datetime, time, timedelta

import pytest
from fastapi.testclient import TestClient
from sqlalchemy import create_engine
from sqlalchemy.orm import Session, sessionmaker
from sqlalchemy.pool import StaticPool

import noshow_db.models  # noqa: F401
from noshow_db.base import Base
from noshow_db.models.core import Doctor, Slot
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


def add_clinic(session: Session, first_day: date, last_day: date) -> None:
    """A small stand-in for the web backend seed: two doctors with 20-minute weekday slots."""
    session.add_all(
        [Doctor(id=1, full_name="Dr. Ada Demir"), Doctor(id=2, full_name="Dr. Bora Kaya")]
    )
    day = first_day
    while day <= last_day:
        if day.weekday() < 5:
            for doctor_id, start_hour in ((1, 9), (2, 13)):
                start = datetime.combine(day, time(start_hour), settings.clinic_timezone)
                session.add_all(
                    Slot(
                        doctor_id=doctor_id,
                        start_at=(start + timedelta(minutes=20 * k)).astimezone(UTC),
                        end_at=(start + timedelta(minutes=20 * (k + 1))).astimezone(UTC),
                    )
                    for k in range(6)
                )
        day += timedelta(days=1)
    session.flush()


@pytest.fixture(scope="session")
def clinic() -> Callable[[Session, date, date], None]:
    return add_clinic


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
