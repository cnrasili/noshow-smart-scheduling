from datetime import time

import pytest
from pydantic import ValidationError
from sqlalchemy import func, select

from noshow_db.models.core import AuthSession, DoctorSchedule, Patient, Slot, UserAccount
from web_backend.accounts import (
    DuplicateAccountError,
    NewDoctor,
    NewPatient,
    WorkingHours,
    create_doctor,
    create_patient,
)
from web_backend.security import verify_password

TOKEN = "internal-test-token"
HEADERS = {"X-Internal-Token": TOKEN}

PATIENT = {
    "national_id": "10000000146",
    "full_name": "Deniz Demo",
    "email": "Deniz@Example.com",
    "age": 41,
    "gender": "F",
    "hipertension": True,
    "password": "initial-pass",
}

DOCTOR = {
    "full_name": "Dr. Demo",
    "specialty": "Dahiliye",
    "email": "dr.demo@example.com",
    "password": "initial-pass",
    # Every day, so the next two weeks always get slots
    "working_hours": [
        {"weekday": day, "start_time": "09:00", "end_time": "10:00"} for day in range(7)
    ],
}


@pytest.fixture(autouse=True)
def service_token(monkeypatch) -> None:
    monkeypatch.setenv("INTERNAL_API_TOKEN", TOKEN)


def test_creates_a_patient_who_can_log_in(client, db) -> None:
    response = client.post("/internal/accounts/patients", json=PATIENT, headers=HEADERS)

    assert response.status_code == 201
    created = response.json()
    assert created["national_id"] == "10000000146"
    assert created["email"] == "deniz@example.com"
    patient = db.get(Patient, created["patient_id"])
    assert patient.hipertension is True
    assert patient.age == 41
    account = db.get(UserAccount, created["account_id"])
    assert account.role == "patient"
    assert "initial-pass" not in account.password_hash

    login = client.post(
        "/auth/login",
        json={"role": "patient", "national_id": "10000000146", "password": "initial-pass"},
    )
    assert login.status_code == 200


def test_creates_a_doctor_with_working_hours_and_slots(client, db) -> None:
    response = client.post("/internal/accounts/doctors", json=DOCTOR, headers=HEADERS)

    assert response.status_code == 201
    created = response.json()
    doctor_id = created["doctor_id"]
    assert created["specialty"] == "Dahiliye"
    assert db.scalar(select(func.count()).where(DoctorSchedule.doctor_id == doctor_id)) == 7
    slots = db.scalar(select(func.count()).where(Slot.doctor_id == doctor_id))
    assert slots == created["slots_created"] > 0

    login = client.post(
        "/auth/login",
        json={"role": "doctor", "email": "dr.demo@example.com", "password": "initial-pass"},
    )
    assert login.status_code == 200


@pytest.mark.parametrize(
    ("change", "detail"),
    [
        ({"email": "other@example.com"}, "National ID number already registered"),
        ({"national_id": "99999000184"}, "Email already in use"),
    ],
)
def test_duplicate_patients_are_rejected(client, db, change, detail) -> None:
    client.post("/internal/accounts/patients", json=PATIENT, headers=HEADERS)

    response = client.post(
        "/internal/accounts/patients", json={**PATIENT, **change}, headers=HEADERS
    )

    assert response.status_code == 409
    assert response.json()["detail"] == detail
    assert db.scalar(select(func.count()).select_from(Patient)) == 1


def test_doctor_email_must_be_unused(client) -> None:
    client.post("/internal/accounts/patients", json=PATIENT, headers=HEADERS)

    response = client.post(
        "/internal/accounts/doctors",
        json={**DOCTOR, "email": "deniz@example.com"},
        headers=HEADERS,
    )

    assert response.status_code == 409
    assert response.json()["detail"] == "Email already in use"


@pytest.mark.parametrize(
    "change",
    [
        {"national_id": "10000000147"},
        {"national_id": "1000000014"},
        {"email": "not-an-email"},
        {"gender": "X"},
        {"age": -1},
        {"handcap": 5},
        {"password": "short"},
        {"full_name": "  "},
    ],
)
def test_invalid_patients_are_rejected(client, db, change) -> None:
    response = client.post(
        "/internal/accounts/patients", json={**PATIENT, **change}, headers=HEADERS
    )

    assert response.status_code == 422
    assert db.scalar(select(func.count()).select_from(Patient)) == 0


@pytest.mark.parametrize(
    "hours",
    [
        [],
        [{"weekday": 7, "start_time": "09:00", "end_time": "10:00"}],
        [{"weekday": 0, "start_time": "10:00", "end_time": "09:00"}],
        [
            {"weekday": 0, "start_time": "09:00", "end_time": "10:00"},
            {"weekday": 0, "start_time": "13:00", "end_time": "14:00"},
        ],
    ],
)
def test_invalid_working_hours_are_rejected(client, hours) -> None:
    response = client.post(
        "/internal/accounts/doctors", json={**DOCTOR, "working_hours": hours}, headers=HEADERS
    )

    assert response.status_code == 422


def test_password_reset_replaces_the_password_and_ends_sessions(client, db) -> None:
    account_id = client.post("/internal/accounts/patients", json=PATIENT, headers=HEADERS).json()[
        "account_id"
    ]
    credentials = {"role": "patient", "national_id": "10000000146", "password": "initial-pass"}
    token = client.post("/auth/login", json=credentials).json()["token"]

    response = client.put(
        f"/internal/accounts/{account_id}/password",
        json={"password": "new-password"},
        headers=HEADERS,
    )

    assert response.status_code == 204
    assert verify_password("new-password", db.get(UserAccount, account_id).password_hash)
    assert db.scalars(select(AuthSession)).all() == []
    assert client.get("/auth/me", headers={"Authorization": f"Bearer {token}"}).status_code == 401
    assert client.post("/auth/login", json=credentials).status_code == 401
    new_credentials = {**credentials, "password": "new-password"}
    assert client.post("/auth/login", json=new_credentials).status_code == 200


def test_password_reset_of_an_unknown_account(client) -> None:
    response = client.put(
        "/internal/accounts/999/password", json={"password": "new-password"}, headers=HEADERS
    )

    assert response.status_code == 404


def test_password_reset_checks_the_length(client) -> None:
    response = client.put(
        "/internal/accounts/1/password", json={"password": "short"}, headers=HEADERS
    )

    assert response.status_code == 422


REQUESTS = [
    ("post", "/internal/accounts/patients", PATIENT),
    ("post", "/internal/accounts/doctors", DOCTOR),
    ("put", "/internal/accounts/1/password", {"password": "new-password"}),
]


@pytest.mark.parametrize(("method", "path", "body"), REQUESTS)
@pytest.mark.parametrize("headers", [{}, {"X-Internal-Token": "wrong"}])
def test_requests_without_the_service_token_are_rejected(client, db, method, path, body, headers):
    response = client.request(method, path, json=body, headers=headers)

    assert response.status_code == 401
    assert db.scalar(select(func.count()).select_from(UserAccount)) == 0


@pytest.mark.parametrize(("method", "path", "body"), REQUESTS)
def test_api_is_disabled_without_a_configured_token(client, monkeypatch, method, path, body):
    monkeypatch.delenv("INTERNAL_API_TOKEN")

    response = client.request(method, path, json=body, headers=HEADERS)

    assert response.status_code == 503


def test_user_session_token_does_not_open_the_internal_api(client, make_doctor, login) -> None:
    make_doctor()

    response = client.post(
        "/internal/accounts/patients", json=PATIENT, headers=login("doctor@example.com")
    )

    assert response.status_code == 401


def test_internal_api_is_not_in_the_public_documentation(client) -> None:
    paths = client.get("/openapi.json").json()["paths"]

    assert not [path for path in paths if path.startswith("/internal")]


def test_account_module_rejects_duplicates_without_the_api(db) -> None:
    create_patient(db, NewPatient(**PATIENT))

    with pytest.raises(DuplicateAccountError, match="National ID number already registered"):
        create_patient(db, NewPatient(**{**PATIENT, "email": "other@example.com"}))


def test_account_module_creates_a_doctor_without_slots(db) -> None:
    account = create_doctor(
        db,
        NewDoctor(
            full_name="Dr. Module",
            specialty="Kardiyoloji",
            email="module@example.com",
            password="initial-pass",
            working_hours=[WorkingHours(weekday=1, start_time=time(9), end_time=time(12))],
        ),
    )

    assert account.role == "doctor"
    assert db.scalar(select(func.count()).select_from(Slot)) == 0


def test_new_patient_validates_the_national_id() -> None:
    with pytest.raises(ValidationError, match="Invalid national ID number"):
        NewPatient(**{**PATIENT, "national_id": "12345678901"})
