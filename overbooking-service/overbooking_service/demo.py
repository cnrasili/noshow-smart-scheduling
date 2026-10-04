"""Fill an empty booking database with simulated demo data.

Usage: python -m overbooking_service.demo [--today 2026-11-16] [--seed 42]
"""

import argparse
import random
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

DOCTORS = ["Dr. Ada Demir", "Dr. Bora Kaya"]
SESSION_START = time(9, 0)
# Booking time on the booking date, used to decide reminder eligibility
BOOKING_TIME = time(8, 0)


@dataclass(frozen=True)
class DemoConfig:
    today: date
    seed: int = 42
    patients: int = 200
    past_days: int = 10
    future_days: int = 5
    slots_per_day: int = 16
    slot_minutes: int = 15
    requests_per_day: int = 20
    future_requests_per_day: int = 8
    # Relative no-show reduction for the reminder group; 0 means reminders have no effect
    reminder_effect: float = 0.0


@dataclass(frozen=True)
class DemoResult:
    appointments: int
    overbooks: int
    rejected: int
    assignments: int


def working_days(start: date, count: int, step: int) -> list[date]:
    """Weekdays from start (exclusive) walking step days at a time."""
    days: list[date] = []
    current = start
    while len(days) < count:
        current += timedelta(days=step)
        if current.weekday() < 5:
            days.append(current)
    return sorted(days)


def lead_days(rng: random.Random) -> int:
    # Same-day, within a week and later bookings, roughly as in the public dataset
    bucket = rng.choices(["same", "week", "later"], weights=[15, 45, 40])[0]
    if bucket == "same":
        return 0
    if bucket == "week":
        return rng.randint(1, 7)
    return rng.randint(8, 30)


def make_patient(rng: random.Random, patient_id: int) -> Patient:
    return Patient(
        id=patient_id,
        full_name=f"Demo Patient {patient_id}",
        email=f"patient{patient_id}@example.com",
        age=rng.randint(1, 90),
        gender="F" if rng.random() < 0.65 else "M",
        scholarship=rng.random() < 0.10,
        hipertension=rng.random() < 0.20,
        diabetes=rng.random() < 0.07,
        alcoholism=rng.random() < 0.03,
        handcap=1 if rng.random() < 0.02 else 0,
    )


def seed(
    session: Session,
    cfg: DemoConfig,
    predictor: Predictor,
    rule: OverbookingRule,
    app_settings: Settings = settings,
) -> DemoResult:
    """Create doctors, patients, slots and appointments booked with the overbooking rule."""
    if session.scalar(select(func.count()).select_from(Doctor)):
        raise RuntimeError("The booking database is not empty; demo data needs an empty database")

    rng = random.Random(cfg.seed)
    tz: ZoneInfo = app_settings.clinic_timezone
    patients = DbPatientSource(session)
    slot_source = DbSlotSource(session, tz)
    hours_before = timedelta(hours=app_settings.reminders.hours_before)

    session.add_all(Doctor(id=i, full_name=name) for i, name in enumerate(DOCTORS, start=1))
    session.add_all(make_patient(rng, i) for i in range(1, cfg.patients + 1))
    session.flush()

    past = working_days(cfg.today, cfg.past_days, -1)
    future = working_days(cfg.today - timedelta(days=1), cfg.future_days, 1)
    result = {"appointments": 0, "overbooks": 0, "rejected": 0, "assignments": 0}

    for day in past + future:
        is_past = day < cfg.today
        for doctor_id in range(1, len(DOCTORS) + 1):
            start = datetime.combine(day, SESSION_START, tz)
            slots = [
                Slot(
                    doctor_id=doctor_id,
                    start_at=(start + timedelta(minutes=cfg.slot_minutes * k)).astimezone(UTC),
                    end_at=(start + timedelta(minutes=cfg.slot_minutes * (k + 1))).astimezone(UTC),
                )
                for k in range(cfg.slots_per_day)
            ]
            session.add_all(slots)
            session.flush()

            requests = cfg.requests_per_day if is_past else cfg.future_requests_per_day
            for _ in range(requests):
                patient_id = rng.randint(1, cfg.patients)
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
                if slot_start - hours_before > booked_at:
                    group = assign_group(patient_id, app_settings.ab_test.salt)
                    session.add(
                        AbAssignment(
                            appointment_id=appointment.id, patient_id=patient_id, group=group
                        )
                    )
                    result["assignments"] += 1
                risk = p_noshow * (1 - cfg.reminder_effect) if group == "reminder" else p_noshow
                appointment.attended = rng.random() >= risk
                session.flush()

    session.commit()
    return DemoResult(**result)


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


def example_slots(session: Session, day: date, tz: ZoneInfo) -> tuple[int | None, int | None]:
    """An empty and a booked slot of the first doctor on a day, for trying the API."""
    start = datetime.combine(day, time(), tz).astimezone(UTC)
    rows = session.execute(
        select(Slot.id, func.count(Appointment.id))
        .outerjoin(Appointment, Appointment.slot_id == Slot.id)
        .where(
            Slot.doctor_id == 1, Slot.start_at >= start, Slot.start_at < start + timedelta(days=1)
        )
        .group_by(Slot.id)
        .order_by(Slot.start_at)
    ).all()
    empty = next((slot_id for slot_id, n in rows if n == 0), None)
    booked = next((slot_id for slot_id, n in rows if n == 1), None)
    return empty, booked


def main() -> None:
    parser = argparse.ArgumentParser(description=__doc__.splitlines()[0])
    parser.add_argument("--today", type=date.fromisoformat, help="Demo date; default today")
    parser.add_argument("--seed", type=int, default=42)
    parser.add_argument("--reminder-effect", type=float, default=0.0)
    args = parser.parse_args()

    today = args.today or datetime.now(settings.clinic_timezone).date()
    cfg = DemoConfig(today=today, seed=args.seed, reminder_effect=args.reminder_effect)
    with SessionLocal() as session:
        result = seed(session, cfg, Predictor.load(settings.model_dir), settings.overbooking)
        tomorrow = working_days(today, 1, 1)[0]
        empty, booked = example_slots(session, tomorrow, settings.clinic_timezone)
    print(
        f"Demo data for {today}: {result.appointments} appointments "
        f"({result.overbooks} overbooks), {result.rejected} requests rejected, "
        f"{result.assignments} A/B assignments"
    )
    print(f"Slots of doctor 1 on {tomorrow}: empty slot {empty}, booked slot {booked}")


if __name__ == "__main__":
    main()
