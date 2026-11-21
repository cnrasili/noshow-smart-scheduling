"""Internal account API for the hospital's admin service; never called by the public frontend.

Every request needs the service token from INTERNAL_API_TOKEN in the X-Internal-Token header.
Without the variable the API is disabled.
"""

import hmac
import os
from typing import Annotated

from fastapi import APIRouter, Depends, Header, HTTPException, Response, status
from pydantic import BaseModel
from sqlalchemy.exc import IntegrityError
from sqlalchemy.orm import Session

from noshow_db.models.core import Patient
from web_backend import accounts
from web_backend.accounts import Password, PatientNumber
from web_backend.db import get_db


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


class PatientAccountRequest(BaseModel):
    patient_number: PatientNumber
    password: Password


class PatientAccountOpened(BaseModel):
    account_id: int
    patient_id: int
    patient_number: str
    full_name: str
    email: str


class PasswordReset(BaseModel):
    password: Password


def _conflict(error: Exception) -> HTTPException:
    return HTTPException(status.HTTP_409_CONFLICT, str(error))


@router.post("/patients", status_code=status.HTTP_201_CREATED)
def open_patient_account(body: PatientAccountRequest, db: DbSession) -> PatientAccountOpened:
    """Open the login account of an existing dataset patient; never creates a patient."""
    try:
        account = accounts.open_patient_account(db, body.patient_number, body.password)
        patient = db.get(Patient, account.patient_id)
        db.commit()
    except accounts.PatientNotFoundError as error:
        raise HTTPException(status.HTTP_404_NOT_FOUND, str(error)) from error
    except accounts.DuplicateAccountError as error:
        raise _conflict(error) from error
    except IntegrityError as error:
        # Another request opened an account for the same patient meanwhile
        db.rollback()
        raise _conflict(accounts.DuplicateAccountError("Patient already has an account")) from error
    return PatientAccountOpened(
        account_id=account.id,
        patient_id=patient.id,
        patient_number=patient.patient_number,
        full_name=patient.full_name,
        email=account.email,
    )


@router.put("/{account_id}/password", status_code=status.HTTP_204_NO_CONTENT)
def reset_password(account_id: int, body: PasswordReset, db: DbSession) -> Response:
    try:
        accounts.reset_password(db, account_id, body.password)
    except accounts.AccountNotFoundError as error:
        raise HTTPException(status.HTTP_404_NOT_FOUND, str(error)) from error
    db.commit()
    return Response(status_code=status.HTTP_204_NO_CONTENT)
