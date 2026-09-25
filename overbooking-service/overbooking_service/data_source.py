from typing import Protocol

from overbooking_service.features import PastAppointment, PatientRecord


class DataSourceUnavailable(Exception):
    """Raised when patient data cannot be read."""


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
