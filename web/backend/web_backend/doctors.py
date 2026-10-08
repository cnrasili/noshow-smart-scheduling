from datetime import UTC, date, datetime, time, timedelta
from typing import Annotated

from fastapi import APIRouter, Depends, HTTPException, Query, status
from pydantic import BaseModel
from sqlalchemy import select
from sqlalchemy.orm import Session

from noshow_db.models.core import Appointment, Doctor, DoctorSchedule, Patient, Slot
from web_backend.auth import DoctorAccount, current_account
from web_backend.clinic import CLINIC_TZ, as_utc, today
from web_backend.db import get_db
from web_backend.slots import clinic_days_in_utc

router = APIRouter(tags=["doctors"], dependencies=[Depends(current_account)])

DbSession = Annotated[Session, Depends(get_db)]

# Longest date range of the agenda; enough for a month view
MAX_AGENDA_DAYS = 31


class DoctorOut(BaseModel):
    id: int
    full_name: str
    specialty: str | None


class CalendarAppointment(BaseModel):
    id: int
    patient_name: str
    patient_age: int
    patient_gender: str
    booking_date: date
    attended: bool | None


class ScheduleDay(BaseModel):
    # 0 = Monday ... 6 = Sunday
    weekday: int
    start_time: time
    end_time: time


class CalendarSlot(BaseModel):
    slot_id: int
    start_at: datetime
    end_at: datetime
    max_patients: int
    appointments: list[CalendarAppointment]


class AgendaAppointment(BaseModel):
    id: int
    slot_id: int
    start_at: datetime
    end_at: datetime
    patient_name: str
    # Booked into a slot that already had a patient (overbooking)
    extra: bool


class AgendaDay(BaseModel):
    date: date
    # 0 when the doctor has no slots that day
    slot_count: int
    appointments: list[AgendaAppointment]


class AttendanceRequest(BaseModel):
    attended: bool


def _calendar_appointment(appointment: Appointment, patient: Patient) -> CalendarAppointment:
    return CalendarAppointment(
        id=appointment.id,
        patient_name=patient.full_name,
        patient_age=patient.age,
        patient_gender=patient.gender,
        booking_date=appointment.booking_date,
        attended=appointment.attended,
    )


@router.get("/doctors")
def list_doctors(db: DbSession) -> list[DoctorOut]:
    doctors = db.scalars(select(Doctor).order_by(Doctor.full_name))
    return [DoctorOut(id=d.id, full_name=d.full_name, specialty=d.specialty) for d in doctors]


@router.get("/doctors/me/calendar")
def my_calendar(
    account: DoctorAccount,
    db: DbSession,
    day: Annotated[date | None, Query(alias="date")] = None,
) -> list[CalendarSlot]:
    """All slots of one clinic day, empty ones included, with their patients."""
    range_start, range_end = clinic_days_in_utc(day or today(), day or today())
    slots = db.scalars(
        select(Slot)
        .where(
            Slot.doctor_id == account.doctor_id,
            Slot.start_at >= range_start,
            Slot.start_at < range_end,
        )
        .order_by(Slot.start_at)
    ).all()
    by_slot: dict[int, list[CalendarAppointment]] = {slot.id: [] for slot in slots}
    rows = db.execute(
        select(Appointment, Patient)
        .join(Patient, Patient.id == Appointment.patient_id)
        .where(Appointment.slot_id.in_(by_slot))
        .order_by(Appointment.created_at, Appointment.id)
    )
    for appointment, patient in rows:
        by_slot[appointment.slot_id].append(_calendar_appointment(appointment, patient))

    return [
        CalendarSlot(
            slot_id=slot.id,
            start_at=as_utc(slot.start_at),
            end_at=as_utc(slot.end_at),
            max_patients=slot.max_patients,
            appointments=by_slot[slot.id],
        )
        for slot in slots
    ]


@router.get("/doctors/me/agenda")
def my_agenda(
    account: DoctorAccount,
    db: DbSession,
    date_from: date,
    date_to: date,
) -> list[AgendaDay]:
    """Every clinic day of a range with its slot count and booked appointments."""
    if date_to < date_from or (date_to - date_from).days >= MAX_AGENDA_DAYS:
        raise HTTPException(
            status.HTTP_422_UNPROCESSABLE_CONTENT,
            f"date_to must be on or after date_from and at most {MAX_AGENDA_DAYS} days in range",
        )
    range_start, range_end = clinic_days_in_utc(date_from, date_to)
    in_range = (
        Slot.doctor_id == account.doctor_id,
        Slot.start_at >= range_start,
        Slot.start_at < range_end,
    )

    days = {
        date_from + timedelta(days=n): AgendaDay(
            date=date_from + timedelta(days=n), slot_count=0, appointments=[]
        )
        for n in range((date_to - date_from).days + 1)
    }
    for start_at in db.scalars(select(Slot.start_at).where(*in_range)):
        days[as_utc(start_at).astimezone(CLINIC_TZ).date()].slot_count += 1

    rows = db.execute(
        select(Appointment, Slot, Patient.full_name)
        .join(Slot, Slot.id == Appointment.slot_id)
        .join(Patient, Patient.id == Appointment.patient_id)
        .where(*in_range)
        .order_by(Slot.start_at, Appointment.created_at, Appointment.id)
    )
    seen_slots: set[int] = set()
    for appointment, slot, patient_name in rows:
        start_at = as_utc(slot.start_at)
        days[start_at.astimezone(CLINIC_TZ).date()].appointments.append(
            AgendaAppointment(
                id=appointment.id,
                slot_id=slot.id,
                start_at=start_at,
                end_at=as_utc(slot.end_at),
                patient_name=patient_name,
                extra=slot.id in seen_slots,
            )
        )
        seen_slots.add(slot.id)
    return list(days.values())


@router.patch("/appointments/{appointment_id}/attendance")
def mark_attendance(
    appointment_id: int, body: AttendanceRequest, account: DoctorAccount, db: DbSession
) -> CalendarAppointment:
    row = db.execute(
        select(Appointment, Slot, Patient)
        .join(Slot, Slot.id == Appointment.slot_id)
        .join(Patient, Patient.id == Appointment.patient_id)
        .where(Appointment.id == appointment_id, Slot.doctor_id == account.doctor_id)
    ).first()
    if row is None:
        raise HTTPException(status.HTTP_404_NOT_FOUND, "Appointment not found")
    appointment, slot, patient = row
    if as_utc(slot.start_at) > datetime.now(UTC):
        raise HTTPException(
            status.HTTP_422_UNPROCESSABLE_CONTENT,
            "Attendance can be marked once the appointment has started",
        )

    appointment.attended = body.attended
    db.commit()
    return _calendar_appointment(appointment, patient)


@router.get("/doctors/me/schedule")
def my_schedule(account: DoctorAccount, db: DbSession) -> list[ScheduleDay]:
    """Weekly working hours that slots are generated from."""
    schedules = db.scalars(
        select(DoctorSchedule)
        .where(DoctorSchedule.doctor_id == account.doctor_id)
        .order_by(DoctorSchedule.weekday)
    )
    return [
        ScheduleDay(weekday=s.weekday, start_time=s.start_time, end_time=s.end_time)
        for s in schedules
    ]
