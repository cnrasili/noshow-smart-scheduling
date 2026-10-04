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


def test_login_ignores_email_case_and_spaces(client, make_doctor) -> None:
    make_doctor(email="doctor@example.com")

    response = client.post(
        "/auth/login",
        json={"email": "  Doctor@Example.com ", "password": "test-password", "role": "doctor"},
    )

    assert response.status_code == 200
    assert response.json()["role"] == "doctor"


@pytest.mark.parametrize(
    ("email", "password"),
    [("patient@example.com", "wrong"), ("nobody@example.com", "test-password")],
)
def test_wrong_credentials_are_rejected(client, make_patient, email, password) -> None:
    make_patient()

    response = client.post(
        "/auth/login", json={"email": email, "password": password, "role": "patient"}
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
    make_patient()
    token = client.post(
        "/auth/login",
        json={"email": "patient@example.com", "password": "test-password", "role": "patient"},
    ).json()["token"]

    stored = db.scalars(select(AuthSession)).one()
    assert stored.token_hash != token
    assert len(stored.token_hash) == 64


def test_doctor_profile_includes_specialty(client, make_doctor, login) -> None:
    make_doctor()

    response = client.get("/auth/me", headers=login("doctor@example.com"))

    assert response.json()["specialty"] == "General"


@pytest.mark.parametrize(
    ("make", "email", "form"),
    [
        ("make_doctor", "doctor@example.com", "patient"),
        ("make_patient", "patient@example.com", "doctor"),
    ],
)
def test_accounts_sign_in_only_through_their_own_form(request, client, make, email, form):
    request.getfixturevalue(make)()

    response = client.post(
        "/auth/login", json={"email": email, "password": "test-password", "role": form}
    )

    # Same answer as a wrong password, so the e-mail's role is not revealed
    assert response.status_code == 401
    assert response.json()["detail"] == "Wrong email or password"


def test_login_requires_a_role(client, make_patient) -> None:
    make_patient()

    response = client.post(
        "/auth/login", json={"email": "patient@example.com", "password": "test-password"}
    )

    assert response.status_code == 422
