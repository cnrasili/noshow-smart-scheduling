# Overbooking service tables: predictions, decisions, reminders, A/B assignments
from datetime import date, datetime

from sqlalchemy import JSON, DateTime, String, func
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
