"""Predicted risks and booking decisions of the overbooking service, read from its decision log."""

from collections import Counter, defaultdict
from dataclasses import dataclass, field
from datetime import UTC, date, datetime, time, timedelta
from typing import Annotated
from zoneinfo import ZoneInfo

from fastapi import APIRouter, Query, Request
from fastapi.responses import HTMLResponse, Response
from sqlalchemy import ColumnElement, and_, select
from sqlalchemy.orm import Session

from admin_service.dependencies import AppSettings, CurrentAdmin, DbSession, Now
from admin_service.templating import templates
from noshow_db.models.core import Appointment, Doctor, Patient, Slot
from noshow_db.models.service import BookingDecision

router = APIRouter()

PERIOD_DAYS = 30
RISK_BANDS = 10


@dataclass
class Booking:
    patient: str
    outcome: str
    decision: BookingDecision | None


@dataclass
class SlotRow:
    start: datetime
    end: datetime
    bookings: list[Booking] = field(default_factory=list)
    refusals: list[tuple[str, BookingDecision]] = field(default_factory=list)


@dataclass
class RiskBand:
    label: str
    appointments: int = 0
    no_shows: int = 0
    predicted_total: float = 0.0

    @property
    def rate(self) -> float | None:
        return self.no_shows / self.appointments if self.appointments else None

    @property
    def predicted(self) -> float | None:
        return self.predicted_total / self.appointments if self.appointments else None


def as_utc(moment: datetime) -> datetime:
    # SQLite returns naive datetimes; they are stored in UTC
    return moment.replace(tzinfo=UTC) if moment.tzinfo is None else moment


def slots_between(first_day: date, last_day: date, tz: ZoneInfo) -> ColumnElement[bool]:
    """Slots that start on the clinic days from first_day to last_day."""
    start = datetime.combine(first_day, time(), tz).astimezone(UTC)
    end = datetime.combine(last_day + timedelta(days=1), time(), tz).astimezone(UTC)
    return and_(Slot.start_at >= start, Slot.start_at < end)


def decision_kind(decision: BookingDecision) -> str:
    """Granted as normal or extra; refusals by the reason the rule gives."""
    if decision.allow:
        return "extra" if decision.overbook else "normal"
    if decision.reason.startswith("Slot is full"):
        return "full"
    if "daily overbook limit" in decision.reason:
        return "limit"
    if decision.reason.startswith("Patient is already booked"):
        return "duplicate"
    return "low_risk"


def outcome(attended: bool | None, start: datetime, now: datetime) -> str:
    if attended is not None:
        return "came" if attended else "missed"
    return "unmarked" if start <= now else "upcoming"


def day_view(
    session: Session, doctor_id: int, day: date, tz: ZoneInfo, now: datetime
) -> list[SlotRow]:
    """Slots of a doctor on a day with their patients, decisions and refused requests."""
    slots = session.scalars(
        select(Slot)
        .where(Slot.doctor_id == doctor_id, slots_between(day, day, tz))
        .order_by(Slot.start_at)
    ).all()
    rows = {
        slot.id: SlotRow(as_utc(slot.start_at).astimezone(tz), as_utc(slot.end_at).astimezone(tz))
        for slot in slots
    }

    granted: dict[tuple[int, int], BookingDecision] = {}
    decisions = session.execute(
        select(BookingDecision, Patient.full_name)
        .outerjoin(Patient, Patient.id == BookingDecision.patient_id)
        .where(BookingDecision.slot_id.in_(rows))
        .order_by(BookingDecision.id)
    ).all()
    for decision, name in decisions:
        if decision.allow:
            # The latest grant of a patient's slot belongs to the current appointment
            granted[(decision.patient_id, decision.slot_id)] = decision
        else:
            rows[decision.slot_id].refusals.append((name or "–", decision))

    appointments = session.execute(
        select(Appointment, Patient.full_name)
        .join(Patient, Patient.id == Appointment.patient_id)
        .where(Appointment.slot_id.in_(rows))
        .order_by(Appointment.id)
    ).all()
    for appointment, name in appointments:
        row = rows[appointment.slot_id]
        row.bookings.append(
            Booking(
                name,
                outcome(appointment.attended, row.start, now),
                granted.get((appointment.patient_id, appointment.slot_id)),
            )
        )
    return list(rows.values())


def period_decisions(
    session: Session, first_day: date, last_day: date, tz: ZoneInfo
) -> list[BookingDecision]:
    """Decisions about slots on the days of the period."""
    return list(
        session.scalars(
            select(BookingDecision)
            .join(Slot, Slot.id == BookingDecision.slot_id)
            .where(slots_between(first_day, last_day, tz))
            .order_by(BookingDecision.id)
        )
    )


def risk_bands(
    session: Session,
    decisions: list[BookingDecision],
    first_day: date,
    last_day: date,
    tz: ZoneInfo,
) -> list[RiskBand]:
    """Marked appointments per predicted risk band with their actual no-shows."""
    granted = {(d.patient_id, d.slot_id): d for d in decisions if d.allow}
    bands = [RiskBand(f"%{i * 10}–{(i + 1) * 10}") for i in range(RISK_BANDS)]
    marked = session.execute(
        select(Appointment.patient_id, Appointment.slot_id, Appointment.attended)
        .join(Slot, Slot.id == Appointment.slot_id)
        .where(slots_between(first_day, last_day, tz), Appointment.attended.is_not(None))
    ).all()
    for patient_id, slot_id, attended in marked:
        decision = granted.get((patient_id, slot_id))
        if decision is None:
            continue
        band = bands[min(int(decision.p_noshow * RISK_BANDS), RISK_BANDS - 1)]
        band.appointments += 1
        band.no_shows += not attended
        band.predicted_total += decision.p_noshow
    return bands


def extra_outcomes(session: Session, first_day: date, last_day: date, tz: ZoneInfo) -> Counter:
    """Slots with more than one patient by what happened to their patients."""
    marks: dict[int, list[bool | None]] = defaultdict(list)
    for slot_id, attended in session.execute(
        select(Appointment.slot_id, Appointment.attended)
        .join(Slot, Slot.id == Appointment.slot_id)
        .where(slots_between(first_day, last_day, tz))
    ):
        marks[slot_id].append(attended)

    result: Counter = Counter()
    for slot_marks in marks.values():
        if len(slot_marks) < 2:
            continue
        if any(mark is None for mark in slot_marks):
            result["pending"] += 1
        elif all(slot_marks):
            result["all_came"] += 1
        elif not any(slot_marks):
            result["none_came"] += 1
        else:
            result["filled"] += 1
    return result


@router.get("/decisions", response_class=HTMLResponse)
def decisions_page(
    request: Request,
    admin: CurrentAdmin,
    session: DbSession,
    now: Now,
    app_settings: AppSettings,
    doctor_id: Annotated[int | None, Query(gt=0)] = None,
    day: Annotated[date | None, Query(alias="date")] = None,
) -> Response:
    tz = app_settings.clinic_timezone
    doctors = list(session.scalars(select(Doctor).order_by(Doctor.full_name)))
    selected = next((d for d in doctors if d.id == doctor_id), doctors[0] if doctors else None)
    day = day or now.astimezone(tz).date()
    first_day = day - timedelta(days=PERIOD_DAYS - 1)

    decisions = period_decisions(session, first_day, day, tz)
    kinds = Counter(decision_kind(d) for d in decisions)
    bands = risk_bands(session, decisions, first_day, day, tz)
    latest = decisions[-1] if decisions else None

    return templates.TemplateResponse(
        request,
        "decisions.html",
        {
            "admin": admin,
            "doctors": doctors,
            "selected": selected,
            "day": day,
            "first_day": first_day,
            "period_days": PERIOD_DAYS,
            "slots": day_view(session, selected.id, day, tz, now) if selected else [],
            "decision_kind": decision_kind,
            "requests": len(decisions),
            "kinds": kinds,
            "refused": len(decisions) - kinds["normal"] - kinds["extra"],
            "latest": latest,
            "bands": bands,
            "marked": sum(band.appointments for band in bands),
            "chart": [
                {
                    "label": band.label,
                    "rate": None if band.rate is None else round(band.rate * 100, 1),
                    "predicted": None if band.predicted is None else round(band.predicted * 100, 1),
                    "count": band.appointments,
                }
                for band in bands
            ],
            "extras": extra_outcomes(session, first_day, day, tz),
        },
    )
