from datetime import UTC, datetime, timedelta
from zoneinfo import ZoneInfo

import pytest
from fastapi.testclient import TestClient
from sqlalchemy import create_engine, func, select
from sqlalchemy.orm import Session, sessionmaker

from noshow_db.base import Base
from noshow_db.models.core import Appointment, Doctor, Patient, Slot
from noshow_db.models.service import AbAssignment, Message
from overbooking_service import recovery, scheduler
from overbooking_service.ab import Group, assign_group
from overbooking_service.config import AbTestSettings, ReminderSettings, settings
from overbooking_service.dependencies import get_ab_settings, get_now
from overbooking_service.events import schedule_messages
from overbooking_service.main import app
from overbooking_service.recovery import recover_lost_bookings
from overbooking_service.schemas import AppointmentBooked

NOW = datetime(2026, 11, 2, 9, 0, tzinfo=UTC)
TZ = ZoneInfo("Europe/Istanbul")
# 10 November 2026, 09:30 in Istanbul
START = datetime(2026, 11, 10, 6, 30, tzinfo=UTC)
LOOKBACK = timedelta(hours=48)
REMINDERS = ReminderSettings(
    enabled=True, hours_before=24, dispatch_interval_seconds=60, max_attempts=3
)
AB_TEST = AbTestSettings(enabled=True, salt="reminder-ab-v1")
REMINDER_PATIENT = next(p for p in range(1, 100) if assign_group(p, AB_TEST.salt) is Group.REMINDER)
CONTROL_PATIENT = next(p for p in range(1, 100) if assign_group(p, AB_TEST.salt) is Group.CONTROL)


def utc(value: datetime) -> datetime:
    # SQLite drops the time zone; stored times are UTC
    return value.replace(tzinfo=UTC) if value.tzinfo is None else value


def make_clinic(session: Session) -> None:
    # A second schedule record lets two bookings start at the same time
    session.add_all(
        [Doctor(id=1, full_name="General Practice"), Doctor(id=2, full_name="Second schedule")]
    )
    session.add_all(
        Patient(
            id=patient_id,
            full_name=f"Patient {patient_id}",
            email=f"patient{patient_id}@demo.local",
            age=40,
            gender="F",
        )
        for patient_id in {REMINDER_PATIENT, CONTROL_PATIENT}
    )
    session.commit()


@pytest.fixture(autouse=True)
def clinic(session_factory: sessionmaker[Session]) -> None:
    with session_factory() as session:
        make_clinic(session)


def book(
    session: Session,
    patient_id: int = REMINDER_PATIENT,
    start: datetime = START,
    booked: datetime = NOW - timedelta(hours=1),
    doctor_id: int = 1,
) -> int:
    """A booking stored without its booked event."""
    slot = Slot(doctor_id=doctor_id, start_at=start, end_at=start + timedelta(minutes=20))
    session.add(slot)
    session.flush()
    appointment = Appointment(
        patient_id=patient_id,
        slot_id=slot.id,
        appointment_date=start.astimezone(TZ).date(),
        booking_date=min(booked, start).astimezone(TZ).date(),
        created_at=booked,
    )
    session.add(appointment)
    session.commit()
    return appointment.id


def recover(session: Session, now: datetime = NOW) -> int:
    return recover_lost_bookings(session, now, LOOKBACK, TZ, REMINDERS, AB_TEST)


def messages(session: Session, appointment_id: int) -> list[Message]:
    return list(
        session.scalars(
            select(Message).where(Message.appointment_id == appointment_id).order_by(Message.id)
        )
    )


def group(session: Session, appointment_id: int) -> str | None:
    return session.scalar(
        select(AbAssignment.group).where(AbAssignment.appointment_id == appointment_id)
    )


def count(session: Session, model: type) -> int:
    return session.scalar(select(func.count()).select_from(model))


def test_lost_booking_gets_confirmation_reminder_and_group(session_factory):
    with session_factory() as session:
        appointment_id = book(session)
        assert recover(session) == 1

        confirmation, reminder = messages(session, appointment_id)
        assert (confirmation.kind, utc(confirmation.send_at)) == ("confirmation", NOW)
        assert (reminder.kind, utc(reminder.send_at)) == ("reminder", START - timedelta(hours=24))
        for message in (confirmation, reminder):
            assert message.status == "pending"
            assert utc(message.appointment_start) == START
            # The local appointment time, as the booking application sends it
            assert "10 Kasım 2026 Salı, 09:30" in message.body
        assert group(session, appointment_id) == "reminder"


def test_control_group_gets_only_the_confirmation(session_factory):
    with session_factory() as session:
        appointment_id = book(session, patient_id=CONTROL_PATIENT)
        assert recover(session) == 1
        assert [m.kind for m in messages(session, appointment_id)] == ["confirmation"]
        assert group(session, appointment_id) == "control"


def test_appointment_too_close_for_a_reminder_gets_only_the_confirmation(session_factory):
    with session_factory() as session:
        appointment_id = book(session, start=NOW + timedelta(hours=5))
        assert recover(session) == 1
        assert [m.kind for m in messages(session, appointment_id)] == ["confirmation"]
        assert group(session, appointment_id) is None


def test_recovery_matches_the_booked_event(client: TestClient, session_factory):
    app.dependency_overrides[get_now] = lambda: NOW
    app.dependency_overrides[get_ab_settings] = lambda: AB_TEST
    with session_factory() as session:
        lost = book(session, doctor_id=1)
        reported = book(session, doctor_id=2)
    response = client.post(
        "/events/appointment-booked",
        json={
            "appointment_id": reported,
            "patient_id": REMINDER_PATIENT,
            "appointment_start": START.astimezone(TZ).isoformat(),
        },
    )
    assert response.status_code == 200

    with session_factory() as session:
        # The appointment with messages from its event is not recovered again
        assert recover(session) == 1

        def content(appointment_id: int) -> list[tuple]:
            return [
                (m.kind, m.body, m.appointment_start, m.send_at, m.status)
                for m in messages(session, appointment_id)
            ]

        assert content(lost) == content(reported)
        assert group(session, lost) == group(session, reported)


def test_appointments_with_messages_are_left_alone(session_factory):
    with session_factory() as session:
        appointment_id = book(session)
        booking = AppointmentBooked(
            appointment_id=appointment_id,
            patient_id=REMINDER_PATIENT,
            appointment_start=START,
        )
        scheduled, _ = schedule_messages(session, booking, NOW, REMINDERS, AB_TEST)
        session.commit()

        assert recover(session) == 0
        assert messages(session, appointment_id) == scheduled


def test_cancelled_messages_also_count_as_messages(session_factory):
    with session_factory() as session:
        appointment_id = book(session)
        recover(session)
        for message in messages(session, appointment_id):
            message.status = "cancelled"
        session.commit()

        assert recover(session) == 0
        assert len(messages(session, appointment_id)) == 2


def test_past_appointments_are_left_alone(session_factory):
    with session_factory() as session:
        book(session, start=NOW - timedelta(hours=1), booked=NOW - timedelta(hours=3))
        assert recover(session) == 0
        assert count(session, Message) == 0


@pytest.mark.parametrize(("hours_ago", "recovered"), [(47, 1), (49, 0)])
def test_only_bookings_within_the_look_back_are_recovered(
    session_factory, hours_ago: int, recovered: int
):
    with session_factory() as session:
        book(session, booked=NOW - timedelta(hours=hours_ago))
        assert recover(session) == recovered
        assert count(session, AbAssignment) == recovered


def test_second_run_changes_nothing(session_factory):
    with session_factory() as session:
        book(session)
        book(session, patient_id=CONTROL_PATIENT, doctor_id=2)
        assert recover(session) == 2
        assert recover(session, NOW + timedelta(minutes=5)) == 0
        assert (count(session, Message), count(session, AbAssignment)) == (3, 2)


def test_booked_event_after_recovery_creates_no_duplicates(client: TestClient, session_factory):
    app.dependency_overrides[get_now] = lambda: NOW
    app.dependency_overrides[get_ab_settings] = lambda: AB_TEST
    with session_factory() as session:
        appointment_id = book(session)
        recover(session)

    response = client.post(
        "/events/appointment-booked",
        json={
            "appointment_id": appointment_id,
            "patient_id": REMINDER_PATIENT,
            "appointment_start": START.astimezone(TZ).isoformat(),
        },
    )
    assert response.status_code == 200
    assert [m["kind"] for m in response.json()["messages"]] == ["confirmation", "reminder"]
    with session_factory() as session:
        assert (count(session, Message), count(session, AbAssignment)) == (2, 1)


def test_event_arriving_during_recovery_creates_no_duplicates(tmp_path, monkeypatch):
    # Separate connections to one database, like the job and a request
    engine = create_engine(f"sqlite:///{tmp_path / 'clinic.db'}")
    Base.metadata.create_all(engine)
    factory = sessionmaker(bind=engine)
    with factory() as session:
        make_clinic(session)
        appointment_id = book(session)

    def event_first(session, booking, now, reminders, ab_test):
        # The booked event commits after the job found the appointment
        with factory() as request_session:
            schedule_messages(request_session, booking, now, reminders, ab_test)
            request_session.commit()
        return schedule_messages(session, booking, now, reminders, ab_test)

    monkeypatch.setattr(recovery, "schedule_messages", event_first)
    with factory() as session:
        assert recover(session) == 0
        assert len(messages(session, appointment_id)) == 2
        assert count(session, AbAssignment) == 1
    engine.dispose()


class FakeScheduler:
    def __init__(self, **kwargs) -> None:
        self.jobs: list[tuple[object, dict]] = []

    def add_job(self, func, trigger, **kwargs) -> None:
        self.jobs.append((func, kwargs))

    def start(self) -> None:
        pass


def test_recovery_runs_at_startup_and_every_interval(monkeypatch):
    monkeypatch.setattr(scheduler, "BackgroundScheduler", FakeScheduler)
    jobs = dict(scheduler.start_scheduler().jobs)

    assert set(jobs) == {scheduler.run_dispatch, scheduler.run_recovery}
    recovery_job = jobs[scheduler.run_recovery]
    assert recovery_job["seconds"] == settings.message_recovery.interval_seconds == 300
    assert recovery_job["next_run_time"] <= datetime.now(UTC)
    assert settings.message_recovery.lookback_hours == 48


def test_recovery_can_be_turned_off(monkeypatch):
    monkeypatch.setattr(scheduler, "BackgroundScheduler", FakeScheduler)
    monkeypatch.setattr(settings.message_recovery, "enabled", False)
    jobs = dict(scheduler.start_scheduler().jobs)
    assert set(jobs) == {scheduler.run_dispatch}
