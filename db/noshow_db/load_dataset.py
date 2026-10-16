"""Load the public no-show dataset into the database.

Usage: python -m noshow_db.load_dataset [--csv ml/data/raw/KaggleV2-May-2016.csv]

Every patient is stored once with the attributes of their latest appointment, and every
appointment goes to the history table. Rows the dataset rules leave out are skipped: an
appointment day before the booking day, or a negative age. Records already in the database
are left as they are, so loading again changes nothing.
"""

import argparse
import csv
from collections.abc import Iterable, Sequence
from dataclasses import dataclass
from datetime import date, datetime
from decimal import Decimal
from pathlib import Path

from sqlalchemy import insert, select
from sqlalchemy.orm import Session

from noshow_db.models.core import Patient
from noshow_db.models.dataset import DatasetAppointment
from noshow_db.session import SessionLocal

DEFAULT_CSV = Path("ml/data/raw/KaggleV2-May-2016.csv")
# Technical addresses derived from the patient number; they only reach the local mail catcher
EMAIL_DOMAIN = "hasta.sehirhastanesi.example"


@dataclass(frozen=True, slots=True)
class DatasetRow:
    """One appointment of the dataset."""

    patient_number: str
    appointment_number: int
    gender: str
    booked_at: datetime
    appointment_date: date
    age: int
    scholarship: bool
    hipertension: bool
    diabetes: bool
    alcoholism: bool
    handcap: int
    sms_received: bool
    attended: bool


@dataclass(frozen=True)
class LoadResult:
    rows: int
    left_out: int
    new_patients: int
    new_appointments: int


def patient_number(value: str) -> str:
    """PatientId in plain notation; the few written in exponent form are converted exactly."""
    return format(Decimal(value), "f")


def _choice(value: str, allowed: tuple[str, ...]) -> str:
    if value not in allowed:
        raise ValueError(f"Expected one of {allowed}, got {value!r}")
    return value


def _flag(value: str) -> bool:
    return _choice(value, ("0", "1")) == "1"


def parse_row(raw: dict[str, str]) -> DatasetRow:
    return DatasetRow(
        patient_number=patient_number(raw["PatientId"]),
        appointment_number=int(raw["AppointmentID"]),
        gender=_choice(raw["Gender"], ("F", "M")),
        booked_at=datetime.fromisoformat(raw["ScheduledDay"]),
        # AppointmentDay always has the time 00:00:00
        appointment_date=datetime.fromisoformat(raw["AppointmentDay"]).date(),
        age=int(raw["Age"]),
        scholarship=_flag(raw["Scholarship"]),
        hipertension=_flag(raw["Hipertension"]),
        diabetes=_flag(raw["Diabetes"]),
        alcoholism=_flag(raw["Alcoholism"]),
        handcap=int(raw["Handcap"]),
        sms_received=_flag(raw["SMS_received"]),
        # "No-show" is "Yes" when the patient missed the appointment
        attended=_choice(raw["No-show"], ("Yes", "No")) == "No",
    )


def read_rows(path: Path) -> list[DatasetRow]:
    with path.open(newline="", encoding="utf-8") as file:
        return [parse_row(raw) for raw in csv.DictReader(file)]


def is_kept(row: DatasetRow) -> bool:
    """False for the rows the dataset rules leave out."""
    return row.appointment_date >= row.booked_at.date() and row.age >= 0


def latest_rows(rows: Iterable[DatasetRow]) -> dict[str, DatasetRow]:
    """Each patient's latest appointment, which gives the attributes of the patient record."""
    latest: dict[str, DatasetRow] = {}
    for row in rows:
        current = latest.get(row.patient_number)
        if current is None or _order(row) > _order(current):
            latest[row.patient_number] = row
    return latest


def _order(row: DatasetRow) -> tuple[date, datetime, int]:
    return row.appointment_date, row.booked_at, row.appointment_number


def patient_values(row: DatasetRow) -> dict[str, object]:
    return {
        "patient_number": row.patient_number,
        "full_name": f"Hasta {row.patient_number}",
        "email": f"{row.patient_number}@{EMAIL_DOMAIN}",
        "age": row.age,
        "gender": row.gender,
        "scholarship": row.scholarship,
        "hipertension": row.hipertension,
        "diabetes": row.diabetes,
        "alcoholism": row.alcoholism,
        "handcap": row.handcap,
    }


def appointment_values(row: DatasetRow, patient_id: int) -> dict[str, object]:
    return {
        "appointment_number": row.appointment_number,
        "patient_id": patient_id,
        "booked_at": row.booked_at,
        "appointment_date": row.appointment_date,
        "attended": row.attended,
        "sms_received": row.sms_received,
    }


def load(session: Session, rows: Sequence[DatasetRow]) -> LoadResult:
    """Add the dataset patients and appointments that are not in the database yet."""
    kept = [row for row in rows if is_kept(row)]
    dataset_patients = select(Patient.patient_number, Patient.id).where(
        Patient.patient_number.is_not(None)
    )

    stored_patients = {number for number, _ in session.execute(dataset_patients)}
    new_patients = [
        patient_values(row)
        for number, row in latest_rows(kept).items()
        if number not in stored_patients
    ]
    if new_patients:
        session.execute(insert(Patient), new_patients)

    patient_ids = {number: patient_id for number, patient_id in session.execute(dataset_patients)}
    stored_appointments = set(session.scalars(select(DatasetAppointment.appointment_number)))
    new_appointments = [
        appointment_values(row, patient_ids[row.patient_number])
        for row in kept
        if row.appointment_number not in stored_appointments
    ]
    if new_appointments:
        session.execute(insert(DatasetAppointment), new_appointments)

    return LoadResult(len(rows), len(rows) - len(kept), len(new_patients), len(new_appointments))


def main(argv: list[str] | None = None) -> None:
    parser = argparse.ArgumentParser(description="Load the public no-show dataset.")
    parser.add_argument("--csv", type=Path, default=DEFAULT_CSV, help="dataset CSV file")
    args = parser.parse_args(argv)

    rows = read_rows(args.csv)
    with SessionLocal() as session:
        result = load(session, rows)
        session.commit()
    print(
        f"Dataset: {result.rows} rows, {result.left_out} left out by the dataset rules; "
        f"added {result.new_patients} patients and {result.new_appointments} appointments."
    )


if __name__ == "__main__":
    main()
