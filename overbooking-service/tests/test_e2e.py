"""Booking flow across the service: demo data, decision, messages, outcome, A/B and KPIs."""

from datetime import UTC, date, datetime, timedelta
from zoneinfo import ZoneInfo

from fastapi.testclient import TestClient
from sqlalchemy import func, select
from sqlalchemy.orm import Session, sessionmaker

from noshow_db.models.core import Appointment, Patient, Slot
from noshow_db.models.service import BookingDecision
from overbooking_service.ab import assign_group
from overbooking_service.config import settings
from overbooking_service.demo import DemoConfig, seed
from overbooking_service.dependencies import get_data_source, get_now
from overbooking_service.dispatcher import dispatch_due
from overbooking_service.main import app
from overbooking_service.national_id import fictional_national_id
from overbooking_service.predictor import Predictor

CLINIC = ZoneInfo("Europe/Istanbul")
TODAY = date(2026, 11, 16)
NOW = datetime(2026, 11, 16, 8, 0, tzinfo=CLINIC).astimezone(UTC)
DAY = date(2026, 11, 18)
NEW_PATIENT = 999


class FakeSender:
    def __init__(self) -> None:
        self.sent: list[tuple[str, str]] = []

    def send(self, to: str, subject: str, body: str) -> None:
        self.sent.append((to, subject))


def empty_slot(session: Session, doctor_id: int, day: date) -> Slot:
    start = datetime.combine(day, datetime.min.time(), CLINIC).astimezone(UTC)
    booked = select(Appointment.slot_id)
    return session.scalars(
        select(Slot)
        .where(
            Slot.doctor_id == doctor_id,
            Slot.start_at >= start,
            Slot.start_at < start + timedelta(days=1),
            Slot.id.not_in(booked),
        )
        .order_by(Slot.start_at)
    ).first()


def test_booking_flow(client: TestClient, session_factory: sessionmaker[Session], clinic):
    del app.dependency_overrides[get_data_source]
    app.dependency_overrides[get_now] = lambda: NOW
    with session_factory() as session:
        clinic(session, TODAY)
        cfg = DemoConfig(today=TODAY, seed=3, patients=60, past_days=7, future_days=3)
        seed(session, cfg, Predictor.load(settings.model_dir), settings.overbooking)
        session.add(
            Patient(
                id=NEW_PATIENT,
                national_id=fictional_national_id(NEW_PATIENT),
                full_name="New",
                email="new@example.com",
                age=35,
                gender="M",
            )
        )
        session.commit()
        slot = empty_slot(session, 1, DAY)
        slot_id, slot_start = slot.id, slot.start_at.replace(tzinfo=UTC)
    before = client.get("/ab/summary").json()

    # 1. Booking decision for an empty slot
    decision = client.post(
        "/booking-decision",
        json={"patient_id": NEW_PATIENT, "slot_id": slot_id, "booking_date": TODAY.isoformat()},
    ).json()
    assert decision["allow"] and not decision["overbook"]

    # 2. The booking application stores the appointment and reports it
    with session_factory() as session:
        appointment = Appointment(
            patient_id=NEW_PATIENT, slot_id=slot_id, appointment_date=DAY, booking_date=TODAY
        )
        session.add(appointment)
        session.commit()
        appointment_id = appointment.id
    booked = client.post(
        "/events/appointment-booked",
        json={
            "appointment_id": appointment_id,
            "patient_id": NEW_PATIENT,
            "email": "new@example.com",
            "appointment_start": slot_start.astimezone(CLINIC).isoformat(),
        },
    ).json()
    group = assign_group(NEW_PATIENT, settings.ab_test.salt)
    assert booked["ab_group"] == group
    kinds = ["confirmation", "reminder"] if group == "reminder" else ["confirmation"]
    assert [m["kind"] for m in booked["messages"]] == kinds

    # 3. The dispatcher sends the confirmation now and the reminder a day before
    sender = FakeSender()
    with session_factory() as session:
        assert dispatch_due(session, sender, NOW, 3) == 1
        reminder_time = slot_start - timedelta(hours=settings.reminders.hours_before)
        assert dispatch_due(session, sender, reminder_time, 3) == len(kinds) - 1
    assert [subject for _, subject in sender.sent] == [
        "Randevunuz onaylandı",
        "Randevu hatırlatması",
    ][: len(kinds)]

    # 4. The doctor marks the patient as attended
    with session_factory() as session:
        session.get(Appointment, appointment_id).attended = True
        session.commit()
        assert session.scalar(select(func.count()).select_from(BookingDecision)) == 1

    after = client.get("/ab/summary").json()
    index = 0 if group == "reminder" else 1
    assert after["groups"][index]["appointments"] == before["groups"][index]["appointments"] + 1

    kpi = client.get("/kpi", params={"doctor_id": 1, "date": DAY.isoformat()}).json()
    assert kpi["patients_seen"] == 1
    assert (
        client.get("/kpi", params={"doctor_id": 1, "date": "2026-11-12"}).json()["patients_seen"]
        > 0
    )
