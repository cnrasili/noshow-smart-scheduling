# Read-only data for the public hospital site; no sign-in and no account data
from collections import defaultdict
from datetime import time
from typing import Annotated

from fastapi import APIRouter, Depends
from pydantic import BaseModel
from sqlalchemy import select
from sqlalchemy.orm import Session

from noshow_db.models.core import Doctor, DoctorSchedule
from web_backend.db import get_db

router = APIRouter(prefix="/public", tags=["public"])

DbSession = Annotated[Session, Depends(get_db)]


class PublicWorkingHours(BaseModel):
    # 0 = Monday ... 6 = Sunday
    weekday: int
    start_time: time
    end_time: time


class PublicDoctor(BaseModel):
    id: int
    full_name: str
    # The doctor's department; None if not set
    specialty: str | None
    working_hours: list[PublicWorkingHours]


@router.get("/doctors")
def public_doctors(db: DbSession) -> list[PublicDoctor]:
    """Doctors with their department and weekly working hours, by department and name."""
    hours: dict[int, list[PublicWorkingHours]] = defaultdict(list)
    for schedule in db.scalars(select(DoctorSchedule).order_by(DoctorSchedule.weekday)):
        hours[schedule.doctor_id].append(
            PublicWorkingHours(
                weekday=schedule.weekday,
                start_time=schedule.start_time,
                end_time=schedule.end_time,
            )
        )
    doctors = db.scalars(select(Doctor).order_by(Doctor.specialty, Doctor.full_name))
    return [
        PublicDoctor(
            id=doctor.id,
            full_name=doctor.full_name,
            specialty=doctor.specialty,
            working_hours=hours[doctor.id],
        )
        for doctor in doctors
    ]
