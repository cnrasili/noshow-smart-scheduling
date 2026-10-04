from collections.abc import Iterator
from datetime import UTC, date, datetime
from zoneinfo import ZoneInfo

import pytest
from fastapi.testclient import TestClient
from sqlalchemy import create_engine
from sqlalchemy.orm import Session, sessionmaker

from noshow_db.models.core import Appointment, Doctor, Patient, Slot
from overbooking_service.data_source import (
    DataSourceUnavailable,
    DbPatientSource,
    DbSlotSource,
    SlotBooking,
)
from overbooking_service.dependencies import get_data_source
from overbooking_service.main import app

CLINIC = ZoneInfo("Europe/Istanbul")


def utc(day: int, hour: int, minute: int = 0) -> datetime:
    return datetime(2026, 11, day, hour, minute, tzinfo=UTC)


def patient(patient_id: int, **fields) -> Patient:
    values = {"full_name": f"Patient {patient_id}", "age": 40, "gender": "F"} | fields
    return Patient(id=patient_id, email=f"p{patient_id}@example.com", **values)


def appointment(patient_id: int, slot_id: int, day: int, **fields) -> Appointment:
    return Appointment(
        patient_id=patient_id,
        slot_id=slot_id,
        appointment_date=date(2026, 11, day),
        booking_date=fields.pop("booking_date", date(2026, 11, 1)),
        **fields,
    )


@pytest.fixture
def db(session_factory: sessionmaker[Session]) -> Iterator[Session]:
    with session_factory() as session:
        session.add_all(
            [
                patient(1, age=67, gender="M", hipertension=True, handcap=1),
                patient(2),
                patient(3),
                patient(4),
                Doctor(id=1, full_name="Doctor 1"),
                Doctor(id=2, full_name="Doctor 2"),
                # 21:30 UTC on Nov 9 is 00:30 on Nov 10 in the clinic
                Slot(
                    id=10,
                    doctor_id=1,
                    start_at=utc(9, 21, 30),
                    end_at=utc(9, 21, 50),
                    max_patients=3,
                ),
                Slot(id=11, doctor_id=1, start_at=utc(10, 7), end_at=utc(10, 7, 20)),
                Slot(id=12, doctor_id=1, start_at=utc(10, 8), end_at=utc(10, 8, 20)),
                # 21:30 UTC on Nov 10 is already Nov 11 in the clinic
                Slot(id=13, doctor_id=1, start_at=utc(10, 21, 30), end_at=utc(10, 21, 50)),
                Slot(id=14, doctor_id=2, start_at=utc(10, 7), end_at=utc(10, 7, 20)),
                Slot(id=20, doctor_id=1, start_at=utc(3, 7), end_at=utc(3, 7, 20)),
            ]
        )
        session.flush()
        session.add_all(
            [
                # Patient 1 history: attended, missed, no outcome yet
                appointment(1, 20, 3, attended=True),
                appointment(1, 11, 10, attended=False),
                appointment(1, 12, 10),
                # Doctor 1 on Nov 10: slot 10 overbooked twice, slot 11 once
                appointment(2, 10, 10),
                appointment(3, 10, 10, booking_date=date(2026, 11, 4)),
                appointment(4, 10, 10),
                appointment(2, 11, 10),
                appointment(2, 13, 11),
                appointment(3, 13, 11),
                appointment(2, 14, 10),
                appointment(3, 14, 10),
            ]
        )
        session.commit()
        yield session


def test_patient_record_is_read(db: Session):
    record = DbPatientSource(db).get_patient(1)
    assert record is not None
    assert (record.patient_id, record.age, record.gender) == (1, 67, "M")
    assert record.hipertension and not record.diabetes
    assert record.handcap == 1


def test_unknown_patient_is_none(db: Session):
    assert DbPatientSource(db).get_patient(99) is None


def test_history_has_only_recorded_outcomes(db: Session):
    history = DbPatientSource(db).get_history(1)
    assert [(h.appointment_date, h.attended) for h in history] == [
        (date(2026, 11, 3), True),
        (date(2026, 11, 10), False),
    ]


def test_slot_state_is_read(db: Session):
    slot = DbSlotSource(db, CLINIC).get_slot(10)
    assert slot is not None
    assert (slot.slot_id, slot.doctor_id, slot.max_patients) == (10, 1, 3)
    assert slot.bookings == (
        SlotBooking(2, date(2026, 11, 1)),
        SlotBooking(3, date(2026, 11, 4)),
        SlotBooking(4, date(2026, 11, 1)),
    )


def test_slot_date_uses_clinic_timezone(db: Session):
    source = DbSlotSource(db, CLINIC)
    assert source.get_slot(10).slot_date == date(2026, 11, 10)
    assert source.get_slot(13).slot_date == date(2026, 11, 11)


def test_unknown_slot_is_none(db: Session):
    assert DbSlotSource(db, CLINIC).get_slot(99) is None


def test_overbooks_are_counted_per_doctor_and_clinic_day(db: Session):
    source = DbSlotSource(db, CLINIC)
    assert source.count_overbooks(1, date(2026, 11, 10)) == 3
    assert source.count_overbooks(1, date(2026, 11, 11)) == 1
    assert source.count_overbooks(2, date(2026, 11, 10)) == 1
    assert source.count_overbooks(1, date(2026, 11, 12)) == 0


def test_missing_tables_raise_unavailable():
    with sessionmaker(bind=create_engine("sqlite://"))() as session:
        with pytest.raises(DataSourceUnavailable):
            DbPatientSource(session).get_patient(1)
        with pytest.raises(DataSourceUnavailable):
            DbPatientSource(session).get_history(1)
        with pytest.raises(DataSourceUnavailable):
            DbSlotSource(session, CLINIC).get_slot(1)
        with pytest.raises(DataSourceUnavailable):
            DbSlotSource(session, CLINIC).count_overbooks(1, date(2026, 11, 10))


def test_predict_reads_patient_from_database(client: TestClient, db: Session):
    del app.dependency_overrides[get_data_source]
    body = {"patient_id": 1, "appointment_date": "2026-11-20", "booking_date": "2026-11-12"}
    response = client.post("/predict", json=body)
    assert response.status_code == 200
    assert 0 <= response.json()["p_noshow"] <= 1


def test_booking_decision_reads_slot_from_database(client: TestClient, db: Session):
    del app.dependency_overrides[get_data_source]
    body = {"patient_id": 1, "slot_id": 10, "booking_date": "2026-11-05"}
    response = client.post("/booking-decision", json=body)
    assert response.status_code == 200
    assert response.json()["reason"] == "Slot is full (3/3 patients)"
