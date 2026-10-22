from datetime import timedelta
from pathlib import Path

import pytest
from sqlalchemy import case, func, select

from noshow_db.load_dataset import DatasetRow, load, read_rows
from noshow_db.models.core import (
    Appointment,
    Doctor,
    DoctorSchedule,
    Patient,
    Slot,
    UserAccount,
)
from noshow_db.models.dataset import DatasetAppointment
from web_backend.clinic import CLINIC_TZ, as_utc, today
from web_backend.seed import (
    DEMO_PASSWORD,
    DEMO_PATIENTS,
    DEPARTMENT_USERNAME,
    SLOT_DAYS,
    DatasetNotLoadedError,
    EarlierDemoError,
    seed,
)

DATASET = Path(__file__).resolve().parents[3] / "ml/data/raw/KaggleV2-May-2016.csv"
DEMO_NUMBERS = [number for number, _ in DEMO_PATIENTS]


@pytest.fixture(scope="module")
def demo_rows() -> list[DatasetRow]:
    """The dataset rows of the demo patients and of one patient without a demo account."""
    rows = read_rows(DATASET)
    others = sorted({row.patient_number for row in rows} - set(DEMO_NUMBERS))[:1]
    return [row for row in rows if row.patient_number in {*DEMO_NUMBERS, *others}]


@pytest.fixture
def dataset(db, demo_rows) -> None:
    load(db, demo_rows)
    db.commit()


def _count(db, model) -> int:
    return db.scalar(select(func.count()).select_from(model))


def _history(db, number: str) -> tuple[int, int]:
    """Appointments and missed appointments of a dataset patient."""
    total, missed = db.execute(
        select(func.count(), func.sum(case((DatasetAppointment.attended.is_(False), 1), else_=0)))
        .join(Patient, Patient.id == DatasetAppointment.patient_id)
        .where(Patient.patient_number == number)
    ).one()
    return total, missed or 0


def _patient_login(client, number: str) -> int:
    return client.post(
        "/auth/login",
        json={"role": "patient", "patient_number": number, "password": DEMO_PASSWORD},
    ).status_code


def _department_login(client, username: str) -> int:
    return client.post(
        "/auth/login",
        json={"role": "department", "username": username, "password": DEMO_PASSWORD},
    ).status_code


def test_seed_opens_the_demo_accounts(db, client, dataset) -> None:
    seed(db)

    for number in DEMO_NUMBERS:
        assert _patient_login(client, number) == 200, number
    assert _department_login(client, DEPARTMENT_USERNAME) == 200


def test_seed_invents_no_patients_or_bookings(db, dataset) -> None:
    patients = _count(db, Patient)

    seed(db)

    assert _count(db, Patient) == patients
    assert _count(db, Appointment) == 0
    # Only the demo patients get an account, besides the department
    assert _count(db, UserAccount) == len(DEMO_PATIENTS) + 1


def test_demo_patients_have_the_listed_histories(db, dataset) -> None:
    histories = {
        "1421986987763": (18, 18),
        "26886125921145": (70, 0),
        "93779.52927": (1, 0),
        "1411446711177": (9, 3),
        "11241475371456": (4, 1),
    }
    assert list(histories) == DEMO_NUMBERS
    for number, history in histories.items():
        assert _history(db, number) == history, number


def test_seed_creates_one_department_without_a_doctor(db, dataset) -> None:
    seed(db)

    department = db.scalars(select(Doctor)).one()
    assert department.full_name == "General Practice"
    hours = db.scalars(select(DoctorSchedule).order_by(DoctorSchedule.weekday)).all()
    assert [h.weekday for h in hours] == [0, 1, 2, 3, 4]
    assert {(h.start_time.hour, h.end_time.hour) for h in hours} == {(8, 12)}


def test_seed_opens_sixteen_quarter_hour_slots_per_working_day(db, dataset) -> None:
    seed(db)

    slots = db.scalars(select(Slot).order_by(Slot.start_at)).all()
    by_day: dict = {}
    for slot in slots:
        start = as_utc(slot.start_at).astimezone(CLINIC_TZ)
        assert as_utc(slot.end_at) - as_utc(slot.start_at) == timedelta(minutes=15)
        by_day.setdefault(start.date(), []).append(start.strftime("%H:%M"))
    assert all(day.weekday() < 5 for day in by_day)
    assert {len(times) for times in by_day.values()} == {16}
    assert {times[0] for times in by_day.values()} == {"08:00"}
    assert {times[-1] for times in by_day.values()} == {"11:45"}
    assert min(by_day) >= today()
    assert max(by_day) < today() + timedelta(days=SLOT_DAYS)


def test_seed_can_run_twice(db, dataset) -> None:
    seed(db)
    models = (Patient, Doctor, UserAccount, Slot, DoctorSchedule)
    counts = [_count(db, model) for model in models]

    seed(db)

    assert [_count(db, model) for model in models] == counts


def test_seed_needs_the_dataset(db) -> None:
    with pytest.raises(DatasetNotLoadedError):
        seed(db)


def test_seed_refuses_a_database_with_doctors_of_the_earlier_demo(db, dataset) -> None:
    db.add(Doctor(full_name="Dr. Earlier Demo", specialty="Dahiliye"))
    db.commit()

    with pytest.raises(EarlierDemoError):
        seed(db)

    assert _count(db, UserAccount) == 0
