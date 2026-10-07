from collections.abc import Iterator
from datetime import UTC, date, datetime

import pytest
from fastapi.testclient import TestClient
from sqlalchemy import create_engine
from sqlalchemy.orm import Session, sessionmaker
from sqlalchemy.pool import StaticPool

import noshow_db.models  # noqa: F401
from admin_service.accounts_client import AccountRejected, AccountsUnavailable
from admin_service.config import Settings
from admin_service.create_admin import create_admin
from admin_service.dependencies import (
    get_accounts,
    get_now,
    get_overbooking,
    get_session,
    get_settings,
)
from admin_service.main import app
from admin_service.overbooking import OverbookingUnavailable
from noshow_db.base import Base
from noshow_db.models.core import Doctor

NOW = datetime(2026, 11, 10, 9, 0, tzinfo=UTC)
EMAIL = "admin@hospital.local"
PASSWORD = "correct horse battery"
INTERNAL = ("127.0.0.1", 50000)
# HTTPS so the client sends the Secure session cookie back
BASE_URL = "https://admin.test"


class FakeOverbooking:
    """KPIs and A/B summary of the overbooking service, kept in memory."""

    def __init__(self) -> None:
        self.kpis: dict[tuple[int, date], dict] = {}
        self.available = True

    def kpi(self, doctor_id: int, day: date) -> dict | None:
        if not self.available:
            raise OverbookingUnavailable("down")
        return self.kpis.get((doctor_id, day))

    def ab_summary(self, unit: str = "appointment") -> dict:
        if not self.available:
            raise OverbookingUnavailable("down")
        return {
            "unit": unit,
            "groups": [
                {"group": "reminder", "appointments": 40, "no_shows": 6, "no_show_rate": 0.15},
                {"group": "control", "appointments": 40, "no_shows": 10, "no_show_rate": 0.25},
            ],
            "difference": -0.1,
            "z": -1.13,
            "p_value": 0.258,
        }


class FakeAccounts:
    """The web backend's internal account API, recording the requests it gets."""

    def __init__(self) -> None:
        self.enabled = True
        self.requests: list[tuple[str, dict]] = []
        self.reject: str | None = None
        self.next_id = 100

    def _answer(self, kind: str, body: dict) -> None:
        if not self.enabled:
            raise AccountsUnavailable("INTERNAL_API_TOKEN is not set")
        self.requests.append((kind, body))
        if self.reject:
            raise AccountRejected(self.reject)
        self.next_id += 1

    def create_patient(self, patient: dict) -> dict:
        self._answer("patient", patient)
        return {
            "account_id": self.next_id,
            "patient_id": self.next_id + 1000,
            "national_id": patient["national_id"],
            "full_name": patient["full_name"],
            "email": patient["email"],
        }

    def create_doctor(self, doctor: dict) -> dict:
        self._answer("doctor", doctor)
        return {
            "account_id": self.next_id,
            "doctor_id": self.next_id + 1000,
            "full_name": doctor["full_name"],
            "specialty": doctor["specialty"],
            "email": doctor["email"],
            "slots_created": 18,
        }

    def reset_password(self, account_id: int, password: str) -> None:
        self._answer("reset", {"account_id": account_id, "password": password})


class Clock:
    def __init__(self) -> None:
        self.now = NOW

    def __call__(self) -> datetime:
        return self.now


@pytest.fixture
def session_factory() -> sessionmaker[Session]:
    engine = create_engine(
        "sqlite://", connect_args={"check_same_thread": False}, poolclass=StaticPool
    )
    Base.metadata.create_all(engine)
    factory = sessionmaker(bind=engine)
    with factory() as session:
        create_admin(session, EMAIL, PASSWORD)
        session.add_all([Doctor(full_name="Dr. Ada"), Doctor(full_name="Dr. Bora")])
        session.commit()
    return factory


@pytest.fixture
def overbooking() -> FakeOverbooking:
    return FakeOverbooking()


@pytest.fixture
def accounts() -> FakeAccounts:
    return FakeAccounts()


@pytest.fixture
def clock() -> Clock:
    return Clock()


@pytest.fixture
def client(
    session_factory: sessionmaker[Session],
    overbooking: FakeOverbooking,
    accounts: FakeAccounts,
    clock: Clock,
) -> Iterator[TestClient]:
    def override_session() -> Iterator[Session]:
        with session_factory() as session:
            yield session

    app.dependency_overrides[get_session] = override_session
    app.dependency_overrides[get_overbooking] = lambda: overbooking
    app.dependency_overrides[get_accounts] = lambda: accounts
    app.dependency_overrides[get_now] = clock
    app.dependency_overrides[get_settings] = lambda: Settings(max_failed_logins=3)
    with TestClient(app, base_url=BASE_URL, client=INTERNAL) as test_client:
        yield test_client
    app.dependency_overrides.clear()


@pytest.fixture
def log_in(client: TestClient):
    """Post the login form; the correct credentials by default."""

    def post(password: str = PASSWORD, email: str = EMAIL):
        return client.post("/login", data={"email": email, "password": password})

    return post
