from collections.abc import Iterator
from datetime import date

import pytest
from fastapi.testclient import TestClient
from sqlalchemy import create_engine
from sqlalchemy.orm import Session, sessionmaker
from sqlalchemy.pool import StaticPool

import noshow_db.models  # noqa: F401
from noshow_db.base import Base
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


@pytest.fixture
def session_factory() -> sessionmaker[Session]:
    engine = create_engine(
        "sqlite://", connect_args={"check_same_thread": False}, poolclass=StaticPool
    )
    Base.metadata.create_all(engine)
    return sessionmaker(bind=engine)


@pytest.fixture
def client(session_factory: sessionmaker[Session]) -> Iterator[TestClient]:
    def override_session() -> Iterator[Session]:
        with session_factory() as session:
            yield session

    app.dependency_overrides[get_session] = override_session
    app.dependency_overrides[get_data_source] = FakeDataSource
    with TestClient(app) as test_client:
        yield test_client
    app.dependency_overrides.clear()
