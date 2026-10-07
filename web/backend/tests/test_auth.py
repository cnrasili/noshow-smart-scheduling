from datetime import UTC, datetime, timedelta

import pytest
from sqlalchemy import select, update

from noshow_db.models.core import AuthSession
from web_backend.security import hash_password, verify_password


def test_password_hash_round_trip() -> None:
    stored = hash_password("secret")
    assert stored.startswith("scrypt$")
    assert "secret" not in stored
    assert verify_password("secret", stored)
    assert not verify_password("wrong", stored)


@pytest.mark.parametrize("stored", ["", "plain", "bcrypt$1$2$3$aa$bb", "scrypt$x$8$1$aa$bb"])
def test_malformed_hashes_never_verify(stored: str) -> None:
    assert not verify_password("secret", stored)


def test_patient_logs_in_and_reads_profile(client, make_patient, login) -> None:
    make_patient(email="ayse@example.com", name="Ayse Demo")
    headers = login("ayse@example.com")

    response = client.get("/auth/me", headers=headers)

    assert response.status_code == 200
    assert response.json() == {
        "role": "patient",
        "name": "Ayse Demo",
        "email": "ayse@example.com",
        "specialty": None,
    }


def test_patient_logs_in_with_national_id(client, make_patient) -> None:
    make_patient(national_id="10000000146")

    response = client.post(
        "/auth/login",
        json={"role": "patient", "national_id": " 10000000146 ", "password": "test-password"},
    )

    assert response.status_code == 200
    assert response.json()["role"] == "patient"


def test_patient_form_no_longer_accepts_an_email(client, make_patient) -> None:
    make_patient(email="patient@example.com")

    response = client.post(
        "/auth/login",
        json={"role": "patient", "email": "patient@example.com", "password": "test-password"},
    )

    assert response.status_code == 422


def test_patient_email_is_not_a_login_name(client, make_patient) -> None:
    make_patient(email="patient@example.com")

    response = client.post(
        "/auth/login",
        json={"role": "patient", "national_id": "patient@example.com", "password": "test-password"},
    )

    assert response.status_code == 401
    assert response.json()["detail"] == "Wrong national ID number or password"


def test_doctor_login_ignores_email_case_and_spaces(client, make_doctor) -> None:
    make_doctor(email="doctor@example.com")

    response = client.post(
        "/auth/login",
        json={"email": "  Doctor@Example.com ", "password": "test-password", "role": "doctor"},
    )

    assert response.status_code == 200
    assert response.json()["role"] == "doctor"


@pytest.mark.parametrize(
    ("national_id", "password"),
    [
        ("10000000146", "wrong"),
        # Valid but unknown, and invalid check digits
        ("99999000184", "test-password"),
        ("10000000147", "test-password"),
    ],
)
def test_wrong_patient_credentials_are_rejected(client, make_patient, national_id, password):
    make_patient(national_id="10000000146")

    response = client.post(
        "/auth/login",
        json={"role": "patient", "national_id": national_id, "password": password},
    )

    assert response.status_code == 401
    assert response.json()["detail"] == "Wrong national ID number or password"


@pytest.mark.parametrize(
    ("email", "password"),
    [("doctor@example.com", "wrong"), ("nobody@example.com", "test-password")],
)
def test_wrong_doctor_credentials_are_rejected(client, make_doctor, email, password) -> None:
    make_doctor()

    response = client.post(
        "/auth/login", json={"email": email, "password": password, "role": "doctor"}
    )

    assert response.status_code == 401
    assert response.json()["detail"] == "Wrong email or password"


@pytest.mark.parametrize("headers", [{}, {"Authorization": "Bearer not-a-token"}])
def test_me_requires_a_valid_token(client, headers) -> None:
    assert client.get("/auth/me", headers=headers).status_code == 401


def test_expired_session_is_rejected(client, db, make_patient, login) -> None:
    make_patient()
    headers = login("patient@example.com")
    db.execute(update(AuthSession).values(expires_at=datetime.now(UTC) - timedelta(minutes=1)))
    db.commit()

    assert client.get("/auth/me", headers=headers).status_code == 401


def test_logout_ends_the_session(client, db, make_patient, login) -> None:
    make_patient()
    headers = login("patient@example.com")

    assert client.post("/auth/logout", headers=headers).status_code == 204
    assert client.get("/auth/me", headers=headers).status_code == 401
    assert db.scalars(select(AuthSession)).all() == []


def test_token_is_stored_only_as_hash(client, db, make_patient) -> None:
    make_patient(national_id="10000000146")
    token = client.post(
        "/auth/login",
        json={"national_id": "10000000146", "password": "test-password", "role": "patient"},
    ).json()["token"]

    stored = db.scalars(select(AuthSession)).one()
    assert stored.token_hash != token
    assert len(stored.token_hash) == 64


def test_doctor_profile_includes_specialty(client, make_doctor, login) -> None:
    make_doctor()

    response = client.get("/auth/me", headers=login("doctor@example.com"))

    assert response.json()["specialty"] == "General"


def test_patient_email_does_not_open_the_doctor_form(client, make_patient) -> None:
    make_patient(email="patient@example.com")

    response = client.post(
        "/auth/login",
        json={"email": "patient@example.com", "password": "test-password", "role": "doctor"},
    )

    # Same answer as a wrong password, so the e-mail's role is not revealed
    assert response.status_code == 401
    assert response.json()["detail"] == "Wrong email or password"


def test_login_requires_a_role(client, make_doctor) -> None:
    make_doctor()

    response = client.post(
        "/auth/login", json={"email": "doctor@example.com", "password": "test-password"}
    )

    assert response.status_code == 422
