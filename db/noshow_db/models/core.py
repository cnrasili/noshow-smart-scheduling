# Core tables of the booking application: patients, doctors, slots, appointments, login accounts
from datetime import date, datetime, time

from sqlalchemy import (
    CheckConstraint,
    DateTime,
    ForeignKey,
    String,
    Time,
    UniqueConstraint,
    false,
    func,
    text,
)
from sqlalchemy.orm import Mapped, mapped_column

from noshow_db.base import Base


class Patient(Base):
    __tablename__ = "patients"
    __table_args__ = (
        CheckConstraint("age >= 0", name="ck_patients_age_non_negative"),
        CheckConstraint("handcap >= 0", name="ck_patients_handcap_non_negative"),
    )

    id: Mapped[int] = mapped_column(primary_key=True)
    full_name: Mapped[str] = mapped_column(String(255))
    email: Mapped[str] = mapped_column(String(255), unique=True, index=True)
    # Age is stored as recorded at registration; it is a model feature known at booking time
    age: Mapped[int]
    gender: Mapped[str] = mapped_column(String(1))
    scholarship: Mapped[bool] = mapped_column(default=False, server_default=false())
    hipertension: Mapped[bool] = mapped_column(default=False, server_default=false())
    diabetes: Mapped[bool] = mapped_column(default=False, server_default=false())
    alcoholism: Mapped[bool] = mapped_column(default=False, server_default=false())
    handcap: Mapped[int] = mapped_column(default=0, server_default=text("0"))
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
    __table_args__ = (
        UniqueConstraint("doctor_id", "start_at"),
        CheckConstraint("end_at > start_at", name="ck_slots_end_after_start"),
        CheckConstraint("max_patients >= 1", name="ck_slots_max_patients_positive"),
    )

    id: Mapped[int] = mapped_column(primary_key=True)
    doctor_id: Mapped[int] = mapped_column(ForeignKey("doctors.id"), index=True)
    start_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), index=True)
    end_at: Mapped[datetime] = mapped_column(DateTime(timezone=True))
    # Maximum patients in one slot, including overbooks; enforced by a PostgreSQL trigger
    max_patients: Mapped[int] = mapped_column(default=2, server_default=text("2"))


class Appointment(Base):
    """A patient's booking of a slot; several appointments may share a slot (overbooking).

    PostgreSQL triggers keep appointment_date equal to the slot's date in the clinic
    timezone and reject bookings beyond the slot's max_patients.
    """

    __tablename__ = "appointments"
    __table_args__ = (
        UniqueConstraint("patient_id", "slot_id"),
        CheckConstraint(
            "booking_date <= appointment_date", name="ck_appointments_booked_before_date"
        ),
    )

    id: Mapped[int] = mapped_column(primary_key=True)
    patient_id: Mapped[int] = mapped_column(ForeignKey("patients.id"), index=True)
    slot_id: Mapped[int] = mapped_column(ForeignKey("slots.id"), index=True)
    appointment_date: Mapped[date]
    booking_date: Mapped[date]
    # NULL until the doctor marks the appointment as attended or missed
    attended: Mapped[bool | None]
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), server_default=func.now())


class UserAccount(Base):
    """Login of a patient or a doctor; kept apart from the patient and doctor records."""

    __tablename__ = "user_accounts"
    __table_args__ = (
        CheckConstraint(
            "(role = 'patient' AND patient_id IS NOT NULL AND doctor_id IS NULL)"
            " OR (role = 'doctor' AND doctor_id IS NOT NULL AND patient_id IS NULL)",
            name="ck_user_accounts_role_matches_owner",
        ),
    )

    id: Mapped[int] = mapped_column(primary_key=True)
    email: Mapped[str] = mapped_column(String(255), unique=True, index=True)
    password_hash: Mapped[str] = mapped_column(String(255))
    # "patient" or "doctor"
    role: Mapped[str] = mapped_column(String(16))
    patient_id: Mapped[int | None] = mapped_column(ForeignKey("patients.id"), unique=True)
    doctor_id: Mapped[int | None] = mapped_column(ForeignKey("doctors.id"), unique=True)
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), server_default=func.now())


class AuthSession(Base):
    """A signed-in session; only the SHA-256 hash of its bearer token is stored."""

    __tablename__ = "auth_sessions"

    id: Mapped[int] = mapped_column(primary_key=True)
    account_id: Mapped[int] = mapped_column(
        ForeignKey("user_accounts.id", ondelete="CASCADE"), index=True
    )
    token_hash: Mapped[str] = mapped_column(String(64), unique=True)
    expires_at: Mapped[datetime] = mapped_column(DateTime(timezone=True))
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), server_default=func.now())
