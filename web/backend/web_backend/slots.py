# Slot generation from the doctors' weekly working hours
from datetime import UTC, date, datetime, timedelta
from typing import Annotated

from fastapi import APIRouter, Depends, HTTPException, Query, status
from pydantic import BaseModel, Field
from sqlalchemy import func, select
from sqlalchemy.orm import Session

from noshow_db.models.core import Appointment, DoctorSchedule, Slot
from web_backend.auth import CurrentAccount, DoctorAccount
from web_backend.clinic import CLINIC_TZ, as_utc, today
from web_backend.db import get_db

# Placeholder until IEN-1 fixes the session parameters
DEFAULT_SLOT_MINUTES = 20
MAX_GENERATION_DAYS = 62
DEFAULT_LISTING_DAYS = 14

router = APIRouter(tags=["slots"])


def clinic_days_in_utc(date_from: date, date_to: date) -> tuple[datetime, datetime]:
    """UTC bounds [start, end) covering whole clinic days from date_from to date_to."""
    start = datetime.combine(date_from, datetime.min.time(), CLINIC_TZ)
    end = datetime.combine(date_to + timedelta(days=1), datetime.min.time(), CLINIC_TZ)
    return start.astimezone(UTC), end.astimezone(UTC)


def generate_slots(
    db: Session,
    doctor_id: int,
    date_from: date,
    date_to: date,
    slot_minutes: int = DEFAULT_SLOT_MINUTES,
) -> list[Slot]:
    """Create the missing slots of a doctor between two dates, both inclusive.

    Each working interval is split into back-to-back slots; a remainder shorter than
    one slot is left unused. Existing slots are kept and a new slot that would overlap one
    is skipped, so the call can be repeated, also with another slot length.
    """
    schedules = {
        schedule.weekday: schedule
        for schedule in db.scalars(
            select(DoctorSchedule).where(DoctorSchedule.doctor_id == doctor_id)
        )
    }
    range_start, range_end = clinic_days_in_utc(date_from, date_to)
    existing = [
        (as_utc(start_at), as_utc(end_at))
        for start_at, end_at in db.execute(
            select(Slot.start_at, Slot.end_at).where(
                Slot.doctor_id == doctor_id,
                Slot.start_at < range_end,
                Slot.end_at > range_start,
            )
        )
    ]

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
                end_utc = start_utc + length
                if not any(s < end_utc and start_utc < e for s, e in existing):
                    created.append(Slot(doctor_id=doctor_id, start_at=start_utc, end_at=end_utc))
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


class SlotOut(BaseModel):
    id: int
    doctor_id: int
    start_at: datetime
    end_at: datetime
    max_patients: int
    booked_count: int
    # Bookable while below capacity; for an already booked slot the overbooking service
    # makes the final decision at booking time
    available: bool
    booked_by_me: bool


@router.get("/slots")
def list_slots(
    account: CurrentAccount,
    db: Annotated[Session, Depends(get_db)],
    doctor_id: int,
    date_from: Annotated[date | None, Query()] = None,
    date_to: Annotated[date | None, Query()] = None,
) -> list[SlotOut]:
    """Upcoming slots of a doctor, by default for the next two weeks."""
    date_from = date_from or today()
    date_to = date_to or date_from + timedelta(days=DEFAULT_LISTING_DAYS - 1)
    range_start, range_end = clinic_days_in_utc(date_from, date_to)
    range_start = max(range_start, datetime.now(UTC))

    booked = (
        select(Appointment.slot_id, func.count().label("booked_count"))
        .group_by(Appointment.slot_id)
        .subquery()
    )
    rows = db.execute(
        select(Slot, func.coalesce(booked.c.booked_count, 0))
        .outerjoin(booked, booked.c.slot_id == Slot.id)
        .where(
            Slot.doctor_id == doctor_id,
            Slot.start_at >= range_start,
            Slot.start_at < range_end,
        )
        .order_by(Slot.start_at)
    ).all()
    mine = set()
    if account.patient_id is not None:
        mine = set(
            db.scalars(
                select(Appointment.slot_id).where(Appointment.patient_id == account.patient_id)
            )
        )

    return [
        SlotOut(
            id=slot.id,
            doctor_id=slot.doctor_id,
            start_at=as_utc(slot.start_at),
            end_at=as_utc(slot.end_at),
            max_patients=slot.max_patients,
            booked_count=booked_count,
            available=booked_count < slot.max_patients,
            booked_by_me=slot.id in mine,
        )
        for slot, booked_count in rows
    ]
