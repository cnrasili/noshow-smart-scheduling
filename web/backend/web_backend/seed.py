"""Fill the database with a fictional demo clinic.

Run with ``python -m web_backend.seed``. Running it again only adds missing slots.
All people are made up; DEMO_PASSWORD is a demo value for local use only.
"""

from datetime import time, timedelta

from sqlalchemy import select
from sqlalchemy.orm import Session

from noshow_db.models.core import Appointment, Doctor, DoctorSchedule, Patient, Slot, UserAccount
from noshow_db.session import SessionLocal
from web_backend.clinic import CLINIC_TZ, as_utc, today
from web_backend.security import hash_password
from web_backend.slots import generate_slots

DEMO_PASSWORD = "demo1234"
DOCTOR_EMAIL = "doktor@demo.local"

# name, email, age, gender, scholarship, hipertension, diabetes, alcoholism, handcap
PATIENTS = [
    ("Ayşe Kaya", "ayse@demo.local", 34, "F", False, False, False, False, 0),
    ("Mehmet Demir", "mehmet@demo.local", 58, "M", False, True, True, False, 0),
    ("Zeynep Çelik", "zeynep@demo.local", 22, "F", True, False, False, False, 0),
    ("Ali Şahin", "ali@demo.local", 45, "M", False, True, False, True, 0),
    ("Elif Arslan", "elif@demo.local", 67, "F", False, True, True, False, 1),
    ("Burak Koç", "burak@demo.local", 29, "M", True, False, False, False, 0),
    ("Selin Aydın", "selin@demo.local", 8, "F", False, False, False, False, 0),
    ("Hasan Öztürk", "hasan@demo.local", 73, "M", False, True, False, False, 2),
]

PAST_DAYS = 7
FUTURE_DAYS = 14


def _create_people(db: Session) -> Doctor:
    password_hash = hash_password(DEMO_PASSWORD)
    doctor = Doctor(full_name="Dr. Deniz Yıldız", specialty="Dahiliye")
    db.add(doctor)
    db.flush()
    db.add(
        UserAccount(
            email=DOCTOR_EMAIL, password_hash=password_hash, role="doctor", doctor_id=doctor.id
        )
    )
    for weekday in range(5):
        db.add(
            DoctorSchedule(
                doctor_id=doctor.id, weekday=weekday, start_time=time(9, 0), end_time=time(12, 0)
            )
        )

    for (
        name,
        email,
        age,
        gender,
        scholarship,
        hipertension,
        diabetes,
        alcoholism,
        handcap,
    ) in PATIENTS:
        patient = Patient(
            full_name=name,
            email=email,
            age=age,
            gender=gender,
            scholarship=scholarship,
            hipertension=hipertension,
            diabetes=diabetes,
            alcoholism=alcoholism,
            handcap=handcap,
        )
        db.add(patient)
        db.flush()
        db.add(
            UserAccount(
                email=email, password_hash=password_hash, role="patient", patient_id=patient.id
            )
        )
    db.flush()
    return doctor


def _book_examples(db: Session, doctor: Doctor) -> None:
    """Past bookings for attendance marking and a few upcoming ones."""
    patients = db.scalars(select(Patient).order_by(Patient.id)).all()
    slots = db.scalars(select(Slot).where(Slot.doctor_id == doctor.id).order_by(Slot.start_at))
    past_slots, future_slots = [], []
    for slot in slots:
        day = as_utc(slot.start_at).astimezone(CLINIC_TZ).date()
        (past_slots if day < today() else future_slots).append((slot, day))

    # Every other slot of the most recent past working day, then the first slots ahead
    last_past_day = max((day for _, day in past_slots), default=None)
    examples = [entry for entry in past_slots if entry[1] == last_past_day][::2]
    examples += [entry for entry in future_slots if entry[1] > today()][:3:2]
    for (slot, day), patient in zip(examples, patients, strict=False):
        db.add(
            Appointment(
                patient_id=patient.id,
                slot_id=slot.id,
                appointment_date=day,
                booking_date=min(day - timedelta(days=5), today()),
            )
        )


def seed(db: Session) -> None:
    account = db.scalar(select(UserAccount).where(UserAccount.email == DOCTOR_EMAIL))
    first_run = account is None
    doctor = _create_people(db) if first_run else db.get(Doctor, account.doctor_id)

    generate_slots(
        db, doctor.id, today() - timedelta(days=PAST_DAYS), today() + timedelta(days=FUTURE_DAYS)
    )
    db.flush()
    if first_run:
        _book_examples(db, doctor)
    db.commit()


def main() -> None:
    with SessionLocal() as db:
        seed(db)
    print(f"Demo data ready. Doctor: {DOCTOR_EMAIL}; patients: {PATIENTS[0][1]} and others.")
    print(f"Every demo account uses the password '{DEMO_PASSWORD}'.")


if __name__ == "__main__":
    main()
