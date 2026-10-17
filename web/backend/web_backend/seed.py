"""Prepare the demo: the department, its staff account and slots, and demo patient accounts.

Run with ``python -m web_backend.seed`` after the dataset is loaded (``python -m
noshow_db.load_dataset``, run by the migrate service). Nothing is invented: the patients and
their history come from the dataset, and the seed only opens login accounts for a few of them.
Running it again only adds what is missing. DEMO_PASSWORD is a demo value for local use only.
"""

from datetime import time, timedelta

from sqlalchemy import select
from sqlalchemy.orm import Session

from noshow_db.models.core import Doctor, Patient, UserAccount
from noshow_db.session import SessionLocal
from web_backend.accounts import WorkingHours, create_department, open_patient_account
from web_backend.clinic import today
from web_backend.slots import generate_slots

DEMO_PASSWORD = "demo1234"

# Login name of the department's staff account
DEPARTMENT_USERNAME = "aile.hekimligi"
# Monday to Friday, one session from 08:00 to 12:00
WORKING_HOURS = [
    WorkingHours(weekday=weekday, start_time=time(8), end_time=time(12)) for weekday in range(5)
]
# Slots are opened from today for this many days; the department can open more later
SLOT_DAYS = 28

# Dataset patients with different histories who get a demo login account
DEMO_PATIENTS = [
    ("1421986987763", "18 appointments, all missed"),
    ("26886125921145", "70 appointments, all attended"),
    ("93779.52927", "1 appointment"),
    ("1411446711177", "9 appointments, 3 missed"),
    ("11241475371456", "4 appointments, 1 missed"),
]


class DatasetNotLoadedError(Exception):
    """A demo patient is missing because the dataset has not been loaded."""


class EarlierDemoError(Exception):
    """The database still holds the doctors of an earlier demo with several departments."""


def _ensure_department(db: Session) -> int:
    """The department's id; the department and its staff account are created if missing."""
    account = db.scalar(select(UserAccount).where(UserAccount.email == DEPARTMENT_USERNAME))
    others = select(Doctor.id)
    if account is not None:
        others = others.where(Doctor.id != account.doctor_id)
    # The department must be the only record in doctors; the seed does not delete data
    if db.scalar(others.limit(1)) is not None:
        raise EarlierDemoError(
            "The database holds doctors of an earlier demo; recreate it "
            "(docker compose down -v, then docker compose up --build -d)"
        )
    if account is None:
        account = create_department(db, DEPARTMENT_USERNAME, DEMO_PASSWORD, WORKING_HOURS)
    return account.doctor_id


def _ensure_patient_accounts(db: Session) -> None:
    for number, _ in DEMO_PATIENTS:
        patient = db.scalar(select(Patient).where(Patient.patient_number == number))
        if patient is None:
            raise DatasetNotLoadedError(
                f"Dataset patient {number} not found; load the dataset first "
                "(python -m noshow_db.load_dataset)"
            )
        if db.scalar(select(UserAccount).where(UserAccount.patient_id == patient.id)) is None:
            open_patient_account(db, number, DEMO_PASSWORD)


def seed(db: Session) -> None:
    """Create the missing demo accounts and the department's slots for the coming weeks."""
    department_id = _ensure_department(db)
    _ensure_patient_accounts(db)
    generate_slots(db, department_id, today(), today() + timedelta(days=SLOT_DAYS - 1))
    db.commit()


def main() -> None:
    with SessionLocal() as db:
        seed(db)
    print("Demo data ready.")
    print(f"Department (Aile Hekimliği): username {DEPARTMENT_USERNAME}")
    print("Patients (dataset patient numbers): " + ", ".join(n for n, _ in DEMO_PATIENTS))
    print(f"Every demo account uses the password '{DEMO_PASSWORD}'.")


if __name__ == "__main__":
    main()
