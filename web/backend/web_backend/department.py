# Read-only days of the public dataset for the department's panel
from datetime import date
from typing import Annotated

from fastapi import APIRouter, Depends
from pydantic import BaseModel
from sqlalchemy import case, func, select
from sqlalchemy.orm import Session

from noshow_db.models.core import Patient
from noshow_db.models.dataset import DatasetAppointment
from web_backend.auth import DepartmentAccount
from web_backend.db import get_db

router = APIRouter(prefix="/department", tags=["department"])

DbSession = Annotated[Session, Depends(get_db)]


class DatasetDay(BaseModel):
    date: date
    appointments: int
    missed: int


class DatasetRecord(BaseModel):
    # "Hasta <PatientId>"
    patient_name: str
    patient_age: int
    # The outcome recorded in the dataset; it cannot be changed
    attended: bool


@router.get("/dataset-days")
def dataset_days(account: DepartmentAccount, db: DbSession) -> list[DatasetDay]:
    """The days of the dataset with their number of appointments and no-shows."""
    rows = db.execute(
        select(
            DatasetAppointment.appointment_date,
            func.count(),
            func.sum(case((DatasetAppointment.attended.is_(False), 1), else_=0)),
        )
        .group_by(DatasetAppointment.appointment_date)
        .order_by(DatasetAppointment.appointment_date)
    )
    return [DatasetDay(date=day, appointments=n, missed=missed) for day, n, missed in rows]


@router.get("/dataset-days/{day}")
def dataset_day(day: date, account: DepartmentAccount, db: DbSession) -> list[DatasetRecord]:
    """Every appointment of a dataset day with its recorded outcome; empty on other days.

    The dataset has no appointment times, so the records are ordered by booking time.
    """
    rows = db.execute(
        select(Patient.full_name, Patient.age, DatasetAppointment.attended)
        .join(Patient, Patient.id == DatasetAppointment.patient_id)
        .where(DatasetAppointment.appointment_date == day)
        .order_by(DatasetAppointment.booked_at, DatasetAppointment.id)
    )
    return [
        DatasetRecord(patient_name=name, patient_age=age, attended=attended)
        for name, age, attended in rows
    ]
