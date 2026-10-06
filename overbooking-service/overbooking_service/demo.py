"""Add simulated booking history to the clinic created by the web backend seed.

Run ``python -m web_backend.seed`` first.
Usage: python -m overbooking_service.demo [--today 2026-11-16] [--seed 42]
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

# Booking time on the booking date, used to decide reminder eligibility
BOOKING_TIME = time(8, 0)
# Email domain of the generated patients; marks a database that already has demo history
PATIENT_DOMAIN = "history.example.com"


@dataclass(frozen=True)
class DemoConfig:
    today: date
    seed: int = 42
    patients: int = 200
    # Calendar days of history before the demo date and of bookings from it
    past_days: int = 21
    future_days: int = 7
    # Booking requests per slot of a doctor-day
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
        email=f"patient{number}@{PATIENT_DOMAIN}",
        age=rng.randint(1, 90),
        gender="F" if rng.random() < 0.65 else "M",
        scholarship=rng.random() < 0.10,
        hipertension=rng.random() < 0.20,
        diabetes=rng.random() < 0.07,
        alcoholism=rng.random() < 0.03,
        handcap=1 if rng.random() < 0.02 else 0,
    )


def as_utc(value: datetime) -> datetime:
    # SQLite returns naive datetimes; they are stored in UTC
    return value.replace(tzinfo=UTC) if value.tzinfo is None else value


def doctor_days(
    session: Session, start: date, end: date, tz: ZoneInfo
) -> dict[tuple[int, date], list[Slot]]:
    """Slots per doctor and clinic date between two dates, both inclusive."""
    first = datetime.combine(start, time(), tz).astimezone(UTC)
    last = datetime.combine(end + timedelta(days=1), time(), tz).astimezone(UTC)
    days: dict[tuple[int, date], list[Slot]] = defaultdict(list)
    for slot in session.scalars(
        select(Slot).where(Slot.start_at >= first, Slot.start_at < last).order_by(Slot.start_at)
    ):
        days[(slot.doctor_id, as_utc(slot.start_at).astimezone(tz).date())].append(slot)
    return days


def reminder_possible(
    slot_start: datetime, booking_date: date, tz: ZoneInfo, app_settings: Settings
) -> bool:
    booked_at = datetime.combine(booking_date, BOOKING_TIME, tz)
    return as_utc(slot_start) - timedelta(hours=app_settings.reminders.hours_before) > booked_at


def seed(
    session: Session,
    cfg: DemoConfig,
    predictor: Predictor,
    rule: OverbookingRule,
    app_settings: Settings = settings,
) -> DemoResult:
    """Book patients into the seeded doctors' slots with the overbooking rule."""
    if not session.scalar(select(func.count()).select_from(Doctor)):
        raise RuntimeError("No doctors found; run python -m web_backend.seed first")
    if session.scalar(select(Patient.id).where(Patient.email.like(f"%@{PATIENT_DOMAIN}"))):
        raise RuntimeError("Demo history already exists; start from a new seeded database")

    rng = random.Random(cfg.seed)
    tz: ZoneInfo = app_settings.clinic_timezone
    patients = DbPatientSource(session)
    slot_source = DbSlotSource(session, tz)

    session.add_all(make_patient(rng, n) for n in range(1, cfg.patients + 1))
    session.flush()
    # Seeded patients with accounts also get a history, so their predictions differ
    patient_ids = list(session.scalars(select(Patient.id).order_by(Patient.id)))

    days = doctor_days(
        session,
        cfg.today - timedelta(days=cfg.past_days),
        cfg.today + timedelta(days=cfg.future_days),
        tz,
    )
    result = {"appointments": 0, "overbooks": 0, "rejected": 0, "assignments": 0}
    result["assignments"] += group_seeded_bookings(session, cfg, app_settings)

    # Doctor-days the seed already booked stay as they are for attendance marking
    seeded_days = {
        (doctor_id, day)
        for doctor_id, day in session.execute(
            select(Slot.doctor_id, Appointment.appointment_date).join(Slot)
        )
    }

    for (doctor_id, day), slots in sorted(days.items()):
        if (doctor_id, day) in seeded_days:
            continue
        is_past = day < cfg.today
        per_slot = cfg.past_requests_per_slot if is_past else cfg.future_requests_per_slot
        for _ in range(round(per_slot * len(slots))):
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
            slot_start = next(s.start_at for s in slots if s.id == appointment.slot_id)
            if reminder_possible(slot_start, booking_date, tz, app_settings):
                group = assign_group(patient_id, app_settings.ab_test.salt)
                session.add(
                    AbAssignment(appointment_id=appointment.id, patient_id=patient_id, group=group)
                )
                result["assignments"] += 1
            risk = p_noshow * (1 - cfg.reminder_effect) if group == "reminder" else p_noshow
            appointment.attended = rng.random() >= risk
            session.flush()

    session.commit()
    return DemoResult(**result)


def group_seeded_bookings(session: Session, cfg: DemoConfig, app_settings: Settings) -> int:
    """A/B groups for the seed's past bookings, so marking attendance changes the summary."""
    tz: ZoneInfo = app_settings.clinic_timezone
    rows = session.execute(
        select(Appointment, Slot.start_at)
        .join(Slot)
        .outerjoin(AbAssignment, AbAssignment.appointment_id == Appointment.id)
        .where(Appointment.appointment_date < cfg.today, AbAssignment.id.is_(None))
    ).all()
    count = 0
    for appointment, slot_start in rows:
        if reminder_possible(slot_start, appointment.booking_date, tz, app_settings):
            group = assign_group(appointment.patient_id, app_settings.ab_test.salt)
            session.add(
                AbAssignment(
                    appointment_id=appointment.id, patient_id=appointment.patient_id, group=group
                )
            )
            count += 1
    session.flush()
    return count


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
    session: Session, today: date, tz: ZoneInfo
) -> tuple[int | None, date | None, int | None, int | None]:
    """The first doctor with slots after today: doctor, day, an empty and a booked slot."""
    start = datetime.combine(today + timedelta(days=1), time(), tz).astimezone(UTC)
    first = session.scalars(
        select(Slot).where(Slot.start_at >= start).order_by(Slot.start_at, Slot.doctor_id)
    ).first()
    if first is None:
        return None, None, None, None
    day = as_utc(first.start_at).astimezone(tz).date()
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
    return first.doctor_id, day, empty, booked


def main() -> None:
    parser = argparse.ArgumentParser(description=__doc__.splitlines()[0])
    parser.add_argument("--today", type=date.fromisoformat, help="Demo date; default today")
    parser.add_argument("--seed", type=int, default=42)
    parser.add_argument("--reminder-effect", type=float, default=0.0)
    args = parser.parse_args()

    tz = settings.clinic_timezone
    today = args.today or datetime.now(tz).date()
    cfg = DemoConfig(today=today, seed=args.seed, reminder_effect=args.reminder_effect)
    with SessionLocal() as session:
        try:
            result = seed(session, cfg, Predictor.load(settings.model_dir), settings.overbooking)
        except RuntimeError as exc:
            raise SystemExit(str(exc)) from None
        doctor_id, day, empty, booked = example_slots(session, today, tz)
    print(
        f"Demo history for {today}: {result.appointments} appointments "
        f"({result.overbooks} overbooks), {result.rejected} requests rejected, "
        f"{result.assignments} A/B assignments"
    )
    if doctor_id is not None:
        print(f"Slots of doctor {doctor_id} on {day}: empty slot {empty}, booked slot {booked}")


if __name__ == "__main__":
    main()
