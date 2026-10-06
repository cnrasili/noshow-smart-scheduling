from datetime import timedelta

from sqlalchemy import delete, func, select

from noshow_db.models.core import (
    Appointment,
    Doctor,
    DoctorSchedule,
    Patient,
    Slot,
    UserAccount,
)
from web_backend.clinic import CLINIC_TZ, as_utc, today
from web_backend.seed import DEMO_PASSWORD, DOCTORS, PAST_DAYS, PATIENTS, seed


def _count(db, model) -> int:
    return db.scalar(select(func.count()).select_from(model))


def _login(client, email: str, role: str) -> int:
    return client.post(
        "/auth/login", json={"email": email, "password": DEMO_PASSWORD, "role": role}
    ).status_code


def test_seed_creates_a_usable_demo_clinic(db, client) -> None:
    seed(db)

    assert _count(db, Patient) == len(PATIENTS)
    assert _count(db, Doctor) == len(DOCTORS)
    assert _count(db, UserAccount) == len(PATIENTS) + len(DOCTORS)
    assert _count(db, Appointment) > 0
    for demo in DOCTORS:
        assert _login(client, demo.email, "doctor") == 200
    assert _login(client, PATIENTS[0][1], "patient") == 200


def test_every_doctor_gets_working_hours_slots_and_examples(db) -> None:
    seed(db)

    specialties = set(db.scalars(select(Doctor.specialty)))
    assert len(specialties) > 1
    for doctor_id in db.scalars(select(Doctor.id)):
        assert db.scalar(select(func.count()).where(DoctorSchedule.doctor_id == doctor_id)), (
            doctor_id
        )
        assert db.scalar(select(func.count()).where(Slot.doctor_id == doctor_id)), doctor_id
        assert db.scalar(
            select(func.count())
            .select_from(Appointment)
            .join(Slot, Slot.id == Appointment.slot_id)
            .where(Slot.doctor_id == doctor_id)
        ), doctor_id


def test_seed_slots_reach_back_three_weeks(db) -> None:
    seed(db)

    first = db.scalar(select(func.min(Slot.start_at)))
    first_day = as_utc(first).astimezone(CLINIC_TZ).date()
    # The first working day of the range may fall a few days after its start
    assert first_day <= today() - timedelta(days=PAST_DAYS - 3)


def test_seed_can_run_twice(db) -> None:
    seed(db)
    models = (Patient, Doctor, UserAccount, Slot, Appointment)
    counts = [_count(db, model) for model in models]

    seed(db)

    assert [_count(db, model) for model in models] == counts


def test_seed_adds_missing_doctors_to_an_earlier_demo(db) -> None:
    seed(db)
    # Remove the last doctor as if the database came from the single-doctor seed
    last = db.scalar(select(UserAccount).where(UserAccount.email == DOCTORS[-1].email))
    doctor_id = last.doctor_id
    db.execute(
        delete(Appointment).where(
            Appointment.slot_id.in_(select(Slot.id).where(Slot.doctor_id == doctor_id))
        )
    )
    db.execute(delete(Slot).where(Slot.doctor_id == doctor_id))
    db.execute(delete(DoctorSchedule).where(DoctorSchedule.doctor_id == doctor_id))
    db.delete(last)
    db.execute(delete(Doctor).where(Doctor.id == doctor_id))
    db.commit()

    seed(db)

    assert _count(db, Doctor) == len(DOCTORS)
    assert _count(db, Patient) == len(PATIENTS)
