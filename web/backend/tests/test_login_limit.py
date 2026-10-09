from datetime import UTC, datetime, timedelta

from sqlalchemy import func, select, update

from noshow_db.models.core import LoginFailure
from web_backend.auth import (
    LOCKOUT_WINDOW,
    MAX_FAILED_LOGINS,
    TOO_MANY_LOGINS,
    PatientLogin,
    _login_hash,
)

PASSWORD = "test-password"
UNKNOWN_ID = "10000000078"


def _patient_login(client, national_id: str, password: str):
    return client.post(
        "/auth/login",
        json={"role": "patient", "national_id": national_id, "password": password},
    )


def _doctor_login(client, email: str, password: str):
    return client.post("/auth/login", json={"role": "doctor", "email": email, "password": password})


def _fail(client, national_id: str, times: int = MAX_FAILED_LOGINS) -> None:
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
    _fail(client, patient.national_id, MAX_FAILED_LOGINS - 1)

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


def test_failures_from_one_address_lock_other_accounts(client, make_patient) -> None:
    other = make_patient(email="other@example.com")
    # All test requests come from the same client address
    _fail(client, UNKNOWN_ID)

    assert _patient_login(client, other.national_id, PASSWORD).status_code == 429


def test_failures_of_one_name_lock_it_from_any_address(client, db, make_patient) -> None:
    patient = make_patient()
    body = PatientLogin(role="patient", national_id=patient.national_id, password="x")
    now = datetime.now(UTC)
    db.add_all(
        LoginFailure(login_hash=_login_hash(body), client_ip=f"10.0.0.{n}", created_at=now)
        for n in range(MAX_FAILED_LOGINS)
    )
    db.commit()

    assert _patient_login(client, patient.national_id, PASSWORD).status_code == 429


def test_doctor_logins_are_limited_too(client, make_doctor) -> None:
    make_doctor(email="doctor@example.com")
    for _ in range(MAX_FAILED_LOGINS):
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
