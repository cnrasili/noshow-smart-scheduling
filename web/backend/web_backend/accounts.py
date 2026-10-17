"""Account rules for patients and the department, used by the demo seed and the internal API.

Nobody can register; the hospital opens the accounts. Patients are the patients of the public
dataset and already exist; their account only adds a login. The functions add the records to
the session and flush; the caller commits.
"""

import re
from datetime import time
from typing import Annotated

from pydantic import AfterValidator, BaseModel, Field, StringConstraints, model_validator
from sqlalchemy import delete, exists, select
from sqlalchemy.orm import Session

from noshow_db.models.core import AuthSession, Doctor, DoctorSchedule, Patient, UserAccount
from web_backend.security import hash_password

MIN_PASSWORD_LENGTH = 8
# The system's only department; "Aile Hekimliği" on the screens
DEPARTMENT_NAME = "General Practice"

_EMAIL = re.compile(r"^[^@\s]+@[^@\s]+\.[^@\s]+$")


class DuplicateAccountError(Exception):
    """The patient or the e-mail address already belongs to an account."""


class AccountNotFoundError(Exception):
    pass


class PatientNotFoundError(Exception):
    pass


def _email(value: str) -> str:
    value = value.lower()
    if len(value) > 255 or not _EMAIL.match(value):
        raise ValueError("Invalid email address")
    return value


Email = Annotated[str, StringConstraints(strip_whitespace=True), AfterValidator(_email)]
Name = Annotated[str, StringConstraints(strip_whitespace=True, min_length=1, max_length=255)]
# PatientId of the dataset as stored in patients.patient_number
PatientNumber = Annotated[
    str, StringConstraints(strip_whitespace=True, min_length=1, max_length=20)
]
Password = Annotated[str, Field(min_length=MIN_PASSWORD_LENGTH, max_length=128)]


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


def open_patient_account(db: Session, patient_number: str, password: str) -> UserAccount:
    """Open the login account of an existing dataset patient; no patient is created.

    The account takes the e-mail address of the patient record; the patient logs in with the
    patient number.
    """
    patient = db.scalar(select(Patient).where(Patient.patient_number == patient_number))
    if patient is None:
        raise PatientNotFoundError("Patient not found")
    if db.scalar(select(exists().where(UserAccount.patient_id == patient.id))):
        raise DuplicateAccountError("Patient already has an account")
    if db.scalar(select(exists().where(UserAccount.email == patient.email))):
        raise DuplicateAccountError("Email already in use")

    account = UserAccount(
        email=patient.email,
        password_hash=hash_password(password),
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


def create_department(
    db: Session, username: str, password: str, working_hours: list[WorkingHours]
) -> UserAccount:
    """Create the department with its staff account and weekly working hours.

    The department is stored as the one record in doctors, and its staff account has the
    doctor role; the login name is kept in user_accounts.email. Slots are not generated.
    """
    if _email_taken(db, username):
        raise DuplicateAccountError("Username already in use")

    department = Doctor(full_name=DEPARTMENT_NAME, specialty=DEPARTMENT_NAME)
    db.add(department)
    db.flush()
    db.add_all(
        DoctorSchedule(
            doctor_id=department.id,
            weekday=hours.weekday,
            start_time=hours.start_time,
            end_time=hours.end_time,
        )
        for hours in working_hours
    )
    account = UserAccount(
        email=username,
        password_hash=hash_password(password),
        role="doctor",
        doctor_id=department.id,
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
