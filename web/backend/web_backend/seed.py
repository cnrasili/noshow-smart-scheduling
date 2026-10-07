"""Fill the database with a fictional demo clinic.

Run with ``python -m web_backend.seed``. Running it again only adds missing doctors,
patients and slots, so it also upgrades a database seeded by an earlier version.
All people are made up, including their national ID numbers (see web_backend.national_id);
DEMO_PASSWORD is a demo value for local use only.
"""

from dataclasses import dataclass
from datetime import time, timedelta

from sqlalchemy import select
from sqlalchemy.orm import Session

from noshow_db.models.core import Appointment, Doctor, Patient, Slot, UserAccount
from noshow_db.session import SessionLocal
from web_backend.accounts import NewDoctor, NewPatient, WorkingHours, create_doctor, create_patient
from web_backend.clinic import CLINIC_TZ, as_utc, today
from web_backend.national_id import fictional_national_id
from web_backend.slots import generate_slots

DEMO_PASSWORD = "demo1234"


@dataclass(frozen=True)
class DemoDoctor:
    name: str
    specialty: str
    email: str
    # Working days (0 = Monday) and their hours
    weekdays: tuple[int, ...]
    start: time
    end: time


# Several doctors and branches so the branch and doctor choice is meaningful in the demo
DOCTORS = [
    DemoDoctor(
        "Dr. Deniz Yıldız", "Dahiliye", "doktor@demo.local", (0, 1, 2, 3, 4), time(9), time(12)
    ),
    DemoDoctor("Dr. Can Özkan", "Dahiliye", "can.ozkan@demo.local", (0, 2, 4), time(13), time(16)),
    DemoDoctor(
        "Dr. Leyla Aksoy", "Kardiyoloji", "leyla.aksoy@demo.local", (1, 3), time(9), time(12)
    ),
    DemoDoctor(
        "Dr. Ebru Kaplan",
        "Göz Hastalıkları",
        "ebru.kaplan@demo.local",
        (0, 1, 3),
        time(13),
        time(15),
    ),
]
DOCTOR_EMAIL = DOCTORS[0].email

# name, email, age, gender, scholarship, hipertension, diabetes, alcoholism, handcap.
# The n-th patient (from 1) gets the fictional national ID number patient_national_id(n).
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

# Three past weeks give the overbooking service demo enough history for KPIs and A/B
PAST_DAYS = 21
FUTURE_DAYS = 14


def patient_national_id(number: int) -> str:
    """Fictional national ID number of the n-th demo patient, counting from 1."""
    return fictional_national_id(number)


def _account(db: Session, email: str) -> UserAccount | None:
    return db.scalar(select(UserAccount).where(UserAccount.email == email))


def _ensure_patients(db: Session) -> None:
    for number, (
        name,
        email,
        age,
        gender,
        scholarship,
        hipertension,
        diabetes,
        alcoholism,
        handcap,
    ) in enumerate(PATIENTS, start=1):
        if _account(db, email) is not None:
            continue
        create_patient(
            db,
            NewPatient(
                national_id=patient_national_id(number),
                full_name=name,
                email=email,
                age=age,
                gender=gender,
                scholarship=scholarship,
                hipertension=hipertension,
                diabetes=diabetes,
                alcoholism=alcoholism,
                handcap=handcap,
                password=DEMO_PASSWORD,
            ),
        )


def _ensure_doctor(db: Session, demo: DemoDoctor) -> tuple[Doctor, bool]:
    """The demo doctor with account and working hours; True if it was just created."""
    account = _account(db, demo.email)
    if account is None:
        account = create_doctor(
            db,
            NewDoctor(
                full_name=demo.name,
                specialty=demo.specialty,
                email=demo.email,
                password=DEMO_PASSWORD,
                working_hours=[
                    WorkingHours(weekday=weekday, start_time=demo.start, end_time=demo.end)
                    for weekday in demo.weekdays
                ],
            ),
        )
        return db.get(Doctor, account.doctor_id), True
    return db.get(Doctor, account.doctor_id), False


def _book_examples(db: Session, doctor: Doctor, first_patient: int) -> None:
    """Past bookings for attendance marking and a few upcoming ones.

    Patients are taken in turn from first_patient, so doctors start with different patients.
    """
    patients = db.scalars(select(Patient).order_by(Patient.id)).all()
    patients = patients[first_patient:] + patients[:first_patient]
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
    """Create the missing demo accounts through the account module, then slots and bookings."""
    _ensure_patients(db)
    for index, demo in enumerate(DOCTORS):
        doctor, created = _ensure_doctor(db, demo)
        generate_slots(
            db,
            doctor.id,
            today() - timedelta(days=PAST_DAYS),
            today() + timedelta(days=FUTURE_DAYS),
        )
        db.flush()
        if created:
            _book_examples(db, doctor, first_patient=(index * 3) % len(PATIENTS))
    db.commit()


def main() -> None:
    with SessionLocal() as db:
        seed(db)
    print("Demo data ready.")
    print("Doctors: " + ", ".join(f"{d.email} ({d.specialty})" for d in DOCTORS))
    print(
        "Patients (fictional national ID numbers): "
        + ", ".join(patient_national_id(n) for n in range(1, len(PATIENTS) + 1))
    )
    print(f"Every demo account uses the password '{DEMO_PASSWORD}'.")


if __name__ == "__main__":
    main()
