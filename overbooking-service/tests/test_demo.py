from collections import Counter
from collections.abc import Callable
from datetime import UTC, date, datetime, time, timedelta
from zoneinfo import ZoneInfo

import pytest
from sqlalchemy import create_engine, func, select
from sqlalchemy.orm import Session, sessionmaker
from sqlalchemy.pool import StaticPool

from noshow_db.base import Base
from noshow_db.models.core import Appointment, Doctor, Patient, Slot
from noshow_db.models.service import AbAssignment
from overbooking_service.ab import assign_group
from overbooking_service.config import settings
from overbooking_service.demo import HISTORY_EMAIL_DOMAIN, DemoConfig, seed
from overbooking_service.predictor import Predictor
from overbooking_service.rules import OverbookingRule

TODAY = date(2026, 11, 16)
CLINIC = ZoneInfo("Europe/Istanbul")
# Low threshold so that the small demo also overbooks
RULE = OverbookingRule(threshold=0.10, daily_overbook_limit=2)
SMALL = DemoConfig(today=TODAY, seed=7, patients=40, past_days=7, future_days=3)
# The seeded clinic's example booking is on this day of the first doctor
EXAMPLE_DAY = date(2026, 11, 13)


@pytest.fixture(scope="module")
def predictor() -> Predictor:
    return Predictor.load(settings.model_dir)


def new_session() -> Session:
    engine = create_engine(
        "sqlite://", connect_args={"check_same_thread": False}, poolclass=StaticPool
    )
    Base.metadata.create_all(engine)
    return sessionmaker(bind=engine)()


@pytest.fixture(scope="module")
def seeded_clinic(clinic: Callable[[Session, date, date], None]) -> Callable[[], Session]:
    """The seeded clinic with one account patient and one example booking."""

    def make() -> Session:
        session = new_session()
        clinic(session, TODAY - timedelta(days=SMALL.past_days + 2), TODAY + timedelta(days=5))
        session.add(Patient(id=1, full_name="Account", email="p@demo.local", age=40, gender="F"))
        example = session.scalar(
            select(Slot)
            .where(
                Slot.doctor_id == 1,
                Slot.start_at >= datetime.combine(EXAMPLE_DAY, time(), CLINIC).astimezone(UTC),
            )
            .order_by(Slot.start_at)
        )
        session.add(
            Appointment(
                patient_id=1,
                slot_id=example.id,
                appointment_date=EXAMPLE_DAY,
                booking_date=EXAMPLE_DAY - timedelta(days=5),
            )
        )
        session.commit()
        return session

    return make


@pytest.fixture(scope="module")
def seeded(predictor: Predictor, seeded_clinic: Callable[[], Session]) -> Session:
    session = seeded_clinic()
    seed(session, SMALL, predictor, RULE)
    return session


def rows(session: Session) -> list[tuple[Appointment, Slot]]:
    return [(a, s) for a, s in session.execute(select(Appointment, Slot).join(Slot))]


def local_date(slot: Slot) -> date:
    return slot.start_at.replace(tzinfo=UTC).astimezone(CLINIC).date()


def is_example(appointment: Appointment) -> bool:
    return appointment.patient_id == 1 and appointment.appointment_date == EXAMPLE_DAY


def test_seed_is_reproducible(predictor: Predictor, seeded_clinic: Callable[[], Session]):
    first, second = seeded_clinic(), seeded_clinic()
    assert seed(first, SMALL, predictor, RULE) == seed(second, SMALL, predictor, RULE)
    outcomes = [
        list(s.scalars(select(Appointment.attended).order_by(Appointment.id)))
        for s in (first, second)
    ]
    assert outcomes[0] == outcomes[1]


def test_seed_builds_on_the_seeded_clinic(seeded: Session):
    assert seeded.scalar(select(func.count()).select_from(Doctor)) == 2
    history = seeded.scalar(
        select(func.count())
        .select_from(Patient)
        .where(Patient.email.like(f"%@{HISTORY_EMAIL_DOMAIN}"))
    )
    assert history == SMALL.patients
    assert {slot.doctor_id for _, slot in rows(seeded)} == {1, 2}


def test_seed_books_with_the_overbooking_rule(seeded: Session):
    result = rows(seeded)
    per_slot = Counter(slot.id for _, slot in result)
    slots = {slot.id: slot for _, slot in result}
    assert all(n <= slots[slot_id].max_patients for slot_id, n in per_slot.items())

    overbooks = Counter(
        (slot.doctor_id, local_date(slot))
        for slot_id, slot in slots.items()
        for _ in range(per_slot[slot_id] - 1)
    )
    assert overbooks, "small demo should overbook with a low threshold"
    assert max(overbooks.values()) <= RULE.daily_overbook_limit


def test_seeded_dates_are_consistent(seeded: Session):
    first_day = TODAY - timedelta(days=SMALL.past_days)
    for appointment, slot in rows(seeded):
        assert appointment.appointment_date == local_date(slot)
        assert appointment.booking_date <= min(appointment.appointment_date, TODAY)
        assert first_day <= appointment.appointment_date
        assert appointment.appointment_date < TODAY + timedelta(days=SMALL.future_days)


def test_days_with_seeded_bookings_are_left_alone(seeded: Session):
    on_example_day = [
        appointment
        for appointment, slot in rows(seeded)
        if slot.doctor_id == 1 and appointment.appointment_date == EXAMPLE_DAY
    ]
    assert len(on_example_day) == 1
    assert on_example_day[0].attended is None


def test_seeded_past_bookings_get_groups_for_attendance_marking(seeded: Session):
    example = seeded.scalar(
        select(Appointment).where(Appointment.patient_id == 1, Appointment.attended.is_(None))
    )
    assignment = seeded.scalar(
        select(AbAssignment).where(AbAssignment.appointment_id == example.id)
    )
    assert assignment is not None
    assert assignment.group == assign_group(1, settings.ab_test.salt)


def test_only_past_history_appointments_have_outcomes(seeded: Session):
    for appointment, _ in rows(seeded):
        if is_example(appointment):
            continue
        if appointment.appointment_date < TODAY:
            assert appointment.attended is not None
        else:
            assert appointment.attended is None


def test_past_eligible_appointments_get_groups(seeded: Session):
    assignments = list(seeded.scalars(select(AbAssignment)))
    assert assignments
    dates = {a.id: a.appointment_date for a in seeded.scalars(select(Appointment))}
    for assignment in assignments:
        assert dates[assignment.appointment_id] < TODAY
        assert assignment.group == assign_group(assignment.patient_id, settings.ab_test.salt)


def test_reminder_effect_lowers_reminder_group_no_shows(
    predictor: Predictor, seeded_clinic: Callable[[], Session]
):
    session = seeded_clinic()
    cfg = DemoConfig(
        today=TODAY, seed=7, patients=40, past_days=7, future_days=1, reminder_effect=1.0
    )
    seed(session, cfg, predictor, RULE)
    reminder_outcomes = session.scalars(
        select(Appointment.attended)
        .join(AbAssignment, AbAssignment.appointment_id == Appointment.id)
        .where(AbAssignment.group == "reminder")
    ).all()
    assert reminder_outcomes and all(reminder_outcomes)


def test_seed_needs_the_seeded_clinic(predictor: Predictor):
    with pytest.raises(RuntimeError, match="web_backend.seed"):
        seed(new_session(), SMALL, predictor, RULE)


def test_seed_refuses_to_run_twice(seeded: Session, predictor: Predictor):
    with pytest.raises(RuntimeError, match="already exists"):
        seed(seeded, SMALL, predictor, RULE)
