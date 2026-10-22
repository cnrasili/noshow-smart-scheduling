from collections.abc import Iterator
from datetime import UTC, date, datetime
from pathlib import Path

import pytest
from sqlalchemy import create_engine, func, select
from sqlalchemy.orm import Session, sessionmaker
from sqlalchemy.pool import StaticPool

import noshow_db.models  # noqa: F401
from noshow_db.base import Base
from noshow_db.load_dataset import (
    DatasetRow,
    is_kept,
    latest_rows,
    load,
    patient_number,
    read_rows,
)
from noshow_db.models.core import Patient
from noshow_db.models.dataset import DatasetAppointment

DATASET = Path(__file__).resolve().parents[2] / "ml/data/raw/KaggleV2-May-2016.csv"

# Rows copied from the dataset:
# - a patient aged 55 at the earlier and 56 at the later appointment
# - a patient number in exponent form, booked on the appointment day
# - a patient with several health attributes
# - a patient with one kept row and one row whose appointment day is before the booking day
# - a patient whose only row has a negative age
SAMPLE = """\
PatientId,AppointmentID,Gender,ScheduledDay,AppointmentDay,Age,Neighbourhood,Scholarship,Hipertension,Diabetes,Alcoholism,Handcap,SMS_received,No-show
996868412638744,5635881,F,2016-04-28T14:14:16Z,2016-04-29T00:00:00Z,55,TABUAZEIRO,0,0,0,0,0,0,No
996868412638744,5616959,F,2016-04-25T15:06:32Z,2016-06-01T00:00:00Z,56,TABUAZEIRO,0,0,0,0,0,1,No
9377952927E-5,5712759,F,2016-05-18T09:12:29Z,2016-05-18T00:00:00Z,33,CENTRO,0,0,0,0,0,0,No
44873463981858,5675485,M,2016-05-09T13:47:04Z,2016-05-11T00:00:00Z,61,GURIGICA,1,1,0,1,1,0,No
24252258389979,5657354,F,2016-05-04T09:15:43Z,2016-05-19T00:00:00Z,22,CONSOLAÇÃO,0,0,0,0,0,0,Yes
24252258389979,5664962,F,2016-05-05T13:43:58Z,2016-05-04T00:00:00Z,22,CONSOLAÇÃO,0,0,0,0,0,0,Yes
465943158731293,5775010,F,2016-06-06T08:58:13Z,2016-06-06T00:00:00Z,-1,ROMÃO,0,0,0,0,0,0,No
"""


@pytest.fixture
def rows(tmp_path: Path) -> list[DatasetRow]:
    path = tmp_path / "dataset.csv"
    path.write_text(SAMPLE, encoding="utf-8")
    return read_rows(path)


@pytest.fixture
def session() -> Iterator[Session]:
    engine = create_engine("sqlite://", poolclass=StaticPool)
    Base.metadata.create_all(engine)
    with sessionmaker(bind=engine)() as db_session:
        yield db_session


def patient(session: Session, number: str) -> Patient:
    return session.scalars(select(Patient).where(Patient.patient_number == number)).one()


def history(session: Session, appointment_number: int) -> DatasetAppointment:
    return session.scalars(
        select(DatasetAppointment).where(
            DatasetAppointment.appointment_number == appointment_number
        )
    ).one()


def count(session: Session, model: type) -> int:
    return session.scalar(select(func.count()).select_from(model))


def test_patient_number_in_exponent_form_is_converted_exactly() -> None:
    assert patient_number("9377952927E-5") == "93779.52927"
    assert patient_number("996868412638744") == "996868412638744"


def test_rows_left_out_by_the_dataset_rules(rows: list[DatasetRow]) -> None:
    assert {row.appointment_number for row in rows if not is_kept(row)} == {5664962, 5775010}


def test_load_stores_every_kept_row(session: Session, rows: list[DatasetRow]) -> None:
    result = load(session, rows)

    assert (result.rows, result.left_out) == (7, 2)
    assert (result.new_patients, result.new_appointments) == (4, 5)
    assert set(session.scalars(select(Patient.patient_number))) == {
        "996868412638744",
        "93779.52927",
        "44873463981858",
        "24252258389979",
    }
    assert set(session.scalars(select(DatasetAppointment.appointment_number))) == {
        5635881,
        5616959,
        5712759,
        5675485,
        5657354,
    }


def test_name_and_email_come_only_from_the_number(session: Session, rows: list[DatasetRow]) -> None:
    load(session, rows)

    stored = patient(session, "93779.52927")
    assert stored.full_name == "Hasta 93779.52927"
    assert stored.email == "93779.52927@hasta.sehirhastanesi.example"
    assert "national_id" not in Patient.__table__.c


def test_patient_has_the_attributes_of_the_dataset(
    session: Session, rows: list[DatasetRow]
) -> None:
    load(session, rows)

    stored = patient(session, "44873463981858")
    assert (stored.age, stored.gender, stored.handcap) == (61, "M", 1)
    assert (stored.scholarship, stored.hipertension, stored.diabetes, stored.alcoholism) == (
        True,
        True,
        False,
        True,
    )


def test_patient_age_is_the_age_at_the_latest_appointment(
    session: Session, rows: list[DatasetRow]
) -> None:
    load(session, rows)

    assert patient(session, "996868412638744").age == 56


def test_history_keeps_the_dataset_values(session: Session, rows: list[DatasetRow]) -> None:
    load(session, rows)

    later = history(session, 5616959)
    assert session.get(Patient, later.patient_id).patient_number == "996868412638744"
    # SQLite returns the stored UTC time without its time zone
    assert later.booked_at.replace(tzinfo=UTC) == datetime(2016, 4, 25, 15, 6, 32, tzinfo=UTC)
    assert later.appointment_date == date(2016, 6, 1)
    assert (later.attended, later.sms_received) == (True, True)
    assert history(session, 5657354).attended is False


def test_loading_twice_changes_nothing(session: Session, rows: list[DatasetRow]) -> None:
    load(session, rows)
    session.commit()

    again = load(session, rows)

    assert (again.new_patients, again.new_appointments) == (0, 0)
    assert (count(session, Patient), count(session, DatasetAppointment)) == (4, 5)


def test_dataset_file_has_the_agreed_counts() -> None:
    rows = read_rows(DATASET)
    kept = [row for row in rows if is_kept(row)]

    assert (len(rows), len(kept)) == (110_527, 110_521)
    assert len(latest_rows(kept)) == 62_298
    assert len({row.appointment_number for row in kept}) == len(kept)
