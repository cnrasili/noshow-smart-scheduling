import os
import subprocess
import sys
from datetime import UTC, datetime, timedelta

import pytest
from sqlalchemy import func, select, update

from noshow_db.models.core import LoginFailure
from web_backend import auth
from web_backend.auth import (
    DEFAULT_MAX_FAILURES_PER_ADDRESS,
    DEFAULT_MAX_FAILURES_PER_NAME,
    LOCKOUT_WINDOW,
    MAX_FAILURES_PER_NAME,
    TOO_MANY_LOGINS,
    PatientLogin,
    _login_hash,
    read_login_limit,
)
from web_backend.national_id import fictional_national_id

PASSWORD = "test-password"
UNKNOWN_ID = "10000000078"


def _patient_login(client, national_id: str, password: str):
    return client.post(
        "/auth/login",
        json={"role": "patient", "national_id": national_id, "password": password},
    )


def _doctor_login(client, email: str, password: str):
    return client.post("/auth/login", json={"role": "doctor", "email": email, "password": password})


def _fail(client, national_id: str, times: int = MAX_FAILURES_PER_NAME) -> None:
    for _ in range(times):
        assert _patient_login(client, national_id, "wrong").status_code == 401


def _age_failures(db, by: timedelta) -> None:
    db.execute(update(LoginFailure).values(created_at=LoginFailure.created_at - by))
    db.commit()


def test_locked_login_refuses_the_correct_password(client, make_patient) -> None:
    patient = make_patient()
    _fail(client, patient.national_id)

    response = _patient_login(client, patient.national_id, PASSWORD)

    assert response.status_code == 429
    assert response.json() == {"detail": TOO_MANY_LOGINS}


def test_fewer_failures_than_the_limit_still_allow_login(client, make_patient) -> None:
    patient = make_patient()
    _fail(client, patient.national_id, MAX_FAILURES_PER_NAME - 1)

    assert _patient_login(client, patient.national_id, PASSWORD).status_code == 200


def test_login_works_again_after_the_window(client, db, make_patient) -> None:
    patient = make_patient()
    _fail(client, patient.national_id)
    _age_failures(db, LOCKOUT_WINDOW + timedelta(seconds=1))

    assert _patient_login(client, patient.national_id, PASSWORD).status_code == 200


def test_unknown_and_existing_names_get_the_same_answers(client, make_patient) -> None:
    patient = make_patient()
    known = [_patient_login(client, patient.national_id, "wrong") for _ in range(2)]
    unknown = [_patient_login(client, UNKNOWN_ID, "wrong") for _ in range(2)]

    assert [(r.status_code, r.json()) for r in known] == [
        (r.status_code, r.json()) for r in unknown
    ]


def test_unknown_name_is_locked_like_an_existing_one(client) -> None:
    _fail(client, UNKNOWN_ID)

    response = _patient_login(client, UNKNOWN_ID, "wrong")

    assert response.status_code == 429
    assert response.json() == {"detail": TOO_MANY_LOGINS}


def test_one_names_failures_do_not_block_another_account_from_the_same_address(
    client, make_patient
) -> None:
    ayse = make_patient(email="ayse@example.com", name="Ayşe Kaya")
    mehmet = make_patient(email="mehmet@example.com", name="Mehmet Demir")
    # All test requests come from the same client address, like browsers behind one gateway
    _fail(client, ayse.national_id)

    assert _patient_login(client, ayse.national_id, PASSWORD).status_code == 429
    assert _patient_login(client, mehmet.national_id, PASSWORD).status_code == 200


def test_failures_across_many_names_from_one_address_are_limited(
    client, make_patient, monkeypatch
) -> None:
    monkeypatch.setattr(auth, "MAX_FAILURES_PER_ADDRESS", 3)
    other = make_patient(email="other@example.com")
    for number in range(3):
        _fail(client, fictional_national_id(9000 + number), 1)

    response = _patient_login(client, other.national_id, PASSWORD)

    assert response.status_code == 429
    assert response.json() == {"detail": TOO_MANY_LOGINS}


def test_default_address_limit_is_reached_only_after_many_failures(
    client, db, make_patient
) -> None:
    other = make_patient(email="other@example.com")
    now = datetime.now(UTC)
    # Failures for different names from the test client's address
    db.add_all(
        LoginFailure(login_hash=f"{n:064d}", client_ip="testclient", created_at=now)
        for n in range(DEFAULT_MAX_FAILURES_PER_ADDRESS - 1)
    )
    db.commit()
    assert _patient_login(client, other.national_id, "wrong").status_code == 401

    assert _patient_login(client, other.national_id, PASSWORD).status_code == 429


def test_name_limit_follows_the_setting(client, make_patient, monkeypatch) -> None:
    monkeypatch.setattr(auth, "MAX_FAILURES_PER_NAME", 2)
    patient = make_patient()
    _fail(client, patient.national_id, 2)

    assert _patient_login(client, patient.national_id, PASSWORD).status_code == 429


def test_failures_of_one_name_lock_it_from_any_address(client, db, make_patient) -> None:
    patient = make_patient()
    body = PatientLogin(role="patient", national_id=patient.national_id, password="x")
    now = datetime.now(UTC)
    db.add_all(
        LoginFailure(login_hash=_login_hash(body), client_ip=f"10.0.0.{n}", created_at=now)
        for n in range(MAX_FAILURES_PER_NAME)
    )
    db.commit()

    assert _patient_login(client, patient.national_id, PASSWORD).status_code == 429


def test_doctor_logins_are_limited_too(client, make_doctor) -> None:
    make_doctor(email="doctor@example.com")
    for _ in range(MAX_FAILURES_PER_NAME):
        assert _doctor_login(client, "Doctor@Example.com", "wrong").status_code == 401

    assert _doctor_login(client, "doctor@example.com", PASSWORD).status_code == 429


def test_national_id_is_not_stored(client, db, make_patient) -> None:
    patient = make_patient()
    _fail(client, patient.national_id, 1)

    failure = db.scalar(select(LoginFailure))
    assert patient.national_id not in failure.login_hash
    assert len(failure.login_hash) == 64


def test_successful_login_clears_the_name_failures(client, db, make_patient) -> None:
    patient = make_patient()
    _fail(client, patient.national_id, 2)

    assert _patient_login(client, patient.national_id, PASSWORD).status_code == 200
    assert db.scalar(select(func.count()).select_from(LoginFailure)) == 0


def test_failures_outside_the_window_are_removed(client, db, make_patient) -> None:
    patient = make_patient()
    _fail(client, patient.national_id, 2)
    _age_failures(db, LOCKOUT_WINDOW + timedelta(minutes=1))

    _fail(client, patient.national_id, 1)

    assert db.scalar(select(func.count()).select_from(LoginFailure)) == 1


@pytest.mark.parametrize("value", [None, "", "  "])
def test_unset_limits_use_the_defaults(value) -> None:
    assert read_login_limit("LOGIN_MAX_FAILURES_PER_NAME", value, 5) == 5
    assert DEFAULT_MAX_FAILURES_PER_NAME == 5
    assert DEFAULT_MAX_FAILURES_PER_ADDRESS == 50


@pytest.mark.parametrize(("value", "limit"), [("3", 3), (" 100 ", 100), ("1", 1), ("10000", 10000)])
def test_limits_can_be_configured(value, limit) -> None:
    assert read_login_limit("LOGIN_MAX_FAILURES_PER_ADDRESS", value, 50) == limit


@pytest.mark.parametrize("value", ["abc", "2.5", "0", "-1", "10001"])
def test_invalid_limits_are_rejected(value) -> None:
    with pytest.raises(ValueError, match="LOGIN_MAX_FAILURES_PER_NAME must be a whole number"):
        read_login_limit("LOGIN_MAX_FAILURES_PER_NAME", value, 5)


def _start_backend(**limits: str) -> subprocess.CompletedProcess:
    return subprocess.run(
        [
            sys.executable,
            "-c",
            "import web_backend.main, web_backend.auth as a; "
            "print(a.MAX_FAILURES_PER_NAME, a.MAX_FAILURES_PER_ADDRESS)",
        ],
        env={**os.environ, **limits},
        capture_output=True,
        text=True,
    )


def test_backend_reads_the_limits_at_startup() -> None:
    result = _start_backend(LOGIN_MAX_FAILURES_PER_NAME="3", LOGIN_MAX_FAILURES_PER_ADDRESS="80")

    assert result.returncode == 0, result.stderr
    assert result.stdout.strip() == "3 80"


def test_backend_does_not_start_with_an_invalid_limit() -> None:
    result = _start_backend(LOGIN_MAX_FAILURES_PER_ADDRESS="many")

    assert result.returncode != 0
    assert "LOGIN_MAX_FAILURES_PER_ADDRESS must be a whole number from 1 to 10000" in result.stderr
