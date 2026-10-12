"""Internal account API for the hospital's admin service; never called by the public frontend.

Every request needs the service token from INTERNAL_API_TOKEN in the X-Internal-Token header.
Without the variable the API is disabled.
"""

import hmac
import os
from datetime import timedelta
from typing import Annotated

from fastapi import APIRouter, Depends, Header, HTTPException, Response, status
from pydantic import BaseModel
from sqlalchemy.exc import IntegrityError
from sqlalchemy.orm import Session

from web_backend import accounts
from web_backend.accounts import NewDoctor, NewPatient, Password
from web_backend.clinic import today
from web_backend.db import get_db
from web_backend.slots import DEFAULT_LISTING_DAYS, generate_slots


def require_service_token(
    token: Annotated[str | None, Header(alias="X-Internal-Token")] = None,
) -> None:
    expected = os.getenv("INTERNAL_API_TOKEN")
    if not expected:
        raise HTTPException(status.HTTP_503_SERVICE_UNAVAILABLE, "Internal API is disabled")
    if token is None or not hmac.compare_digest(token.encode(), expected.encode()):
        raise HTTPException(status.HTTP_401_UNAUTHORIZED, "Invalid service token")


# Left out of the public API documentation
router = APIRouter(
    prefix="/internal/accounts",
    tags=["internal"],
    include_in_schema=False,
    dependencies=[Depends(require_service_token)],
)

DbSession = Annotated[Session, Depends(get_db)]


class PatientCreated(BaseModel):
    account_id: int
    patient_id: int
    national_id: str
    full_name: str
    email: str


class DoctorCreated(BaseModel):
    account_id: int
    doctor_id: int
    full_name: str
    specialty: str
    email: str
    # Slots generated from the working hours for the next two weeks
    slots_created: int


class PasswordReset(BaseModel):
    password: Password


def _conflict(error: Exception) -> HTTPException:
    return HTTPException(status.HTTP_409_CONFLICT, str(error))


@router.post("/patients", status_code=status.HTTP_201_CREATED)
def create_patient(body: NewPatient, db: DbSession) -> PatientCreated:
    try:
        account = accounts.create_patient(db, body)
        db.commit()
    except accounts.DuplicateAccountError as error:
        raise _conflict(error) from error
    except IntegrityError as error:
        # Another request created the same national ID number or e-mail meanwhile
        db.rollback()
        raise _conflict(accounts.DuplicateAccountError("Account already exists")) from error
    return PatientCreated(
        account_id=account.id,
        patient_id=account.patient_id,
        national_id=body.national_id,
        full_name=body.full_name,
        email=account.email,
    )


@router.post("/doctors", status_code=status.HTTP_201_CREATED)
def create_doctor(body: NewDoctor, db: DbSession) -> DoctorCreated:
    try:
        account = accounts.create_doctor(db, body)
        slots = generate_slots(
            db, account.doctor_id, today(), today() + timedelta(days=DEFAULT_LISTING_DAYS - 1)
        )
        db.commit()
    except accounts.DuplicateAccountError as error:
        raise _conflict(error) from error
    except IntegrityError as error:
        db.rollback()
        raise _conflict(accounts.DuplicateAccountError("Account already exists")) from error
    return DoctorCreated(
        account_id=account.id,
        doctor_id=account.doctor_id,
        full_name=body.full_name,
        specialty=body.specialty,
        email=account.email,
        slots_created=len(slots),
    )


@router.put("/{account_id}/password", status_code=status.HTTP_204_NO_CONTENT)
def reset_password(account_id: int, body: PasswordReset, db: DbSession) -> Response:
    try:
        accounts.reset_password(db, account_id, body.password)
    except accounts.AccountNotFoundError as error:
        raise HTTPException(status.HTTP_404_NOT_FOUND, str(error)) from error
    db.commit()
    return Response(status_code=status.HTTP_204_NO_CONTENT)
