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


NUMBER = "29872499824296"
# A dataset patient number written in exponent form in the CSV, stored converted
DECIMAL_NUMBER = "93779.52927"


def _patient_login(client, patient_number: str, password: str = "test-password"):
    return client.post(
        "/auth/login",
        json={"role": "patient", "patient_number": patient_number, "password": password},
    )


def _department_login(client, username: str, password: str = "test-password"):
    return client.post(
        "/auth/login", json={"role": "department", "username": username, "password": password}
    )


def test_patient_logs_in_and_reads_profile(client, make_patient, login) -> None:
    make_patient(email="ayse@example.com", patient_number=NUMBER)
    headers = login("ayse@example.com")

    response = client.get("/auth/me", headers=headers)

    assert response.status_code == 200
    assert response.json() == {"role": "patient", "name": f"Hasta {NUMBER}"}


@pytest.mark.parametrize("number", [NUMBER, DECIMAL_NUMBER])
def test_patient_logs_in_with_patient_number(client, make_patient, number) -> None:
    make_patient(patient_number=number)

    response = _patient_login(client, f" {number} ")

    assert response.status_code == 200
    assert response.json()["role"] == "patient"


def test_patient_form_accepts_only_the_patient_number(client, make_patient) -> None:
    make_patient(email="patient@example.com", patient_number=NUMBER)

    response = client.post(
        "/auth/login",
        json={"role": "patient", "email": "patient@example.com", "password": "test-password"},
    )

    assert response.status_code == 422


def test_patient_email_is_not_a_login_name(client, make_patient) -> None:
    make_patient(email="patient@example.com")

    response = _patient_login(client, "patient@example.com")

    assert response.status_code == 401
    assert response.json()["detail"] == "Wrong patient number or password"


def test_department_login_ignores_username_case_and_spaces(client, make_department) -> None:
    make_department()

    response = _department_login(client, "  Aile.Hekimligi ")

    assert response.status_code == 200
    assert response.json() == {
        "role": "department",
        "name": "General Practice",
        "token": response.json()["token"],
    }


@pytest.mark.parametrize(
    ("number", "password"),
    [
        (NUMBER, "wrong"),
        ("29872499824297", "test-password"),
        ("", "test-password"),
    ],
)
def test_wrong_patient_credentials_are_rejected(client, make_patient, number, password):
    make_patient(patient_number=NUMBER)

    response = _patient_login(client, number, password)

    assert response.status_code == 401
    assert response.json()["detail"] == "Wrong patient number or password"


@pytest.mark.parametrize(
    ("username", "password"),
    [("aile.hekimligi", "wrong"), ("nobody", "test-password")],
)
def test_wrong_department_credentials_are_rejected(
    client, make_department, username, password
) -> None:
    make_department()

    response = _department_login(client, username, password)

    assert response.status_code == 401
    assert response.json()["detail"] == "Wrong username or password"


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
    make_patient(patient_number=NUMBER)
    token = _patient_login(client, NUMBER).json()["token"]

    stored = db.scalars(select(AuthSession)).one()
    assert stored.token_hash != token
    assert len(stored.token_hash) == 64


def test_department_profile_names_only_the_department(client, make_department, login) -> None:
    make_department()

    response = client.get("/auth/me", headers=login("aile.hekimligi"))

    assert response.json() == {"role": "department", "name": "General Practice"}


def test_patient_email_does_not_open_the_department_form(client, make_patient) -> None:
    make_patient(email="patient@example.com")

    response = _department_login(client, "patient@example.com")

    # Same answer as a wrong password, so the e-mail's role is not revealed
    assert response.status_code == 401
    assert response.json()["detail"] == "Wrong username or password"


def test_patient_number_does_not_open_the_department_form(client, make_patient) -> None:
    make_patient(patient_number=NUMBER)

    assert _department_login(client, NUMBER).status_code == 401


def test_the_old_doctor_form_is_gone(client, make_department) -> None:
    make_department()

    response = client.post(
        "/auth/login",
        json={"role": "doctor", "email": "aile.hekimligi", "password": "test-password"},
    )

    assert response.status_code == 422


def test_login_requires_a_role(client, make_department) -> None:
    make_department()

    response = client.post(
        "/auth/login", json={"username": "aile.hekimligi", "password": "test-password"}
    )

    assert response.status_code == 422
