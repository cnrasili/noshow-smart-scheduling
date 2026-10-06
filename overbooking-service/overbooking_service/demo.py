"""Add booking history to the demo clinic created by the web backend seed.

Run ``python -m web_backend.seed`` first, then
``python -m overbooking_service.demo [--today 2026-11-16] [--seed 42]``.
"""

import argparse
import random
from collections import defaultdict
from dataclasses import dataclass
from datetime import UTC, date, datetime, time, timedelta
from zoneinfo import ZoneInfo

from sqlalchemy import func, select
from sqlalchemy.orm import Session

from noshow_db import SessionLocal
from noshow_db.models.core import Appointment, Doctor, Patient, Slot
from noshow_db.models.service import AbAssignment
from overbooking_service.ab import assign_group
from overbooking_service.booking import evaluate
from overbooking_service.config import Settings, settings
from overbooking_service.data_source import DbPatientSource, DbSlotSource
from overbooking_service.predictor import Predictor
from overbooking_service.rules import OverbookingRule

# History patients have no login account; this domain marks them
HISTORY_EMAIL_DOMAIN = "history.demo.local"
# Booking time on the booking date, used to decide reminder eligibility
BOOKING_TIME = time(8, 0)


@dataclass(frozen=True)
class DemoConfig:
    today: date
    seed: int = 42
    patients: int = 200
    # Calendar days before and from today whose slots get bookings
    past_days: int = 21
    future_days: int = 7
    # Booking requests per slot of a doctor's day
    past_requests_per_slot: float = 1.25
    future_requests_per_slot: float = 0.5
    # Relative no-show reduction for the reminder group; 0 means reminders have no effect
    reminder_effect: float = 0.0


@dataclass(frozen=True)
class DemoResult:
    appointments: int
    overbooks: int
    rejected: int
    assignments: int


def lead_days(rng: random.Random) -> int:
    # Same-day, within a week and later bookings, roughly as in the public dataset
    bucket = rng.choices(["same", "week", "later"], weights=[15, 45, 40])[0]
    if bucket == "same":
        return 0
    if bucket == "week":
        return rng.randint(1, 7)
    return rng.randint(8, 30)


def make_patient(rng: random.Random, number: int) -> Patient:
    return Patient(
        full_name=f"Demo Patient {number}",
        email=f"patient{number}@{HISTORY_EMAIL_DOMAIN}",
        age=rng.randint(1, 90),
        gender="F" if rng.random() < 0.65 else "M",
        scholarship=rng.random() < 0.10,
        hipertension=rng.random() < 0.20,
        diabetes=rng.random() < 0.07,
        alcoholism=rng.random() < 0.03,
        handcap=1 if rng.random() < 0.02 else 0,
    )


def as_utc(moment: datetime) -> datetime:
    # SQLite returns naive datetimes; stored values are UTC
    return moment if moment.tzinfo else moment.replace(tzinfo=UTC)


def local_date(moment: datetime, tz: ZoneInfo) -> date:
    return as_utc(moment).astimezone(tz).date()


def doctor_days(
    session: Session, cfg: DemoConfig, tz: ZoneInfo
) -> dict[tuple[date, int], list[Slot]]:
    """Slots in the demo window by day and doctor, without days that already have bookings."""
    start = datetime.combine(cfg.today - timedelta(days=cfg.past_days), time(), tz)
    end = datetime.combine(cfg.today + timedelta(days=cfg.future_days), time(), tz)
    slots = session.scalars(
        select(Slot)
        .where(Slot.start_at >= start.astimezone(UTC), Slot.start_at < end.astimezone(UTC))
        .order_by(Slot.start_at, Slot.doctor_id)
    )
    days: dict[tuple[date, int], list[Slot]] = defaultdict(list)
    for slot in slots:
        days[(local_date(slot.start_at, tz), slot.doctor_id)].append(slot)

    # Days the seed booked are kept as they are, for example for attendance marking
    booked = session.execute(
        select(Slot.start_at, Slot.doctor_id).join(Appointment, Appointment.slot_id == Slot.id)
    )
    for start_at, doctor_id in booked:
        days.pop((local_date(start_at, tz), doctor_id), None)
    return dict(sorted(days.items(), key=lambda item: item[0]))


def seed(
    session: Session,
    cfg: DemoConfig,
    predictor: Predictor,
    rule: OverbookingRule,
    app_settings: Settings = settings,
) -> DemoResult:
    """Add patients and appointments booked with the overbooking rule to the seeded clinic."""
    if not session.scalar(select(func.count()).select_from(Doctor)):
        raise RuntimeError("No doctors found; run python -m web_backend.seed first")
    history = session.scalar(
        select(func.count())
        .select_from(Patient)
        .where(Patient.email.like(f"%@{HISTORY_EMAIL_DOMAIN}"))
    )
    if history:
        raise RuntimeError("The demo history already exists; start from an empty database")

    rng = random.Random(cfg.seed)
    tz: ZoneInfo = app_settings.clinic_timezone
    patients = DbPatientSource(session)
    slot_source = DbSlotSource(session, tz)
    hours_before = timedelta(hours=app_settings.reminders.hours_before)

    session.add_all(make_patient(rng, n) for n in range(1, cfg.patients + 1))
    session.flush()
    # Seeded patients with accounts get a history too, so their risks differ
    patient_ids = list(session.scalars(select(Patient.id).order_by(Patient.id)))
    result = {"appointments": 0, "overbooks": 0, "rejected": 0, "assignments": 0}

    # Days are processed in order, so earlier outcomes count as later patients' history
    for (day, _), slots in doctor_days(session, cfg, tz).items():
        is_past = day < cfg.today
        ratio = cfg.past_requests_per_slot if is_past else cfg.future_requests_per_slot
        for _ in range(round(len(slots) * ratio)):
            patient_id = rng.choice(patient_ids)
            # Future appointments are booked today at the latest
            booking_date = min(day - timedelta(days=lead_days(rng)), cfg.today)
            booked = book(
                session, patients, slot_source, predictor, rule, slots, patient_id, booking_date
            )
            if booked is None:
                result["rejected"] += 1
                continue
            appointment, p_noshow, overbook = booked
            result["appointments"] += 1
            result["overbooks"] += overbook
            if not is_past:
                continue

            # Past appointments get an outcome and, when eligible, an A/B group
            group = None
            booked_at = datetime.combine(booking_date, BOOKING_TIME, tz)
            slot_start = next(s.start_at for s in slots if s.id == appointment.slot_id)
            if as_utc(slot_start) - hours_before > booked_at:
                group = assign_group(patient_id, app_settings.ab_test.salt)
                session.add(
                    AbAssignment(appointment_id=appointment.id, patient_id=patient_id, group=group)
                )
                result["assignments"] += 1
            risk = p_noshow * (1 - cfg.reminder_effect) if group == "reminder" else p_noshow
            appointment.attended = rng.random() >= risk
            session.flush()

    result["assignments"] += group_seeded_bookings(session, cfg, app_settings)
    session.commit()
    return DemoResult(**result)


def group_seeded_bookings(session: Session, cfg: DemoConfig, app_settings: Settings) -> int:
    """A/B groups for the seed's unmarked past bookings, so marking them changes the A/B summary."""
    tz: ZoneInfo = app_settings.clinic_timezone
    hours_before = timedelta(hours=app_settings.reminders.hours_before)
    rows = session.execute(
        select(Appointment, Slot.start_at)
        .join(Slot, Slot.id == Appointment.slot_id)
        .outerjoin(AbAssignment, AbAssignment.appointment_id == Appointment.id)
        .where(
            Appointment.appointment_date < cfg.today,
            Appointment.attended.is_(None),
            AbAssignment.id.is_(None),
        )
        .order_by(Appointment.id)
    ).all()
    assigned = 0
    for appointment, start_at in rows:
        booked_at = datetime.combine(appointment.booking_date, BOOKING_TIME, tz)
        if as_utc(start_at) - hours_before > booked_at:
            group = assign_group(appointment.patient_id, app_settings.ab_test.salt)
            session.add(
                AbAssignment(
                    appointment_id=appointment.id, patient_id=appointment.patient_id, group=group
                )
            )
            assigned += 1
    return assigned


def book(
    session: Session,
    patients: DbPatientSource,
    slot_source: DbSlotSource,
    predictor: Predictor,
    rule: OverbookingRule,
    slots: list[Slot],
    patient_id: int,
    booking_date: date,
) -> tuple[Appointment, float, bool] | None:
    """Book the first empty slot, otherwise the first slot the rule allows to overbook."""
    states = [slot_source.get_slot(slot.id) for slot in slots]
    if any(b.patient_id == patient_id for state in states for b in state.bookings):
        return None
    candidates = [s for s in states if not s.bookings] + [s for s in states if s.bookings]
    for state in candidates:
        decision, p_noshow, _ = evaluate(
            patients, slot_source, predictor, rule, patient_id, state, booking_date
        )
        if decision.allow:
            appointment = Appointment(
                patient_id=patient_id,
                slot_id=state.slot_id,
                appointment_date=state.slot_date,
                booking_date=booking_date,
            )
            session.add(appointment)
            session.flush()
            return appointment, p_noshow, decision.overbook
    return None


def example_slots(
    session: Session, after: date, tz: ZoneInfo
) -> tuple[str, date, int | None, int | None] | None:
    """An empty and a booked slot of the first doctor working after a day, for trying the API."""
    start = datetime.combine(after + timedelta(days=1), time(), tz).astimezone(UTC)
    first = session.scalar(select(Slot).where(Slot.start_at >= start).order_by(Slot.start_at))
    if first is None:
        return None
    day = local_date(first.start_at, tz)
    day_start = datetime.combine(day, time(), tz).astimezone(UTC)
    rows = session.execute(
        select(Slot.id, func.count(Appointment.id))
        .outerjoin(Appointment, Appointment.slot_id == Slot.id)
        .where(
            Slot.doctor_id == first.doctor_id,
            Slot.start_at >= day_start,
            Slot.start_at < day_start + timedelta(days=1),
        )
        .group_by(Slot.id)
        .order_by(Slot.start_at)
    ).all()
    empty = next((slot_id for slot_id, n in rows if n == 0), None)
    booked = next((slot_id for slot_id, n in rows if n == 1), None)
    doctor = session.get(Doctor, first.doctor_id)
    return doctor.full_name, day, empty, booked


def main() -> None:
    parser = argparse.ArgumentParser(description=__doc__.splitlines()[0])
    parser.add_argument("--today", type=date.fromisoformat, help="Demo date; default today")
    parser.add_argument("--seed", type=int, default=42)
    parser.add_argument("--reminder-effect", type=float, default=0.0)
    args = parser.parse_args()

    today = args.today or datetime.now(settings.clinic_timezone).date()
    cfg = DemoConfig(today=today, seed=args.seed, reminder_effect=args.reminder_effect)
    with SessionLocal() as session:
        try:
            result = seed(session, cfg, Predictor.load(settings.model_dir), settings.overbooking)
        except RuntimeError as exc:
            raise SystemExit(str(exc)) from exc
        example = example_slots(session, today, settings.clinic_timezone)
    print(
        f"Demo history for {today}: {result.appointments} appointments "
        f"({result.overbooks} overbooks), {result.rejected} requests rejected, "
        f"{result.assignments} A/B assignments"
    )
    if example is not None:
        doctor, day, empty, booked = example
        print(f"Slots of {doctor} on {day}: empty slot {empty}, booked slot {booked}")


if __name__ == "__main__":
    main()
