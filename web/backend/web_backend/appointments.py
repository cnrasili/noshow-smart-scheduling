# Patient booking and cancellation
from datetime import UTC, date, datetime
from typing import Annotated

from fastapi import APIRouter, BackgroundTasks, Depends, HTTPException, Response, status
from pydantic import BaseModel
from sqlalchemy import select
from sqlalchemy.exc import IntegrityError
from sqlalchemy.orm import Session

from noshow_db.models.core import Appointment, Doctor, Patient, Slot
from web_backend.auth import PatientAccount
from web_backend.clinic import CLINIC_TZ, as_utc, today
from web_backend.db import get_db
from web_backend.overbooking import OverbookingClient, get_overbooking_client

router = APIRouter(tags=["appointments"])

DbSession = Annotated[Session, Depends(get_db)]
Overbooking = Annotated[OverbookingClient, Depends(get_overbooking_client)]


class BookingRequest(BaseModel):
    slot_id: int


class AppointmentOut(BaseModel):
    id: int
    slot_id: int
    doctor_name: str
    doctor_specialty: str | None
    start_at: datetime
    end_at: datetime
    appointment_date: date
    booking_date: date
    attended: bool | None


def _appointment_out(appointment: Appointment, slot: Slot, doctor: Doctor) -> AppointmentOut:
    return AppointmentOut(
        id=appointment.id,
        slot_id=slot.id,
        doctor_name=doctor.full_name,
        doctor_specialty=doctor.specialty,
        start_at=as_utc(slot.start_at),
        end_at=as_utc(slot.end_at),
        appointment_date=appointment.appointment_date,
        booking_date=appointment.booking_date,
        attended=appointment.attended,
    )


@router.get("/patients/me/appointments")
def my_appointments(account: PatientAccount, db: DbSession) -> list[AppointmentOut]:
    rows = db.execute(
        select(Appointment, Slot, Doctor)
        .join(Slot, Slot.id == Appointment.slot_id)
        .join(Doctor, Doctor.id == Slot.doctor_id)
        .where(Appointment.patient_id == account.patient_id)
        .order_by(Slot.start_at)
    ).all()
    return [_appointment_out(*row) for row in rows]


@router.post("/appointments", status_code=status.HTTP_201_CREATED)
def book(
    body: BookingRequest,
    account: PatientAccount,
    db: DbSession,
    overbooking: Overbooking,
    background: BackgroundTasks,
) -> AppointmentOut:
    # Lock the slot so two concurrent bookings cannot both see it empty (PostgreSQL)
    slot = db.scalar(select(Slot).where(Slot.id == body.slot_id).with_for_update())
    if slot is None:
        raise HTTPException(status.HTTP_404_NOT_FOUND, "Slot not found")
    start_at = as_utc(slot.start_at)
    if start_at <= datetime.now(UTC):
        raise HTTPException(status.HTTP_422_UNPROCESSABLE_CONTENT, "Slot has already started")

    patients = set(db.scalars(select(Appointment.patient_id).where(Appointment.slot_id == slot.id)))
    if account.patient_id in patients:
        raise HTTPException(status.HTTP_409_CONFLICT, "You already booked this slot")
    if len(patients) >= slot.max_patients:
        raise HTTPException(status.HTTP_409_CONFLICT, "Slot is full")

    # The overbooking service decides whether the patient may join the slot. The slot row
    # stays locked meanwhile, so concurrent bookings of this slot wait for the decision.
    booking_date = today()
    decision = overbooking.booking_decision(account.patient_id, slot.id, booking_date)
    if decision is None:
        # Service unavailable: empty slots can still be booked, but never overbooked
        if patients:
            raise HTTPException(status.HTTP_409_CONFLICT, "Slot is already booked")
    elif not decision.allow:
        raise HTTPException(status.HTTP_409_CONFLICT, "Slot is not available")

    appointment = Appointment(
        patient_id=account.patient_id,
        slot_id=slot.id,
        appointment_date=start_at.astimezone(CLINIC_TZ).date(),
        booking_date=booking_date,
    )
    db.add(appointment)
    try:
        db.commit()
    except IntegrityError as error:
        db.rollback()
        raise HTTPException(status.HTTP_409_CONFLICT, "Slot is no longer available") from error

    # Sent after the response so a slow or stopped service does not delay the patient
    background.add_task(
        overbooking.appointment_booked,
        appointment.id,
        account.patient_id,
        db.get(Patient, account.patient_id).email,
        start_at.astimezone(CLINIC_TZ),
    )
    return _appointment_out(appointment, slot, db.get(Doctor, slot.doctor_id))


@router.delete("/appointments/{appointment_id}", status_code=status.HTTP_204_NO_CONTENT)
def cancel(
    appointment_id: int,
    account: PatientAccount,
    db: DbSession,
    overbooking: Overbooking,
    background: BackgroundTasks,
) -> Response:
    row = db.execute(
        select(Appointment, Slot)
        .join(Slot, Slot.id == Appointment.slot_id)
        .where(Appointment.id == appointment_id, Appointment.patient_id == account.patient_id)
    ).first()
    if row is None:
        raise HTTPException(status.HTTP_404_NOT_FOUND, "Appointment not found")
    appointment, slot = row
    if as_utc(slot.start_at) <= datetime.now(UTC):
        raise HTTPException(
            status.HTTP_422_UNPROCESSABLE_CONTENT, "Past appointments cannot be cancelled"
        )

    # The schema has no cancellation state, so the booking is removed
    db.delete(appointment)
    db.commit()
    background.add_task(overbooking.appointment_cancelled, appointment_id)
    return Response(status_code=status.HTTP_204_NO_CONTENT)
