from datetime import datetime
from enum import StrEnum

CANCEL_NOTE = (
    "If you cannot attend, please cancel the appointment so that another patient can use it."
)


class Kind(StrEnum):
    CONFIRMATION = "confirmation"
    REMINDER = "reminder"


class Status(StrEnum):
    PENDING = "pending"
    SENT = "sent"
    FAILED = "failed"
    CANCELLED = "cancelled"
    EXPIRED = "expired"


def render(kind: Kind, appointment_start: datetime) -> tuple[str, str]:
    """Return the subject and body of a message."""
    when = f"{appointment_start:%d %B %Y, %H:%M}"
    if kind is Kind.CONFIRMATION:
        return "Appointment confirmed", f"Your appointment on {when} is confirmed.\n\n{CANCEL_NOTE}"
    return "Appointment reminder", f"Reminder: you have an appointment on {when}.\n\n{CANCEL_NOTE}"
