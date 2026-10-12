from collections.abc import Iterator
from datetime import UTC, date, datetime, time
from itertools import count

import pytest
from sqlalchemy import create_engine, func, inspect, select, text
from sqlalchemy.exc import IntegrityError
from sqlalchemy.orm import Session, sessionmaker
from sqlalchemy.pool import StaticPool

import noshow_db.models  # noqa: F401
from noshow_db.base import Base
from noshow_db.models.core import (
    Appointment,
    Doctor,
    DoctorSchedule,
    Patient,
    Slot,
    UserAccount,
)
from web_backend.national_id import fictional_national_id


@pytest.fixture
def session() -> Iterator[Session]:
    engine = create_engine(
        "sqlite://", connect_args={"check_same_thread": False}, poolclass=StaticPool
    )
    Base.metadata.create_all(engine)
    with sessionmaker(bind=engine)() as db_session:
        yield db_session


_numbers = count(1)


def _patient(email: str = "patient@example.com", age: int = 30) -> Patient:
    return Patient(
        national_id=fictional_national_id(next(_numbers)),
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
    assert {
        "patients",
        "doctors",
        "doctor_schedules",
        "slots",
        "appointments",
        "user_accounts",
        "auth_sessions",
    } <= tables


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


def test_defaults_apply_to_raw_sql_inserts(session: Session) -> None:
    session.execute(
        text(
            "INSERT INTO patients (national_id, full_name, email, age, gender) "
            "VALUES ('99999000184', 'Raw Patient', 'raw@example.com', 40, 'M')"
        )
    )
    session.execute(text("INSERT INTO doctors (full_name) VALUES ('Dr. Raw')"))
    session.execute(
        text(
            "INSERT INTO slots (doctor_id, start_at, end_at) "
            "VALUES (1, '2026-11-10 09:00:00', '2026-11-10 09:30:00')"
        )
    )
    session.commit()

    patient = session.scalars(select(Patient)).one()
    assert patient.scholarship is False
    assert patient.hipertension is False
    assert patient.diabetes is False
    assert patient.alcoholism is False
    assert patient.handcap == 0
    assert session.scalars(select(Slot)).one().max_patients == 2


def test_patient_age_cannot_be_negative(session: Session) -> None:
    session.add(_patient(age=-1))

    with pytest.raises(IntegrityError):
        session.commit()


def test_booking_date_cannot_be_after_appointment_date(session: Session) -> None:
    slot = _slot(session)
    patient = _patient()
    session.add(patient)
    session.flush()
    session.add(
        Appointment(
            patient_id=patient.id,
            slot_id=slot.id,
            appointment_date=date(2026, 11, 10),
            booking_date=date(2026, 11, 11),
        )
    )

    with pytest.raises(IntegrityError):
        session.commit()


@pytest.mark.parametrize("max_patients", [0, -1])
def test_slot_capacity_must_be_positive(session: Session, max_patients: int) -> None:
    session.add(Doctor(full_name="Dr. Test", specialty=None))
    session.flush()
    session.add(
        Slot(
            doctor_id=1,
            start_at=datetime(2026, 11, 10, 9, 0, tzinfo=UTC),
            end_at=datetime(2026, 11, 10, 9, 30, tzinfo=UTC),
            max_patients=max_patients,
        )
    )

    with pytest.raises(IntegrityError):
        session.commit()


def test_slot_must_end_after_it_starts(session: Session) -> None:
    session.add(Doctor(full_name="Dr. Test", specialty=None))
    session.flush()
    start = datetime(2026, 11, 10, 9, 0, tzinfo=UTC)
    session.add(Slot(doctor_id=1, start_at=start, end_at=start))

    with pytest.raises(IntegrityError):
        session.commit()


def _owners(session: Session) -> tuple[int, int]:
    patient = _patient()
    doctor = Doctor(full_name="Dr. Test", specialty=None)
    session.add_all([patient, doctor])
    session.flush()
    return patient.id, doctor.id


def test_accounts_link_to_a_patient_or_a_doctor(session: Session) -> None:
    patient_id, doctor_id = _owners(session)
    session.add_all(
        [
            UserAccount(
                email="patient@example.com",
                password_hash="x",
                role="patient",
                patient_id=patient_id,
            ),
            UserAccount(
                email="doctor@example.com", password_hash="x", role="doctor", doctor_id=doctor_id
            ),
        ]
    )
    session.commit()

    assert session.scalar(select(func.count()).select_from(UserAccount)) == 2


@pytest.mark.parametrize(
    ("role", "link_patient", "link_doctor"),
    [
        ("patient", False, False),
        ("patient", False, True),
        ("doctor", True, False),
        ("patient", True, True),
        ("admin", True, False),
    ],
)
def test_account_role_must_match_its_owner(
    session: Session, role: str, link_patient: bool, link_doctor: bool
) -> None:
    patient_id, doctor_id = _owners(session)
    session.add(
        UserAccount(
            email="user@example.com",
            password_hash="x",
            role=role,
            patient_id=patient_id if link_patient else None,
            doctor_id=doctor_id if link_doctor else None,
        )
    )

    with pytest.raises(IntegrityError):
        session.commit()


def test_a_patient_has_at_most_one_account(session: Session) -> None:
    patient_id, _ = _owners(session)
    for email in ("first@example.com", "second@example.com"):
        session.add(
            UserAccount(email=email, password_hash="x", role="patient", patient_id=patient_id)
        )

    with pytest.raises(IntegrityError):
        session.commit()
