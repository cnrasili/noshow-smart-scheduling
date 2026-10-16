from collections import Counter
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
from web_backend.national_id import FICTIONAL_PREFIX, is_valid_national_id
from web_backend.seed import (
    DEMO_PASSWORD,
    DOCTORS,
    PAST_DAYS,
    PATIENTS,
    patient_national_id,
    seed,
)


def _count(db, model) -> int:
    return db.scalar(select(func.count()).select_from(model))


def _doctor_login(client, email: str) -> int:
    return client.post(
        "/auth/login", json={"email": email, "password": DEMO_PASSWORD, "role": "doctor"}
    ).status_code


def _patient_login(client, national_id: str) -> int:
    return client.post(
        "/auth/login",
        json={"national_id": national_id, "password": DEMO_PASSWORD, "role": "patient"},
    ).status_code


def test_seed_creates_a_usable_demo_clinic(db, client) -> None:
    seed(db)

    assert _count(db, Patient) == len(PATIENTS)
    assert _count(db, Doctor) == len(DOCTORS)
    assert _count(db, UserAccount) == len(PATIENTS) + len(DOCTORS)
    assert _count(db, Appointment) > 0
    for demo in DOCTORS:
        assert _doctor_login(client, demo.email) == 200
    for number in range(1, len(PATIENTS) + 1):
        assert _patient_login(client, patient_national_id(number)) == 200


def test_seeded_national_ids_are_fictional_valid_and_unique(db) -> None:
    seed(db)

    numbers = list(db.scalars(select(Patient.national_id)))
    assert len(set(numbers)) == len(PATIENTS)
    assert all(is_valid_national_id(n) and n.startswith(FICTIONAL_PREFIX) for n in numbers)


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


def test_original_demo_doctors_and_patients_stay_the_same(db) -> None:
    seed(db)

    first_four = [
        ("Dr. Deniz Yıldız", "Dahiliye", "doktor@demo.local"),
        ("Dr. Can Özkan", "Dahiliye", "can.ozkan@demo.local"),
        ("Dr. Leyla Aksoy", "Kardiyoloji", "leyla.aksoy@demo.local"),
        ("Dr. Ebru Kaplan", "Göz Hastalıkları", "ebru.kaplan@demo.local"),
    ]
    assert [(d.name, d.specialty, d.email) for d in DOCTORS[:4]] == first_four
    assert [p[1] for p in PATIENTS] == [
        "ayse@demo.local",
        "mehmet@demo.local",
        "zeynep@demo.local",
        "ali@demo.local",
        "elif@demo.local",
        "burak@demo.local",
        "selin@demo.local",
        "hasan@demo.local",
    ]


def test_hospital_has_several_departments_with_two_or_three_doctors() -> None:
    per_department = Counter(demo.specialty for demo in DOCTORS)

    assert 8 <= len(per_department) <= 10
    assert set(per_department.values()) <= {2, 3}
    assert len({demo.email for demo in DOCTORS}) == len(DOCTORS)


def test_seed_adds_the_new_doctors_to_a_four_doctor_database(db, monkeypatch) -> None:
    from web_backend import seed as seed_module

    monkeypatch.setattr(seed_module, "DOCTORS", DOCTORS[:4])
    seed_module.seed(db)
    assert _count(db, Doctor) == 4
    monkeypatch.undo()

    seed_module.seed(db)

    assert _count(db, Doctor) == len(DOCTORS)
    assert _count(db, Patient) == len(PATIENTS)
