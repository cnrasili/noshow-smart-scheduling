import os
from datetime import UTC, datetime, timedelta
from typing import Annotated, Literal

from fastapi import APIRouter, Body, Depends, HTTPException, Request, Response, status
from fastapi.security import HTTPAuthorizationCredentials, HTTPBearer
from pydantic import BaseModel
from sqlalchemy import case, delete, func, or_, select
from sqlalchemy.orm import Session

from noshow_db.models.core import AuthSession, Doctor, LoginFailure, Patient, UserAccount
from web_backend.clinic import as_utc
from web_backend.db import get_db
from web_backend.national_id import is_valid_national_id
from web_backend.security import hash_password, hash_token, new_token, verify_password

SESSION_LIFETIME = timedelta(hours=12)
LOCKOUT_WINDOW = timedelta(minutes=15)
# Defaults of the failed-login limits within the window. The name limit stops guessing one
# account's password; the much higher address limit stops one client trying many names,
# without letting a few typos lock everyone who shares an address (a gateway or Docker host)
DEFAULT_MAX_FAILURES_PER_NAME = 5
DEFAULT_MAX_FAILURES_PER_ADDRESS = 50
MAX_FAILURES_LIMIT = 10_000


def read_login_limit(variable: str, value: str | None, default: int) -> int:
    """A failed-login limit from an environment value; the default when it is unset."""
    if value is None or not value.strip():
        return default
    try:
        limit = int(value)
    except ValueError:
        limit = None
    if limit is None or not 1 <= limit <= MAX_FAILURES_LIMIT:
        raise ValueError(
            f"{variable} must be a whole number from 1 to {MAX_FAILURES_LIMIT}, got {value!r}"
        )
    return limit


# Read once, so an invalid value stops the startup
MAX_FAILURES_PER_NAME = read_login_limit(
    "LOGIN_MAX_FAILURES_PER_NAME",
    os.getenv("LOGIN_MAX_FAILURES_PER_NAME"),
    DEFAULT_MAX_FAILURES_PER_NAME,
)
MAX_FAILURES_PER_ADDRESS = read_login_limit(
    "LOGIN_MAX_FAILURES_PER_ADDRESS",
    os.getenv("LOGIN_MAX_FAILURES_PER_ADDRESS"),
    DEFAULT_MAX_FAILURES_PER_ADDRESS,
)

# Compared against when the login name is unknown so both failure paths take similar time
_DUMMY_HASH = hash_password("unused-password")

router = APIRouter(prefix="/auth", tags=["auth"])
bearer = HTTPBearer(auto_error=False)

DbSession = Annotated[Session, Depends(get_db)]


class PatientLogin(BaseModel):
    # The login form the user chose; an account can only sign in through its own form
    role: Literal["patient"]
    national_id: str
    password: str


class DoctorLogin(BaseModel):
    role: Literal["doctor"]
    email: str
    password: str


LoginRequest = Annotated[PatientLogin | DoctorLogin, Body(discriminator="role")]

WRONG_PATIENT_LOGIN = "Wrong national ID number or password"
WRONG_DOCTOR_LOGIN = "Wrong email or password"
# Same answer for known and unknown login names, so it does not reveal an account
TOO_MANY_LOGINS = "Too many failed login attempts; try again later"


class Me(BaseModel):
    role: Literal["patient", "doctor"]
    name: str
    email: str
    # Doctor's specialty; None for patients
    specialty: str | None = None


class LoginResponse(Me):
    token: str


def _unauthorized() -> HTTPException:
    return HTTPException(
        status.HTTP_401_UNAUTHORIZED,
        "Not signed in or session expired",
        headers={"WWW-Authenticate": "Bearer"},
    )


def current_account(
    db: DbSession,
    credentials: Annotated[HTTPAuthorizationCredentials | None, Depends(bearer)],
) -> UserAccount:
    if credentials is None:
        raise _unauthorized()
    session = db.scalar(
        select(AuthSession).where(AuthSession.token_hash == hash_token(credentials.credentials))
    )
    if session is None or as_utc(session.expires_at) <= datetime.now(UTC):
        raise _unauthorized()
    return db.get(UserAccount, session.account_id)


CurrentAccount = Annotated[UserAccount, Depends(current_account)]


def require_patient(account: CurrentAccount) -> UserAccount:
    if account.role != "patient":
        raise HTTPException(status.HTTP_403_FORBIDDEN, "Patients only")
    return account


def require_doctor(account: CurrentAccount) -> UserAccount:
    if account.role != "doctor":
        raise HTTPException(status.HTTP_403_FORBIDDEN, "Doctors only")
    return account


PatientAccount = Annotated[UserAccount, Depends(require_patient)]
DoctorAccount = Annotated[UserAccount, Depends(require_doctor)]


def _me(db: Session, account: UserAccount) -> Me:
    if account.role == "patient":
        patient = db.get(Patient, account.patient_id)
        return Me(role="patient", name=patient.full_name, email=account.email)
    doctor = db.get(Doctor, account.doctor_id)
    return Me(role="doctor", name=doctor.full_name, email=account.email, specialty=doctor.specialty)


def _find_account(db: Session, body: PatientLogin | DoctorLogin) -> UserAccount | None:
    if isinstance(body, PatientLogin):
        national_id = body.national_id.strip()
        if not is_valid_national_id(national_id):
            return None
        return db.scalar(
            select(UserAccount)
            .join(Patient, Patient.id == UserAccount.patient_id)
            .where(Patient.national_id == national_id)
        )
    account = db.scalar(select(UserAccount).where(UserAccount.email == body.email.strip().lower()))
    # A patient's e-mail is a contact address, not a login name; it gets the same answer
    return account if account is not None and account.role == "doctor" else None


def _login_hash(body: PatientLogin | DoctorLogin) -> str:
    """Hash of the role and the normalized login name; the national ID is never stored."""
    name = body.national_id.strip() if isinstance(body, PatientLogin) else body.email.strip()
    return hash_token(f"{body.role}:{name.lower()}")


def _is_locked(db: Session, login_hash: str, client_ip: str, now: datetime) -> bool:
    """True if the login name or the client address reached its limit within the window."""
    name_failures, address_failures = db.execute(
        select(
            func.coalesce(func.sum(case((LoginFailure.login_hash == login_hash, 1), else_=0)), 0),
            func.coalesce(func.sum(case((LoginFailure.client_ip == client_ip, 1), else_=0)), 0),
        ).where(
            LoginFailure.created_at >= now - LOCKOUT_WINDOW,
            or_(LoginFailure.login_hash == login_hash, LoginFailure.client_ip == client_ip),
        )
    ).one()
    return name_failures >= MAX_FAILURES_PER_NAME or address_failures >= MAX_FAILURES_PER_ADDRESS


def _record_failure(db: Session, login_hash: str, client_ip: str, now: datetime) -> None:
    # Rows outside the window no longer count, so they are removed on the way
    db.execute(delete(LoginFailure).where(LoginFailure.created_at < now - LOCKOUT_WINDOW))
    db.add(LoginFailure(login_hash=login_hash, client_ip=client_ip, created_at=now))
    db.commit()


@router.post("/login")
def login(body: LoginRequest, request: Request, db: DbSession) -> LoginResponse:
    wrong = WRONG_PATIENT_LOGIN if body.role == "patient" else WRONG_DOCTOR_LOGIN
    now = datetime.now(UTC)
    login_hash = _login_hash(body)
    client_ip = request.client.host if request.client else "unknown"
    # Checked before the password, so a locked login is refused even with the right one
    if _is_locked(db, login_hash, client_ip, now):
        raise HTTPException(status.HTTP_429_TOO_MANY_REQUESTS, TOO_MANY_LOGINS)

    account = _find_account(db, body)
    if account is None:
        verify_password(body.password, _DUMMY_HASH)
    if account is None or not verify_password(body.password, account.password_hash):
        _record_failure(db, login_hash, client_ip, now)
        raise HTTPException(status.HTTP_401_UNAUTHORIZED, wrong)

    # Earlier failures of this login name do not count against the next session
    db.execute(delete(LoginFailure).where(LoginFailure.login_hash == login_hash))

    token = new_token()
    db.add(
        AuthSession(
            account_id=account.id,
            token_hash=hash_token(token),
            expires_at=datetime.now(UTC) + SESSION_LIFETIME,
        )
    )
    db.commit()
    return LoginResponse(token=token, **_me(db, account).model_dump())


@router.post(
    "/logout", status_code=status.HTTP_204_NO_CONTENT, dependencies=[Depends(current_account)]
)
def logout(
    db: DbSession,
    credentials: Annotated[HTTPAuthorizationCredentials, Depends(bearer)],
) -> Response:
    db.execute(
        delete(AuthSession).where(AuthSession.token_hash == hash_token(credentials.credentials))
    )
    db.commit()
    return Response(status_code=status.HTTP_204_NO_CONTENT)


@router.get("/me")
def me(db: DbSession, account: CurrentAccount) -> Me:
    return _me(db, account)
