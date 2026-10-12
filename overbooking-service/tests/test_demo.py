from collections import Counter
from collections.abc import Callable
from datetime import UTC, date
from zoneinfo import ZoneInfo

import pytest
from sqlalchemy import create_engine, select
from sqlalchemy.orm import Session, sessionmaker
from sqlalchemy.pool import StaticPool

from noshow_db.base import Base
from noshow_db.models.core import Appointment, Patient, Slot
from noshow_db.models.service import AbAssignment, BookingDecision
from overbooking_service.ab import assign_group
from overbooking_service.config import settings
from overbooking_service.demo import DemoConfig, free_national_ids, seed
from overbooking_service.national_id import fictional_national_id
from overbooking_service.predictor import Predictor
from overbooking_service.rules import OverbookingRule

TODAY = date(2026, 11, 16)
# Last working day before TODAY; the clinic fixture books doctor 1 on it
SEEDED_DAY = date(2026, 11, 13)
SEEDED_PATIENTS = 8
CLINIC = ZoneInfo("Europe/Istanbul")
# Low threshold so that the small demo also overbooks
RULE = OverbookingRule(threshold=0.10, daily_overbook_limit=2)
SMALL = DemoConfig(today=TODAY, seed=7, patients=40, past_days=7, future_days=3)

Clinic = Callable[[Session, date], None]


@pytest.fixture(scope="module")
def predictor() -> Predictor:
    return Predictor.load(settings.model_dir)


def new_session() -> Session:
    engine = create_engine(
        "sqlite://", connect_args={"check_same_thread": False}, poolclass=StaticPool
    )
    Base.metadata.create_all(engine)
    return sessionmaker(bind=engine)()


def seeded_clinic(clinic: Clinic) -> Session:
    session = new_session()
    clinic(session, TODAY)
    return session


@pytest.fixture(scope="module")
def seeded(clinic: Clinic, predictor: Predictor) -> Session:
    session = seeded_clinic(clinic)
    seed(session, SMALL, predictor, RULE)
    return session


def rows(session: Session) -> list[tuple[Appointment, Slot]]:
    return [(a, s) for a, s in session.execute(select(Appointment, Slot).join(Slot))]


def local_date(slot: Slot) -> date:
    return slot.start_at.replace(tzinfo=UTC).astimezone(CLINIC).date()


def is_seeded(slot: Slot) -> bool:
    return slot.doctor_id == 1 and local_date(slot) == SEEDED_DAY


def test_seed_is_reproducible(clinic: Clinic, predictor: Predictor):
    first, second = seeded_clinic(clinic), seeded_clinic(clinic)
    assert seed(first, SMALL, predictor, RULE) == seed(second, SMALL, predictor, RULE)
    outcomes = [
        list(s.scalars(select(Appointment.attended).order_by(Appointment.id)))
        for s in (first, second)
    ]
    assert outcomes[0] == outcomes[1]


def test_seed_uses_the_clinic_slots(seeded: Session):
    result = rows(seeded)
    assert {slot.doctor_id for _, slot in result} == {1, 2}
    days = {local_date(slot) for _, slot in result}
    assert min(days) >= date(2026, 11, 9) and max(days) <= date(2026, 11, 19)


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


def test_seed_logs_its_decisions(seeded: Session):
    decisions = list(seeded.scalars(select(BookingDecision)))
    generated = [(a, slot) for a, slot in rows(seeded) if not is_seeded(slot)]
    per_slot = Counter(slot.id for _, slot in generated)

    # Every generated appointment has the decision that granted it
    granted = Counter((d.patient_id, d.slot_id) for d in decisions if d.allow)
    assert granted == Counter((a.patient_id, slot.id) for a, slot in generated)
    assert sum(d.overbook for d in decisions) == sum(n - 1 for n in per_slot.values())
    assert {d.threshold for d in decisions} == {RULE.threshold}


def test_seed_logs_refused_requests(clinic: Clinic, predictor: Predictor):
    session = seeded_clinic(clinic)
    # No overbooking, so requests beyond the slot capacity are refused
    strict = OverbookingRule(threshold=0.99, daily_overbook_limit=0)
    result = seed(session, SMALL, predictor, strict)
    refused = list(session.scalars(select(BookingDecision).where(BookingDecision.allow.is_(False))))
    assert 0 < len(refused) <= result.rejected
    assert all(d.reason.startswith("Slot is") for d in refused)


def test_seeded_dates_are_consistent(seeded: Session):
    for appointment, slot in rows(seeded):
        assert appointment.appointment_date == local_date(slot)
        assert appointment.booking_date <= min(appointment.appointment_date, TODAY)
        assert slot.start_at.replace(tzinfo=UTC).astimezone(CLINIC).hour >= 9


def test_seeded_day_is_left_for_attendance_marking(seeded: Session):
    booked = [(a, s) for a, s in rows(seeded) if is_seeded(s)]
    assert len(booked) == 5
    assert all(a.attended is None for a, _ in booked)


def test_only_generated_past_appointments_have_outcomes(seeded: Session):
    for appointment, slot in rows(seeded):
        if appointment.appointment_date < TODAY and not is_seeded(slot):
            assert appointment.attended is not None
        elif appointment.appointment_date >= TODAY:
            assert appointment.attended is None


def test_seeded_patients_get_a_history(seeded: Session):
    patients = {a.patient_id for a, s in rows(seeded) if not is_seeded(s)}
    assert patients & set(range(1, SEEDED_PATIENTS + 1))


def test_past_eligible_appointments_get_groups(seeded: Session):
    assignments = list(seeded.scalars(select(AbAssignment)))
    assert assignments
    dates = {a.id: a.appointment_date for a in seeded.scalars(select(Appointment))}
    for assignment in assignments:
        assert dates[assignment.appointment_id] < TODAY
        assert assignment.group == assign_group(assignment.patient_id, settings.ab_test.salt)


def test_seeded_bookings_get_groups(seeded: Session):
    grouped = set(seeded.scalars(select(AbAssignment.appointment_id)))
    assert all(a.id in grouped for a, s in rows(seeded) if is_seeded(s))


def test_reminder_effect_lowers_reminder_group_no_shows(clinic: Clinic, predictor: Predictor):
    session = seeded_clinic(clinic)
    cfg = DemoConfig(
        today=TODAY, seed=7, patients=40, past_days=7, future_days=1, reminder_effect=1.0
    )
    seed(session, cfg, predictor, RULE)
    reminder_outcomes = session.scalars(
        select(Appointment.attended)
        .join(AbAssignment, AbAssignment.appointment_id == Appointment.id)
        .where(AbAssignment.group == "reminder", Appointment.attended.is_not(None))
    ).all()
    assert reminder_outcomes and all(reminder_outcomes)


def test_seed_refuses_database_without_doctors(predictor: Predictor):
    with pytest.raises(RuntimeError, match="web_backend.seed first"):
        seed(new_session(), SMALL, predictor, RULE)


def test_seed_refuses_second_run(seeded: Session, predictor: Predictor):
    with pytest.raises(RuntimeError, match="already exists"):
        seed(seeded, SMALL, predictor, RULE)


def is_valid_national_id(value: str) -> bool:
    # Official rules, written independently of the code under test
    d = [int(c) for c in value]
    return (
        len(d) == 11
        and d[0] != 0
        and d[9] == ((d[0] + d[2] + d[4] + d[6] + d[8]) * 7 - (d[1] + d[3] + d[5] + d[7])) % 10
        and d[10] == sum(d[:10]) % 10
    )


def test_fictional_national_ids_follow_the_web_backend_pattern():
    # The web backend seed's first demo patient has this number
    assert fictional_national_id(1) == "99999000184"
    assert all(is_valid_national_id(fictional_national_id(n)) for n in range(0, 10000, 7))
    with pytest.raises(ValueError):
        fictional_national_id(10000)


def test_generated_patients_get_unique_fictional_national_ids(seeded: Session):
    national_ids = list(seeded.scalars(select(Patient.national_id)))
    assert len(national_ids) == len(set(national_ids)) == SEEDED_PATIENTS + SMALL.patients
    assert all(is_valid_national_id(nid) and nid.startswith("99999") for nid in national_ids)
    generated = seeded.scalars(
        select(Patient.national_id).where(Patient.email.like("%@history.example.com"))
    ).all()
    assert all(int(nid[5:9]) >= 1000 for nid in generated)


def test_free_national_ids_skip_numbers_in_use(clinic: Clinic):
    session = seeded_clinic(clinic)
    session.add(
        Patient(
            national_id=fictional_national_id(1000),
            full_name="Existing",
            email="existing@demo.local",
            age=50,
            gender="M",
        )
    )
    session.flush()
    assert free_national_ids(session, 2) == [
        fictional_national_id(1001),
        fictional_national_id(1002),
    ]
