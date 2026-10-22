from datetime import time

import pytest
from sqlalchemy import func, select

from noshow_db.models.core import AuthSession, DoctorSchedule, Patient, Slot, UserAccount
from web_backend.accounts import (
    DuplicateAccountError,
    NewDoctor,
    PatientNotFoundError,
    WorkingHours,
    create_doctor,
    open_patient_account,
)
from web_backend.security import verify_password

TOKEN = "internal-test-token"
HEADERS = {"X-Internal-Token": TOKEN}

NUMBER = "29872499824296"
EMAIL = f"{NUMBER}@hasta.sehirhastanesi.example"
PATIENT = {"patient_number": NUMBER, "password": "initial-pass"}

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


@pytest.fixture
def patient(db) -> Patient:
    """A patient of the dataset as the loading command stores it, without an account."""
    patient = Patient(
        patient_number=NUMBER, full_name=f"Hasta {NUMBER}", email=EMAIL, age=41, gender="F"
    )
    db.add(patient)
    db.commit()
    return patient


def _patient_count(db) -> int:
    return db.scalar(select(func.count()).select_from(Patient))


def test_opens_an_account_for_a_dataset_patient(client, db, patient) -> None:
    response = client.post("/internal/accounts/patients", json=PATIENT, headers=HEADERS)

    assert response.status_code == 201
    assert response.json() == {
        "account_id": response.json()["account_id"],
        "patient_id": patient.id,
        "patient_number": NUMBER,
        "full_name": f"Hasta {NUMBER}",
        "email": EMAIL,
    }
    account = db.get(UserAccount, response.json()["account_id"])
    assert account.role == "patient"
    assert account.email == EMAIL
    assert "initial-pass" not in account.password_hash
    assert _patient_count(db) == 1

    login = client.post(
        "/auth/login",
        json={"role": "patient", "patient_number": NUMBER, "password": "initial-pass"},
    )
    assert login.status_code == 200


def test_the_patient_number_is_trimmed(client, patient) -> None:
    response = client.post(
        "/internal/accounts/patients",
        json={**PATIENT, "patient_number": f" {NUMBER} "},
        headers=HEADERS,
    )

    assert response.status_code == 201


def test_no_patient_is_created_for_an_unknown_number(client, db, patient) -> None:
    response = client.post(
        "/internal/accounts/patients",
        json={**PATIENT, "patient_number": "11111111111"},
        headers=HEADERS,
    )

    assert response.status_code == 404
    assert response.json()["detail"] == "Patient not found"
    assert _patient_count(db) == 1
    assert db.scalar(select(func.count()).select_from(UserAccount)) == 0


def test_a_patient_gets_only_one_account(client, patient) -> None:
    client.post("/internal/accounts/patients", json=PATIENT, headers=HEADERS)

    response = client.post(
        "/internal/accounts/patients",
        json={**PATIENT, "password": "other-password"},
        headers=HEADERS,
    )

    assert response.status_code == 409
    assert response.json()["detail"] == "Patient already has an account"


def test_the_patient_email_must_be_unused(client, make_department, patient) -> None:
    make_department(username=EMAIL)

    response = client.post("/internal/accounts/patients", json=PATIENT, headers=HEADERS)

    assert response.status_code == 409
    assert response.json()["detail"] == "Email already in use"


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
        json={"role": "department", "username": "dr.demo@example.com", "password": "initial-pass"},
    )
    assert login.status_code == 200


def test_doctor_email_must_be_unused(client, patient) -> None:
    response = client.post(
        "/internal/accounts/doctors",
        json={**DOCTOR, "email": EMAIL},
        headers=HEADERS,
    )

    assert response.status_code == 409
    assert response.json()["detail"] == "Email already in use"


@pytest.mark.parametrize(
    "body",
    [
        {**PATIENT, "password": "short"},
        {**PATIENT, "patient_number": "  "},
        {**PATIENT, "patient_number": "1" * 21},
        {"password": "initial-pass"},
        # The format before the dataset rules, which created a patient
        {"full_name": "Deniz Demo", "age": 41, "gender": "F", "password": "initial-pass"},
    ],
)
def test_invalid_requests_are_rejected(client, db, patient, body) -> None:
    response = client.post("/internal/accounts/patients", json=body, headers=HEADERS)

    assert response.status_code == 422
    assert db.scalar(select(func.count()).select_from(UserAccount)) == 0


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


def test_password_reset_replaces_the_password_and_ends_sessions(client, db, patient) -> None:
    account_id = client.post("/internal/accounts/patients", json=PATIENT, headers=HEADERS).json()[
        "account_id"
    ]
    credentials = {"role": "patient", "patient_number": NUMBER, "password": "initial-pass"}
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


def test_user_session_token_does_not_open_the_internal_api(client, make_department, login) -> None:
    make_department()

    response = client.post(
        "/internal/accounts/patients", json=PATIENT, headers=login("aile.hekimligi")
    )

    assert response.status_code == 401


def test_internal_api_is_not_in_the_public_documentation(client) -> None:
    paths = client.get("/openapi.json").json()["paths"]

    assert not [path for path in paths if path.startswith("/internal")]


def test_account_module_rejects_duplicates_without_the_api(db, patient) -> None:
    open_patient_account(db, NUMBER, "initial-pass")

    with pytest.raises(DuplicateAccountError, match="Patient already has an account"):
        open_patient_account(db, NUMBER, "other-password")


def test_account_module_never_creates_a_patient(db) -> None:
    with pytest.raises(PatientNotFoundError):
        open_patient_account(db, NUMBER, "initial-pass")

    assert _patient_count(db) == 0


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
