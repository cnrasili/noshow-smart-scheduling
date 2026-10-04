from dataclasses import dataclass
from datetime import UTC, date, datetime, time, timedelta
from typing import Protocol
from zoneinfo import ZoneInfo

from sqlalchemy import func, select
from sqlalchemy.exc import SQLAlchemyError
from sqlalchemy.orm import Session

from noshow_db.models.core import Appointment, Patient, Slot
from overbooking_service.features import PastAppointment, PatientRecord


class DataSourceUnavailable(Exception):
    """Raised when patient or slot data cannot be read."""


class PatientDataSource(Protocol):
    """Read access to patient records and appointment history."""

    def get_patient(self, patient_id: int) -> PatientRecord | None: ...

    def get_history(self, patient_id: int) -> list[PastAppointment]: ...


@dataclass(frozen=True)
class SlotBooking:
    patient_id: int
    booking_date: date


@dataclass(frozen=True)
class SlotState:
    slot_id: int
    doctor_id: int
    slot_date: date
    max_patients: int
    bookings: tuple[SlotBooking, ...]


class SlotDataSource(Protocol):
    """Read access to slots and their bookings."""

    def get_slot(self, slot_id: int) -> SlotState | None: ...

    def count_overbooks(self, doctor_id: int, slot_date: date) -> int:
        """Number of overbooked appointments of a doctor on a date."""
        ...


class DbPatientSource:
    """Patient records and history from the booking application tables."""

    def __init__(self, session: Session) -> None:
        self.session = session

    def get_patient(self, patient_id: int) -> PatientRecord | None:
        try:
            patient = self.session.get(Patient, patient_id)
        except SQLAlchemyError as exc:
            raise DataSourceUnavailable("Patient data cannot be read") from exc
        if patient is None:
            return None
        return PatientRecord(
            patient_id=patient.id,
            age=patient.age,
            gender=patient.gender,
            scholarship=patient.scholarship,
            hipertension=patient.hipertension,
            diabetes=patient.diabetes,
            alcoholism=patient.alcoholism,
            handcap=patient.handcap,
        )

    def get_history(self, patient_id: int) -> list[PastAppointment]:
        # Only appointments with a recorded outcome
        query = (
            select(Appointment.appointment_date, Appointment.attended)
            .where(Appointment.patient_id == patient_id, Appointment.attended.is_not(None))
            .order_by(Appointment.appointment_date)
        )
        try:
            rows = self.session.execute(query).all()
        except SQLAlchemyError as exc:
            raise DataSourceUnavailable("Appointment history cannot be read") from exc
        return [PastAppointment(row.appointment_date, row.attended) for row in rows]


class DbSlotSource:
    """Slots and bookings from the booking application tables."""

    def __init__(self, session: Session, timezone: ZoneInfo) -> None:
        self.session = session
        self.timezone = timezone

    def _local_date(self, moment: datetime) -> date:
        # SQLite returns naive datetimes; stored values are UTC
        if moment.tzinfo is None:
            moment = moment.replace(tzinfo=UTC)
        return moment.astimezone(self.timezone).date()

    def get_slot(self, slot_id: int) -> SlotState | None:
        try:
            slot = self.session.get(Slot, slot_id)
            if slot is None:
                return None
            bookings = self.session.execute(
                select(Appointment.patient_id, Appointment.booking_date)
                .where(Appointment.slot_id == slot_id)
                .order_by(Appointment.id)
            ).all()
        except SQLAlchemyError as exc:
            raise DataSourceUnavailable("Slot data cannot be read") from exc
        return SlotState(
            slot_id=slot.id,
            doctor_id=slot.doctor_id,
            slot_date=self._local_date(slot.start_at),
            max_patients=slot.max_patients,
            bookings=tuple(SlotBooking(row.patient_id, row.booking_date) for row in bookings),
        )

    def count_overbooks(self, doctor_id: int, slot_date: date) -> int:
        # Every appointment after the first one in a slot is an overbook
        day_start = datetime.combine(slot_date, time(), self.timezone).astimezone(UTC)
        day_end = datetime.combine(slot_date + timedelta(days=1), time(), self.timezone).astimezone(
            UTC
        )
        query = (
            select(Appointment.slot_id, func.count())
            .join(Slot, Slot.id == Appointment.slot_id)
            .where(Slot.doctor_id == doctor_id, Slot.start_at >= day_start, Slot.start_at < day_end)
            .group_by(Appointment.slot_id)
        )
        try:
            counts = self.session.execute(query).all()
        except SQLAlchemyError as exc:
            raise DataSourceUnavailable("Slot data cannot be read") from exc
        return sum(n - 1 for _, n in counts)
