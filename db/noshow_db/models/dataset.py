# Appointment history of the public no-show dataset
from datetime import date, datetime

from sqlalchemy import DateTime, ForeignKey
from sqlalchemy.orm import Mapped, mapped_column

from noshow_db.base import Base


class DatasetAppointment(Base):
    """A past appointment from the public dataset; it has a day but no slot or time.

    Bookings made in the application are stored in appointments with their slots.
    """

    __tablename__ = "dataset_appointments"

    id: Mapped[int] = mapped_column(primary_key=True)
    # AppointmentID in the dataset
    appointment_number: Mapped[int] = mapped_column(unique=True)
    patient_id: Mapped[int] = mapped_column(ForeignKey("patients.id"), index=True)
    # ScheduledDay: when the appointment was booked
    booked_at: Mapped[datetime] = mapped_column(DateTime(timezone=True))
    # AppointmentDay
    appointment_date: Mapped[date]
    # False when the dataset marks the appointment as a no-show
    attended: Mapped[bool]
    sms_received: Mapped[bool]
