from dataclasses import dataclass
from datetime import date
from typing import Protocol

from overbooking_service.features import PastAppointment, PatientRecord


class DataSourceUnavailable(Exception):
    """Raised when patient or slot data cannot be read."""


class PatientDataSource(Protocol):
    """Read access to patient records and appointment history."""

    def get_patient(self, patient_id: int) -> PatientRecord | None: ...

    def get_history(self, patient_id: int) -> list[PastAppointment]: ...


class UnconfiguredDataSource:
    """Placeholder until the booking application tables exist."""

    def get_patient(self, patient_id: int) -> PatientRecord | None:
        raise DataSourceUnavailable("Patient data source is not configured")

    def get_history(self, patient_id: int) -> list[PastAppointment]:
        raise DataSourceUnavailable("Patient data source is not configured")


@dataclass(frozen=True)
class SlotBooking:
    patient_id: int
    booking_date: date


@dataclass(frozen=True)
class SlotState:
    slot_id: int
    doctor_id: int
    slot_date: date
    bookings: tuple[SlotBooking, ...]


class SlotDataSource(Protocol):
    """Read access to slots and their bookings."""

    def get_slot(self, slot_id: int) -> SlotState | None: ...

    def count_overbooks(self, doctor_id: int, slot_date: date) -> int:
        """Number of overbooked appointments of a doctor on a date."""
        ...


class UnconfiguredSlotSource:
    """Placeholder until the booking application tables exist."""

    def get_slot(self, slot_id: int) -> SlotState | None:
        raise DataSourceUnavailable("Slot data source is not configured")

    def count_overbooks(self, doctor_id: int, slot_date: date) -> int:
        raise DataSourceUnavailable("Slot data source is not configured")
