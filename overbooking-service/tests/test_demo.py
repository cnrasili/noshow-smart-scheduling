from collections import Counter
from datetime import UTC, date
from zoneinfo import ZoneInfo

import pytest
from sqlalchemy import create_engine, select
from sqlalchemy.orm import Session, sessionmaker
from sqlalchemy.pool import StaticPool

from noshow_db.base import Base
from noshow_db.models.core import Appointment, Slot
from noshow_db.models.service import AbAssignment
from overbooking_service.ab import assign_group
from overbooking_service.config import settings
from overbooking_service.demo import DemoConfig, seed
from overbooking_service.predictor import Predictor
from overbooking_service.rules import OverbookingRule

TODAY = date(2026, 11, 16)
CLINIC = ZoneInfo("Europe/Istanbul")
# Low threshold so that the small demo also overbooks
RULE = OverbookingRule(threshold=0.10, daily_overbook_limit=2)
SMALL = DemoConfig(today=TODAY, seed=7, patients=40, past_days=3, future_days=2)


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
def seeded(predictor: Predictor) -> Session:
    session = new_session()
    seed(session, SMALL, predictor, RULE)
    return session


def rows(session: Session) -> list[tuple[Appointment, Slot]]:
    return [(a, s) for a, s in session.execute(select(Appointment, Slot).join(Slot))]


def local_date(slot: Slot) -> date:
    return slot.start_at.replace(tzinfo=UTC).astimezone(CLINIC).date()


def test_seed_is_reproducible(predictor: Predictor):
    first, second = new_session(), new_session()
    assert seed(first, SMALL, predictor, RULE) == seed(second, SMALL, predictor, RULE)
    outcomes = [
        list(s.scalars(select(Appointment.attended).order_by(Appointment.id)))
        for s in (first, second)
    ]
    assert outcomes[0] == outcomes[1]


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
    for appointment, slot in rows(seeded):
        assert appointment.appointment_date == local_date(slot)
        assert appointment.booking_date <= min(appointment.appointment_date, TODAY)
        assert slot.start_at.replace(tzinfo=UTC).astimezone(CLINIC).hour >= 9


def test_only_past_appointments_have_outcomes(seeded: Session):
    for appointment, _ in rows(seeded):
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


def test_reminder_effect_lowers_reminder_group_no_shows(predictor: Predictor):
    session = new_session()
    cfg = DemoConfig(
        today=TODAY, seed=7, patients=40, past_days=3, future_days=1, reminder_effect=1.0
    )
    seed(session, cfg, predictor, RULE)
    reminder_outcomes = session.scalars(
        select(Appointment.attended)
        .join(AbAssignment, AbAssignment.appointment_id == Appointment.id)
        .where(AbAssignment.group == "reminder")
    ).all()
    assert reminder_outcomes and all(reminder_outcomes)


def test_seed_refuses_non_empty_database(seeded: Session, predictor: Predictor):
    with pytest.raises(RuntimeError, match="not empty"):
        seed(seeded, SMALL, predictor, RULE)
