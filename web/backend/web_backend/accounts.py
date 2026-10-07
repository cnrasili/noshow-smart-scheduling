"""Account creation rules for patients and doctors, used by the demo seed and the internal API.

Patients and doctors cannot register themselves; the hospital creates their accounts.
The functions add the records to the session and flush; the caller commits.
"""

import re
from datetime import time
from typing import Annotated, Literal

from pydantic import AfterValidator, BaseModel, Field, StringConstraints, model_validator
from sqlalchemy import delete, exists, select
from sqlalchemy.orm import Session

from noshow_db.models.core import AuthSession, Doctor, DoctorSchedule, Patient, UserAccount
from web_backend.national_id import is_valid_national_id
from web_backend.security import hash_password

MIN_PASSWORD_LENGTH = 8

_EMAIL = re.compile(r"^[^@\s]+@[^@\s]+\.[^@\s]+$")


class DuplicateAccountError(Exception):
    """The national ID number or the e-mail address already belongs to an account."""


class AccountNotFoundError(Exception):
    pass


def _national_id(value: str) -> str:
    if not is_valid_national_id(value):
        raise ValueError("Invalid national ID number")
    return value


def _email(value: str) -> str:
    value = value.lower()
    if len(value) > 255 or not _EMAIL.match(value):
        raise ValueError("Invalid email address")
    return value


NationalId = Annotated[str, StringConstraints(strip_whitespace=True), AfterValidator(_national_id)]
Email = Annotated[str, StringConstraints(strip_whitespace=True), AfterValidator(_email)]
Name = Annotated[str, StringConstraints(strip_whitespace=True, min_length=1, max_length=255)]
Password = Annotated[str, Field(min_length=MIN_PASSWORD_LENGTH, max_length=128)]


class NewPatient(BaseModel):
    national_id: NationalId
    full_name: Name
    # Contact address for messages; patients log in with the national ID number
    email: Email
    age: int = Field(ge=0, le=130)
    gender: Literal["F", "M"]
    scholarship: bool = False
    hipertension: bool = False
    diabetes: bool = False
    alcoholism: bool = False
    handcap: int = Field(0, ge=0, le=4)
    password: Password


class WorkingHours(BaseModel):
    # 0 = Monday ... 6 = Sunday
    weekday: int = Field(ge=0, le=6)
    start_time: time
    end_time: time

    @model_validator(mode="after")
    def _ends_after_start(self) -> "WorkingHours":
        if self.end_time <= self.start_time:
            raise ValueError("end_time must be after start_time")
        return self


class NewDoctor(BaseModel):
    full_name: Name
    # Department shown to patients when they choose a doctor
    specialty: Name
    email: Email
    password: Password
    working_hours: list[WorkingHours] = Field(min_length=1, max_length=7)

    @model_validator(mode="after")
    def _one_interval_per_weekday(self) -> "NewDoctor":
        weekdays = [hours.weekday for hours in self.working_hours]
        if len(set(weekdays)) != len(weekdays):
            raise ValueError("At most one working interval per weekday")
        return self


def _email_taken(db: Session, email: str) -> bool:
    return db.scalar(
        select(exists().where(UserAccount.email == email) | exists().where(Patient.email == email))
    )


def create_patient(db: Session, new: NewPatient) -> UserAccount:
    """Create a patient record with its login account."""
    if db.scalar(select(exists().where(Patient.national_id == new.national_id))):
        raise DuplicateAccountError("National ID number already registered")
    if _email_taken(db, new.email):
        raise DuplicateAccountError("Email already in use")

    patient = Patient(**new.model_dump(exclude={"password"}))
    db.add(patient)
    db.flush()
    account = UserAccount(
        email=new.email,
        password_hash=hash_password(new.password),
        role="patient",
        patient_id=patient.id,
    )
    db.add(account)
    db.flush()
    return account


def create_doctor(db: Session, new: NewDoctor) -> UserAccount:
    """Create a doctor with login account and weekly working hours; slots are not generated."""
    if _email_taken(db, new.email):
        raise DuplicateAccountError("Email already in use")

    doctor = Doctor(full_name=new.full_name, specialty=new.specialty)
    db.add(doctor)
    db.flush()
    db.add_all(
        DoctorSchedule(
            doctor_id=doctor.id,
            weekday=hours.weekday,
            start_time=hours.start_time,
            end_time=hours.end_time,
        )
        for hours in new.working_hours
    )
    account = UserAccount(
        email=new.email,
        password_hash=hash_password(new.password),
        role="doctor",
        doctor_id=doctor.id,
    )
    db.add(account)
    db.flush()
    return account


def reset_password(db: Session, account_id: int, password: str) -> UserAccount:
    """Set a new password and end the account's open sessions."""
    account = db.get(UserAccount, account_id)
    if account is None:
        raise AccountNotFoundError("Account not found")
    account.password_hash = hash_password(password)
    db.execute(delete(AuthSession).where(AuthSession.account_id == account_id))
    db.flush()
    return account
