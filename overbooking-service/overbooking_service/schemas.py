from datetime import date, datetime

from pydantic import AwareDatetime, BaseModel, Field


class PredictRequest(BaseModel):
    patient_id: int = Field(gt=0)
    appointment_date: date
    booking_date: date


class PredictResponse(BaseModel):
    p_noshow: float = Field(ge=0, le=1)
    model_version: str


class BookingDecisionRequest(BaseModel):
    patient_id: int = Field(gt=0)
    slot_id: int = Field(gt=0)
    booking_date: date


class BookingDecisionResponse(BaseModel):
    allow: bool
    overbook: bool
    p_noshow: float = Field(ge=0, le=1)
    reason: str


class AppointmentBooked(BaseModel):
    appointment_id: int = Field(gt=0)
    patient_id: int = Field(gt=0)
    email: str = Field(max_length=255, pattern=r"^[^@\s]+@[^@\s]+$")
    appointment_start: AwareDatetime


class AppointmentCancelled(BaseModel):
    appointment_id: int = Field(gt=0)


class ScheduledMessage(BaseModel):
    kind: str
    send_at: datetime
    status: str


class ScheduledMessages(BaseModel):
    messages: list[ScheduledMessage]
    ab_group: str | None


class AbGroupSummary(BaseModel):
    group: str
    appointments: int
    no_shows: int
    no_show_rate: float | None


class AbSummary(BaseModel):
    groups: list[AbGroupSummary]
    difference: float | None
    z: float | None
    p_value: float | None


class CancelledMessages(BaseModel):
    cancelled: int
