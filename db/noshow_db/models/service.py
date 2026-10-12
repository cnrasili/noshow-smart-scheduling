# Overbooking service tables: predictions, decisions, reminders, A/B assignments
from datetime import date, datetime

from sqlalchemy import JSON, DateTime, String, Text, UniqueConstraint, func
from sqlalchemy.orm import Mapped, mapped_column

from noshow_db.base import Base


class Prediction(Base):
    __tablename__ = "predictions"

    id: Mapped[int] = mapped_column(primary_key=True)
    patient_id: Mapped[int] = mapped_column(index=True)
    appointment_date: Mapped[date]
    booking_date: Mapped[date]
    features: Mapped[dict] = mapped_column(JSON)
    p_noshow: Mapped[float]
    model_version: Mapped[str] = mapped_column(String(64))
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), server_default=func.now())


class BookingDecision(Base):
    __tablename__ = "booking_decisions"

    id: Mapped[int] = mapped_column(primary_key=True)
    patient_id: Mapped[int] = mapped_column(index=True)
    slot_id: Mapped[int] = mapped_column(index=True)
    booking_date: Mapped[date]
    p_noshow: Mapped[float]
    booked_p_noshow: Mapped[float | None]
    allow: Mapped[bool]
    overbook: Mapped[bool]
    reason: Mapped[str] = mapped_column(String(255))
    threshold: Mapped[float]
    model_version: Mapped[str] = mapped_column(String(64))
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), server_default=func.now())


class Message(Base):
    __tablename__ = "messages"
    # One message of each kind per appointment; also indexes appointment_id
    __table_args__ = (UniqueConstraint("appointment_id", "kind"),)

    id: Mapped[int] = mapped_column(primary_key=True)
    appointment_id: Mapped[int]
    patient_id: Mapped[int] = mapped_column(index=True)
    kind: Mapped[str] = mapped_column(String(16))
    email: Mapped[str] = mapped_column(String(255))
    subject: Mapped[str] = mapped_column(String(255))
    body: Mapped[str] = mapped_column(Text)
    appointment_start: Mapped[datetime] = mapped_column(DateTime(timezone=True))
    send_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), index=True)
    status: Mapped[str] = mapped_column(String(16), index=True)
    attempts: Mapped[int] = mapped_column(default=0)
    error: Mapped[str | None] = mapped_column(String(255))
    sent_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True))
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), server_default=func.now())


class AbAssignment(Base):
    __tablename__ = "ab_assignments"

    id: Mapped[int] = mapped_column(primary_key=True)
    appointment_id: Mapped[int] = mapped_column(unique=True)
    patient_id: Mapped[int] = mapped_column(index=True)
    group: Mapped[str] = mapped_column(String(16))
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), server_default=func.now())
