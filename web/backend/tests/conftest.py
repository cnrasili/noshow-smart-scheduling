from collections.abc import Callable, Iterator

import pytest
from fastapi.testclient import TestClient
from sqlalchemy import create_engine
from sqlalchemy.orm import Session, sessionmaker
from sqlalchemy.pool import StaticPool

import noshow_db.models  # noqa: F401
from noshow_db.base import Base
from noshow_db.models.core import Doctor, Patient, UserAccount
from web_backend.db import get_db
from web_backend.main import app
from web_backend.security import hash_password

PASSWORD = "test-password"


@pytest.fixture
def db() -> Iterator[Session]:
    engine = create_engine(
        "sqlite://", connect_args={"check_same_thread": False}, poolclass=StaticPool
    )
    Base.metadata.create_all(engine)
    with sessionmaker(bind=engine)() as db_session:
        yield db_session


@pytest.fixture
def client(db: Session) -> Iterator[TestClient]:
    app.dependency_overrides[get_db] = lambda: db
    with TestClient(app) as test_client:
        yield test_client
    app.dependency_overrides.clear()


@pytest.fixture
def make_patient(db: Session) -> Callable[..., Patient]:
    def make(email: str = "patient@example.com", name: str = "Test Patient") -> Patient:
        patient = Patient(full_name=name, email=email, age=30, gender="F")
        db.add(patient)
        db.flush()
        db.add(
            UserAccount(
                email=email,
                password_hash=hash_password(PASSWORD),
                role="patient",
                patient_id=patient.id,
            )
        )
        db.commit()
        return patient

    return make


@pytest.fixture
def make_doctor(db: Session) -> Callable[..., Doctor]:
    def make(email: str = "doctor@example.com", name: str = "Dr. Test") -> Doctor:
        doctor = Doctor(full_name=name, specialty="General")
        db.add(doctor)
        db.flush()
        db.add(
            UserAccount(
                email=email,
                password_hash=hash_password(PASSWORD),
                role="doctor",
                doctor_id=doctor.id,
            )
        )
        db.commit()
        return doctor

    return make


@pytest.fixture
def login(client: TestClient) -> Callable[[str], dict[str, str]]:
    """Sign in and return the Authorization header."""

    def sign_in(email: str) -> dict[str, str]:
        response = client.post("/auth/login", json={"email": email, "password": PASSWORD})
        assert response.status_code == 200, response.text
        return {"Authorization": f"Bearer {response.json()['token']}"}

    return sign_in
