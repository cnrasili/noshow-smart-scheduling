from datetime import UTC, datetime, timedelta
from typing import Annotated, Literal

from fastapi import APIRouter, Depends, HTTPException, Response, status
from fastapi.security import HTTPAuthorizationCredentials, HTTPBearer
from pydantic import BaseModel
from sqlalchemy import delete, select
from sqlalchemy.orm import Session

from noshow_db.models.core import AuthSession, Doctor, Patient, UserAccount
from web_backend.clinic import as_utc
from web_backend.db import get_db
from web_backend.security import hash_password, hash_token, new_token, verify_password

SESSION_LIFETIME = timedelta(hours=12)

# Compared against when the email is unknown so both failure paths take similar time
_DUMMY_HASH = hash_password("unused-password")

router = APIRouter(prefix="/auth", tags=["auth"])
bearer = HTTPBearer(auto_error=False)

DbSession = Annotated[Session, Depends(get_db)]


class LoginRequest(BaseModel):
    email: str
    password: str


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


@router.post("/login")
def login(body: LoginRequest, db: DbSession) -> LoginResponse:
    account = db.scalar(select(UserAccount).where(UserAccount.email == body.email.strip().lower()))
    if account is None:
        verify_password(body.password, _DUMMY_HASH)
        raise HTTPException(status.HTTP_401_UNAUTHORIZED, "Wrong email or password")
    if not verify_password(body.password, account.password_hash):
        raise HTTPException(status.HTTP_401_UNAUTHORIZED, "Wrong email or password")

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
