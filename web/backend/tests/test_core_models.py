from collections.abc import Iterator
from datetime import UTC, date, datetime, time

import pytest
from sqlalchemy import create_engine, func, inspect, select
from sqlalchemy.exc import IntegrityError
from sqlalchemy.orm import Session, sessionmaker
from sqlalchemy.pool import StaticPool

import noshow_db.models  # noqa: F401
from noshow_db.base import Base
from noshow_db.models.core import Appointment, Doctor, DoctorSchedule, Patient, Slot


@pytest.fixture
def session() -> Iterator[Session]:
    engine = create_engine(
        "sqlite://", connect_args={"check_same_thread": False}, poolclass=StaticPool
    )
    Base.metadata.create_all(engine)
    with sessionmaker(bind=engine)() as db_session:
        yield db_session


def _patient(email: str = "patient@example.com", age: int = 30) -> Patient:
    return Patient(
        full_name="Test Patient",
        email=email,
        age=age,
        gender="F",
        scholarship=False,
        hipertension=True,
        diabetes=False,
        alcoholism=False,
        handcap=0,
    )


def _slot(session: Session) -> Slot:
    doctor = Doctor(full_name="Dr. Test", specialty="General")
    session.add(doctor)
    session.flush()
    slot = Slot(
        doctor_id=doctor.id,
        start_at=datetime(2026, 11, 10, 9, 30, tzinfo=UTC),
        end_at=datetime(2026, 11, 10, 10, 0, tzinfo=UTC),
        max_patients=2,
    )
    session.add(slot)
    session.flush()
    return slot


def test_core_tables_exist(session: Session) -> None:
    tables = set(inspect(session.get_bind()).get_table_names())
    assert {"patients", "doctors", "doctor_schedules", "slots", "appointments"} <= tables


def test_patient_stores_booking_features(session: Session) -> None:
    session.add(_patient())
    session.commit()

    stored = session.scalars(select(Patient)).one()
    assert stored.age == 30
    assert stored.gender == "F"
    assert stored.scholarship is False
    assert stored.hipertension is True
    assert stored.diabetes is False
    assert stored.alcoholism is False
    assert stored.handcap == 0


def test_two_patients_can_share_a_slot(session: Session) -> None:
    slot = _slot(session)
    first = _patient("first@example.com")
    second = _patient("second@example.com")
    session.add_all([first, second])
    session.flush()

    appointment_date = date(2026, 11, 10)
    session.add_all(
        [
            Appointment(
                patient_id=first.id,
                slot_id=slot.id,
                appointment_date=appointment_date,
                booking_date=date(2026, 11, 2),
            ),
            Appointment(
                patient_id=second.id,
                slot_id=slot.id,
                appointment_date=appointment_date,
                booking_date=date(2026, 11, 3),
            ),
        ]
    )
    session.commit()

    assert session.scalar(select(func.count()).select_from(Appointment)) == 2
    assert session.scalars(select(Appointment)).first().attended is None


def test_same_patient_cannot_book_a_slot_twice(session: Session) -> None:
    slot = _slot(session)
    patient = _patient()
    session.add(patient)
    session.flush()

    for booking_date in (date(2026, 11, 2), date(2026, 11, 3)):
        session.add(
            Appointment(
                patient_id=patient.id,
                slot_id=slot.id,
                appointment_date=date(2026, 11, 10),
                booking_date=booking_date,
            )
        )

    with pytest.raises(IntegrityError):
        session.commit()


def test_doctor_schedule_is_one_interval_per_weekday(session: Session) -> None:
    doctor = Doctor(full_name="Dr. Test", specialty=None)
    session.add(doctor)
    session.flush()

    for weekday in (0, 0):
        session.add(
            DoctorSchedule(
                doctor_id=doctor.id,
                weekday=weekday,
                start_time=time(9, 0),
                end_time=time(12, 0),
            )
        )

    with pytest.raises(IntegrityError):
        session.commit()
