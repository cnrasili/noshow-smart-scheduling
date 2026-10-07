from datetime import UTC, date, datetime, timedelta
from zoneinfo import ZoneInfo

import pytest
from fastapi.testclient import TestClient
from sqlalchemy.orm import Session, sessionmaker

from noshow_db.models.core import Appointment, Doctor, Patient, Slot
from overbooking_service.dependencies import get_kpi_settings
from overbooking_service.kpi import SlotLoad, compute_kpis, load_day

CLINIC = ZoneInfo("Europe/Istanbul")
START = datetime(2026, 11, 10, 6, 0, tzinfo=UTC)


def session_of(*loads: tuple[int, int]) -> list[SlotLoad]:
    """15-minute slots from (booked, attended) pairs."""
    return [
        SlotLoad(START + timedelta(minutes=15 * i), START + timedelta(minutes=15 * (i + 1)), b, a)
        for i, (b, a) in enumerate(loads)
    ]


def test_no_slots_has_no_kpis():
    assert compute_kpis([], 12) is None


def test_one_patient_per_slot():
    kpis = compute_kpis(session_of((1, 1), (1, 1), (1, 1), (1, 1)), 12)
    assert kpis.utilization == pytest.approx(0.8)
    assert kpis.idle_minutes == pytest.approx(12)
    assert kpis.overtime_minutes == 0
    assert kpis.mean_wait_minutes == 0
    assert (kpis.overbooked_slots, kpis.patients_seen) == (0, 4)


def test_overbooked_patient_waits_and_fills_idle_time():
    kpis = compute_kpis(session_of((2, 2), (1, 1), (1, 1), (1, 1)), 12)
    assert kpis.utilization == pytest.approx(1.0)
    assert kpis.idle_minutes == pytest.approx(0)
    assert kpis.overtime_minutes == 0
    # Waits: 0, 12, 9, 6, 3
    assert kpis.mean_wait_minutes == pytest.approx(6)
    assert (kpis.overbooked_slots, kpis.patients_seen) == (1, 5)


def test_overtime_when_patients_run_past_session_end():
    kpis = compute_kpis(session_of((2, 2), (1, 1), (1, 1), (1, 1)), 15)
    assert kpis.overtime_minutes == pytest.approx(15)
    assert kpis.idle_minutes == pytest.approx(0)
    assert kpis.utilization == pytest.approx(75 / 60)
    assert kpis.mean_wait_minutes == pytest.approx(12)


def test_no_shows_leave_idle_time():
    kpis = compute_kpis(session_of((1, 1), (1, 0), (2, 0), (0, 0)), 12)
    assert kpis.idle_minutes == pytest.approx(48)
    assert kpis.utilization == pytest.approx(0.2)
    assert (kpis.overbooked_slots, kpis.patients_seen) == (1, 1)


def test_slot_order_does_not_matter():
    slots = session_of((1, 1), (2, 2), (1, 1))
    assert compute_kpis(slots[::-1], 12) == compute_kpis(slots, 12)


@pytest.fixture
def clinic(session_factory: sessionmaker[Session]) -> None:
    with session_factory() as session:
        session.add_all(
            [Doctor(id=1, full_name="Dr. Ada"), Doctor(id=2, full_name="Dr. Bora")]
            + [
                Patient(id=i, full_name=f"P{i}", email=f"p{i}@example.com", age=40, gender="F")
                for i in range(1, 6)
            ]
            # Four 15-minute slots from 09:00 clinic time on 10 November
            + [
                Slot(
                    id=10 + i,
                    doctor_id=1,
                    start_at=START + timedelta(minutes=15 * i),
                    end_at=START + timedelta(minutes=15 * (i + 1)),
                )
                for i in range(4)
            ]
            # 23:30 clinic time on 9 November belongs to the previous day
            + [
                Slot(
                    id=20,
                    doctor_id=1,
                    start_at=datetime(2026, 11, 9, 20, 30, tzinfo=UTC),
                    end_at=datetime(2026, 11, 9, 20, 45, tzinfo=UTC),
                )
            ]
        )
        session.flush()
        outcomes = [(1, 10, True), (2, 10, True), (3, 11, True), (4, 12, False), (5, 13, None)]
        session.add_all(
            [
                Appointment(
                    patient_id=p,
                    slot_id=s,
                    appointment_date=date(2026, 11, 10),
                    booking_date=date(2026, 11, 1),
                    attended=attended,
                )
                for p, s, attended in outcomes
            ]
        )
        session.commit()


def test_day_is_loaded_in_clinic_timezone(session_factory: sessionmaker[Session], clinic):
    with session_factory() as session:
        loads = load_day(session, 1, date(2026, 11, 10), CLINIC)
    assert sorted((s.booked, s.attended) for s in loads) == [(1, 0), (1, 0), (1, 1), (2, 2)]


def test_kpi_endpoint(client: TestClient, clinic):
    response = client.get("/kpi", params={"doctor_id": 1, "date": "2026-11-10"})
    assert response.status_code == 200
    # Patients 1 and 2 in the first slot, patient 3 in the second; waits 0, 12 and 9 minutes
    assert response.json() == {
        "utilization": 0.6,
        "idle_minutes": 24.0,
        "overtime_minutes": 0.0,
        "mean_wait_minutes": 7.0,
        "overbooked_slots": 1,
        "patients_seen": 3,
    }


@pytest.mark.parametrize(
    "params",
    [{"doctor_id": 99, "date": "2026-11-10"}, {"doctor_id": 2, "date": "2026-11-10"}],
)
def test_kpi_not_found(client: TestClient, clinic, params: dict):
    assert client.get("/kpi", params=params).status_code == 404


def test_kpi_invalid_request(client: TestClient):
    assert client.get("/kpi", params={"doctor_id": 0, "date": "2026-11-10"}).status_code == 422


def test_dashboard_moved_to_admin_service(client: TestClient):
    assert client.get("/dashboard").status_code == 404


def test_default_settings_come_from_config():
    settings = get_kpi_settings()
    assert settings.service_minutes == 12
