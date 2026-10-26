# Patient booking and cancellation
from datetime import UTC, date, datetime
from typing import Annotated

from fastapi import APIRouter, BackgroundTasks, Depends, HTTPException, Response, status
from pydantic import BaseModel
from sqlalchemy import exists, func, select
from sqlalchemy.exc import IntegrityError
from sqlalchemy.orm import Session

from noshow_db.models.core import Appointment, Slot
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
    start_at: datetime
    end_at: datetime
    appointment_date: date
    booking_date: date
    attended: bool | None


def _appointment_out(appointment: Appointment, slot: Slot) -> AppointmentOut:
    return AppointmentOut(
        id=appointment.id,
        slot_id=slot.id,
        start_at=as_utc(slot.start_at),
        end_at=as_utc(slot.end_at),
        appointment_date=appointment.appointment_date,
        booking_date=appointment.booking_date,
        attended=appointment.attended,
    )


def _lock_department_day(db: Session, doctor_id: int, day: date) -> None:
    """Hold a transaction-level lock on the department's day; other databases skip it."""
    if db.get_bind().dialect.name == "postgresql":
        db.execute(select(func.pg_advisory_xact_lock(doctor_id, day.toordinal())))


def _has_appointment_on(db: Session, patient_id: int, doctor_id: int, day: date) -> bool:
    """Whether the patient already has an appointment with the department on the day."""
    return db.scalar(
        select(
            exists()
            .where(Appointment.patient_id == patient_id, Appointment.appointment_date == day)
            .where(Appointment.slot_id == Slot.id, Slot.doctor_id == doctor_id)
        )
    )


@router.get("/patients/me/appointments")
def my_appointments(account: PatientAccount, db: DbSession) -> list[AppointmentOut]:
    rows = db.execute(
        select(Appointment, Slot)
        .join(Slot, Slot.id == Appointment.slot_id)
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
    slot = db.get(Slot, body.slot_id)
    if slot is None:
        raise HTTPException(status.HTTP_404_NOT_FOUND, "Slot not found")
    start_at = as_utc(slot.start_at)
    if start_at <= datetime.now(UTC):
        raise HTTPException(status.HTTP_422_UNPROCESSABLE_CONTENT, "Slot has already started")
    day = start_at.astimezone(CLINIC_TZ).date()

    # Bookings of the same department day wait for each other until commit: the overbooking
    # service counts the day's overbooks from committed appointments, so its daily limit only
    # holds if no other booking of the day is being decided meanwhile (PostgreSQL)
    _lock_department_day(db, slot.doctor_id, day)
    # Lock the slot so two concurrent bookings cannot both see it empty (PostgreSQL)
    db.refresh(slot, with_for_update=True)

    patients = set(db.scalars(select(Appointment.patient_id).where(Appointment.slot_id == slot.id)))
    if account.patient_id in patients:
        raise HTTPException(status.HTTP_409_CONFLICT, "You already booked this slot")
    if _has_appointment_on(db, account.patient_id, slot.doctor_id, day):
        raise HTTPException(status.HTTP_409_CONFLICT, "You already have an appointment on this day")
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
        appointment_date=day,
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
        start_at.astimezone(CLINIC_TZ),
    )
    return _appointment_out(appointment, slot)


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
