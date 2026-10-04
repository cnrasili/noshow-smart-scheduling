# Slot generation from the doctors' weekly working hours
from datetime import UTC, date, datetime, timedelta
from typing import Annotated

from fastapi import APIRouter, Depends, HTTPException, status
from pydantic import BaseModel, Field
from sqlalchemy import select
from sqlalchemy.orm import Session

from noshow_db.models.core import DoctorSchedule, Slot
from web_backend.auth import DoctorAccount
from web_backend.clinic import CLINIC_TZ, as_utc, today
from web_backend.db import get_db

# Placeholder until IEN-1 fixes the session parameters
DEFAULT_SLOT_MINUTES = 20
MAX_GENERATION_DAYS = 62

router = APIRouter(tags=["slots"])


def generate_slots(
    db: Session,
    doctor_id: int,
    date_from: date,
    date_to: date,
    slot_minutes: int = DEFAULT_SLOT_MINUTES,
) -> list[Slot]:
    """Create the missing slots of a doctor between two dates, both inclusive.

    Each working interval is split into back-to-back slots; a remainder shorter than
    one slot is left unused. Existing slots are kept, so the call can be repeated.
    """
    schedules = {
        schedule.weekday: schedule
        for schedule in db.scalars(
            select(DoctorSchedule).where(DoctorSchedule.doctor_id == doctor_id)
        )
    }
    range_start = datetime.combine(date_from, datetime.min.time(), CLINIC_TZ).astimezone(UTC)
    range_end = datetime.combine(
        date_to + timedelta(days=1), datetime.min.time(), CLINIC_TZ
    ).astimezone(UTC)
    existing = {
        as_utc(start_at)
        for start_at in db.scalars(
            select(Slot.start_at).where(
                Slot.doctor_id == doctor_id,
                Slot.start_at >= range_start,
                Slot.start_at < range_end,
            )
        )
    }

    length = timedelta(minutes=slot_minutes)
    created = []
    day = date_from
    while day <= date_to:
        schedule = schedules.get(day.weekday())
        if schedule is not None:
            start = datetime.combine(day, schedule.start_time, CLINIC_TZ)
            day_end = datetime.combine(day, schedule.end_time, CLINIC_TZ)
            while start + length <= day_end:
                # Stored in UTC so SQLite and PostgreSQL keep the same instant
                start_utc = start.astimezone(UTC)
                if start_utc not in existing:
                    created.append(
                        Slot(doctor_id=doctor_id, start_at=start_utc, end_at=start_utc + length)
                    )
                start += length
        day += timedelta(days=1)

    db.add_all(created)
    return created


class GenerateSlotsRequest(BaseModel):
    date_from: date
    date_to: date
    slot_minutes: int = Field(DEFAULT_SLOT_MINUTES, ge=5, le=120)


class GenerateSlotsResponse(BaseModel):
    created: int


@router.post("/doctors/me/slots/generate")
def generate_my_slots(
    body: GenerateSlotsRequest,
    account: DoctorAccount,
    db: Annotated[Session, Depends(get_db)],
) -> GenerateSlotsResponse:
    if body.date_from < today():
        raise HTTPException(status.HTTP_422_UNPROCESSABLE_CONTENT, "date_from is in the past")
    if body.date_to < body.date_from:
        raise HTTPException(status.HTTP_422_UNPROCESSABLE_CONTENT, "date_to is before date_from")
    if (body.date_to - body.date_from).days >= MAX_GENERATION_DAYS:
        raise HTTPException(
            status.HTTP_422_UNPROCESSABLE_CONTENT,
            f"At most {MAX_GENERATION_DAYS} days can be generated at once",
        )

    created = generate_slots(db, account.doctor_id, body.date_from, body.date_to, body.slot_minutes)
    db.commit()
    return GenerateSlotsResponse(created=len(created))
