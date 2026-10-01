from datetime import date

from pydantic import BaseModel, Field


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
