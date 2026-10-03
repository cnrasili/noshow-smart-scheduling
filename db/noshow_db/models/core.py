# Core tables of the booking application: patients, doctors, slots, appointments
from datetime import date, datetime, time

from sqlalchemy import (
    CheckConstraint,
    DateTime,
    ForeignKey,
    String,
    Time,
    UniqueConstraint,
    func,
)
from sqlalchemy.orm import Mapped, mapped_column

from noshow_db.base import Base


class Patient(Base):
    __tablename__ = "patients"

    id: Mapped[int] = mapped_column(primary_key=True)
    full_name: Mapped[str] = mapped_column(String(255))
    email: Mapped[str] = mapped_column(String(255), unique=True, index=True)
    # Age is stored as recorded at registration; it is a model feature known at booking time
    age: Mapped[int]
    gender: Mapped[str] = mapped_column(String(1))
    scholarship: Mapped[bool] = mapped_column(default=False)
    hipertension: Mapped[bool] = mapped_column(default=False)
    diabetes: Mapped[bool] = mapped_column(default=False)
    alcoholism: Mapped[bool] = mapped_column(default=False)
    handcap: Mapped[int] = mapped_column(default=0)
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), server_default=func.now())


class Doctor(Base):
    __tablename__ = "doctors"

    id: Mapped[int] = mapped_column(primary_key=True)
    full_name: Mapped[str] = mapped_column(String(255))
    specialty: Mapped[str | None] = mapped_column(String(255))


class DoctorSchedule(Base):
    """Recurring weekly working hours used to generate slots; one interval per weekday."""

    __tablename__ = "doctor_schedules"
    __table_args__ = (
        UniqueConstraint("doctor_id", "weekday"),
        CheckConstraint("end_time > start_time"),
    )

    id: Mapped[int] = mapped_column(primary_key=True)
    doctor_id: Mapped[int] = mapped_column(ForeignKey("doctors.id"), index=True)
    # 0 = Monday ... 6 = Sunday
    weekday: Mapped[int]
    start_time: Mapped[time] = mapped_column(Time)
    end_time: Mapped[time] = mapped_column(Time)


class Slot(Base):
    __tablename__ = "slots"
    __table_args__ = (UniqueConstraint("doctor_id", "start_at"),)

    id: Mapped[int] = mapped_column(primary_key=True)
    doctor_id: Mapped[int] = mapped_column(ForeignKey("doctors.id"), index=True)
    start_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), index=True)
    end_at: Mapped[datetime] = mapped_column(DateTime(timezone=True))
    # Maximum patients in one slot, including overbooks
    max_patients: Mapped[int] = mapped_column(default=2)


class Appointment(Base):
    """A patient's booking of a slot; several appointments may share a slot (overbooking)."""

    __tablename__ = "appointments"
    __table_args__ = (UniqueConstraint("patient_id", "slot_id"),)

    id: Mapped[int] = mapped_column(primary_key=True)
    patient_id: Mapped[int] = mapped_column(ForeignKey("patients.id"), index=True)
    slot_id: Mapped[int] = mapped_column(ForeignKey("slots.id"), index=True)
    appointment_date: Mapped[date]
    booking_date: Mapped[date]
    # NULL until the doctor marks the appointment as attended or missed
    attended: Mapped[bool | None]
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), server_default=func.now())
