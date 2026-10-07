import json
from collections.abc import Callable, Iterator

import httpx2
import pytest
from fastapi.testclient import TestClient
from sqlalchemy import create_engine, select
from sqlalchemy.orm import Session, sessionmaker
from sqlalchemy.pool import StaticPool

import noshow_db.models  # noqa: F401
from noshow_db.base import Base
from noshow_db.models.core import Doctor, Patient, UserAccount
from web_backend.db import get_db
from web_backend.main import app
from web_backend.national_id import fictional_national_id
from web_backend.overbooking import OverbookingClient, get_overbooking_client
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


class FakeOverbookingService:
    """Stands in for the overbooking service; unreachable until a test sets `respond`."""

    def __init__(self) -> None:
        self.requests: list[dict] = []
        self.respond: Callable[[dict], httpx2.Response] | None = None

    @property
    def decisions(self) -> list[dict]:
        return [r for r in self.requests if r["path"] == "/booking-decision"]

    @property
    def events(self) -> list[dict]:
        return [r for r in self.requests if r["path"].startswith("/events/")]

    def allow(self, overbook: bool = False) -> None:
        self.respond = lambda _: httpx2.Response(
            200, json={"allow": True, "overbook": overbook, "p_noshow": 0.4, "reason": "ok"}
        )

    def reject(self) -> None:
        self.respond = lambda _: httpx2.Response(
            200, json={"allow": False, "overbook": False, "p_noshow": 0.1, "reason": "low risk"}
        )

    def handle(self, request: httpx2.Request) -> httpx2.Response:
        body = json.loads(request.content)
        self.requests.append({"path": request.url.path, **body})
        if self.respond is None:
            raise httpx2.ConnectError("Overbooking service is not running", request=request)
        return self.respond(body)


@pytest.fixture
def overbooking() -> FakeOverbookingService:
    return FakeOverbookingService()


@pytest.fixture
def client(db: Session, overbooking: FakeOverbookingService) -> Iterator[TestClient]:
    app.dependency_overrides[get_db] = lambda: db
    app.dependency_overrides[get_overbooking_client] = lambda: OverbookingClient(
        base_url="http://overbooking.test", transport=httpx2.MockTransport(overbooking.handle)
    )
    with TestClient(app) as test_client:
        yield test_client
    app.dependency_overrides.clear()


@pytest.fixture
def make_patient(db: Session) -> Callable[..., Patient]:
    numbers = iter(range(1, 10000))

    def make(
        email: str = "patient@example.com",
        name: str = "Test Patient",
        national_id: str | None = None,
    ) -> Patient:
        patient = Patient(
            national_id=national_id or fictional_national_id(next(numbers)),
            full_name=name,
            email=email,
            age=30,
            gender="F",
        )
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
def login(client: TestClient, db: Session) -> Callable[[str], dict[str, str]]:
    """Sign in through the account's own login form and return the Authorization header.

    Accounts are looked up by e-mail; patients then sign in with their national ID number.
    """

    def sign_in(email: str) -> dict[str, str]:
        account = db.scalar(select(UserAccount).where(UserAccount.email == email))
        if account.role == "patient":
            national_id = db.get(Patient, account.patient_id).national_id
            body = {"role": "patient", "national_id": national_id, "password": PASSWORD}
        else:
            body = {"role": "doctor", "email": email, "password": PASSWORD}
        response = client.post("/auth/login", json=body)
        assert response.status_code == 200, response.text
        return {"Authorization": f"Bearer {response.json()['token']}"}

    return sign_in
