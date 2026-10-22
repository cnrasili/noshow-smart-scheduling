from datetime import UTC, date, datetime

import pytest

from noshow_db.models.core import Patient
from noshow_db.models.dataset import DatasetAppointment

DAY = date(2016, 6, 7)


@pytest.fixture
def records(db) -> None:
    first = Patient(
        patient_number="111", full_name="Hasta 111", email="111@x.example", age=9, gender="F"
    )
    second = Patient(
        patient_number="222", full_name="Hasta 222", email="222@x.example", age=63, gender="M"
    )
    db.add_all([first, second])
    db.flush()
    rows = [
        (1, second, DAY, True, 10),
        (2, first, DAY, False, 8),
        (3, first, date(2016, 6, 8), True, 9),
    ]
    db.add_all(
        DatasetAppointment(
            appointment_number=number,
            patient_id=patient.id,
            booked_at=datetime(2016, 5, 2, hour, tzinfo=UTC),
            appointment_date=day,
            attended=attended,
            sms_received=False,
        )
        for number, patient, day, attended, hour in rows
    )
    db.commit()


@pytest.fixture
def headers(make_department, login):
    make_department()
    return login("aile.hekimligi")


@pytest.mark.usefixtures("records")
def test_dataset_days_with_their_counts(client, headers) -> None:
    response = client.get("/department/dataset-days", headers=headers)

    assert response.json() == [
        {"date": "2016-06-07", "appointments": 2, "missed": 1},
        {"date": "2016-06-08", "appointments": 1, "missed": 0},
    ]


@pytest.mark.usefixtures("records")
def test_a_dataset_day_lists_its_records_by_booking_time(client, headers) -> None:
    response = client.get("/department/dataset-days/2016-06-07", headers=headers)

    assert response.json() == [
        {"patient_name": "Hasta 111", "patient_age": 9, "attended": False},
        {"patient_name": "Hasta 222", "patient_age": 63, "attended": True},
    ]
    assert client.get("/department/dataset-days/2026-10-19", headers=headers).json() == []


@pytest.mark.usefixtures("records")
def test_dataset_days_are_for_the_department_only(client, make_patient, login) -> None:
    make_patient()
    patient_headers = login("patient@example.com")

    assert client.get("/department/dataset-days", headers=patient_headers).status_code == 403
    assert client.get("/department/dataset-days/2016-06-07").status_code == 401
