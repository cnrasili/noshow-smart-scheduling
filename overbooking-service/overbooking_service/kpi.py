from dataclasses import dataclass
from datetime import UTC, date, datetime, time, timedelta
from typing import Annotated
from zoneinfo import ZoneInfo

from fastapi import APIRouter, Depends, HTTPException, Query
from sqlalchemy import case, func, select
from sqlalchemy.orm import Session

from noshow_db.models.core import Appointment, Doctor, DoctorSchedule, Slot
from overbooking_service.config import KpiSettings, SessionDefinition, settings
from overbooking_service.dependencies import get_kpi_settings, get_session
from overbooking_service.schemas import KpiResponse

router = APIRouter()


@dataclass(frozen=True)
class SlotLoad:
    start: datetime
    end: datetime
    booked: int
    attended: int


@dataclass(frozen=True)
class Kpis:
    utilization: float
    idle_minutes: float
    overtime_minutes: float
    mean_wait_minutes: float
    overbooked_slots: int
    patients_seen: int


def compute_kpis(
    slots: list[SlotLoad],
    service_minutes: float,
    session_bounds: tuple[datetime, datetime] | None = None,
) -> Kpis | None:
    """Replay a session: attended patients are seen in slot order, each for service_minutes.

    The session runs from the first slot start to the last slot end, or within session_bounds
    when they are given, for example the doctor's working hours.
    """
    if not slots:
        return None
    slots = sorted(slots, key=lambda s: s.start)
    session_start, session_end = session_bounds or (slots[0].start, max(s.end for s in slots))

    def minutes(moment: datetime) -> float:
        return (moment - session_start).total_seconds() / 60

    end_min = minutes(session_end)
    # The doctor is free from the session start, or from an earlier first slot
    free_at = min(0.0, minutes(slots[0].start))
    busy: list[tuple[float, float]] = []
    waits: list[float] = []
    for slot in slots:
        # Patients are assumed to arrive on time
        ready = minutes(slot.start)
        for _ in range(slot.attended):
            start = max(ready, free_at)
            free_at = start + service_minutes
            busy.append((start, free_at))
            waits.append(start - ready)

    busy_in_session = sum(max(0.0, min(e, end_min) - max(s, 0.0)) for s, e in busy)
    return Kpis(
        utilization=sum(e - s for s, e in busy) / end_min,
        idle_minutes=end_min - busy_in_session,
        overtime_minutes=max(0.0, free_at - end_min),
        mean_wait_minutes=sum(waits) / len(waits) if waits else 0.0,
        overbooked_slots=sum(s.booked > 1 for s in slots),
        patients_seen=len(waits),
    )


def as_utc(value: datetime) -> datetime:
    # SQLite returns naive datetimes; they are stored in UTC
    return value.replace(tzinfo=UTC) if value.tzinfo is None else value


def load_day(session: Session, doctor_id: int, day: date, timezone: ZoneInfo) -> list[SlotLoad]:
    """Slots of a doctor on a clinic day with booked and attended counts."""
    day_start = datetime.combine(day, time(), timezone).astimezone(UTC)
    day_end = datetime.combine(day + timedelta(days=1), time(), timezone).astimezone(UTC)
    rows = session.execute(
        select(
            Slot.start_at,
            Slot.end_at,
            func.count(Appointment.id),
            func.count(case((Appointment.attended.is_(True), 1))),
        )
        .outerjoin(Appointment, Appointment.slot_id == Slot.id)
        .where(Slot.doctor_id == doctor_id, Slot.start_at >= day_start, Slot.start_at < day_end)
        .group_by(Slot.id, Slot.start_at, Slot.end_at)
    ).all()
    return [
        SlotLoad(as_utc(start), as_utc(end), booked, attended)
        for start, end, booked, attended in rows
    ]


def working_hours(
    session: Session, doctor_id: int, day: date, timezone: ZoneInfo
) -> tuple[datetime, datetime] | None:
    """The doctor's working hours on a clinic day, or None on a day without working hours."""
    schedule = session.scalar(
        select(DoctorSchedule).where(
            DoctorSchedule.doctor_id == doctor_id, DoctorSchedule.weekday == day.weekday()
        )
    )
    if schedule is None:
        return None
    return (
        datetime.combine(day, schedule.start_time, timezone).astimezone(UTC),
        datetime.combine(day, schedule.end_time, timezone).astimezone(UTC),
    )


def doctor_kpis(session: Session, doctor_id: int, day: date, kpi: KpiSettings) -> Kpis | None:
    timezone = settings.clinic_timezone
    bounds = None
    if kpi.session is SessionDefinition.SCHEDULE:
        bounds = working_hours(session, doctor_id, day, timezone)
    return compute_kpis(load_day(session, doctor_id, day, timezone), kpi.service_minutes, bounds)


@router.get("/kpi", responses={404: {"description": "Doctor not found or no slots on the date"}})
def get_kpi(
    doctor_id: Annotated[int, Query(gt=0)],
    date: date,
    session: Annotated[Session, Depends(get_session)],
    kpi: Annotated[KpiSettings, Depends(get_kpi_settings)],
) -> KpiResponse:
    if session.get(Doctor, doctor_id) is None:
        raise HTTPException(404, f"Doctor {doctor_id} not found")
    result = doctor_kpis(session, doctor_id, date, kpi)
    if result is None:
        raise HTTPException(404, f"Doctor {doctor_id} has no slots on {date}")
    return KpiResponse(
        utilization=round(result.utilization, 3),
        idle_minutes=round(result.idle_minutes, 1),
        overtime_minutes=round(result.overtime_minutes, 1),
        mean_wait_minutes=round(result.mean_wait_minutes, 1),
        overbooked_slots=result.overbooked_slots,
        patients_seen=result.patients_seen,
    )
