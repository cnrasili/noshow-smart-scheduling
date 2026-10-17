from datetime import datetime
from enum import StrEnum

# Turkish names, independent of the server's locale
MONTHS = [
    "Ocak",
    "Şubat",
    "Mart",
    "Nisan",
    "Mayıs",
    "Haziran",
    "Temmuz",
    "Ağustos",
    "Eylül",
    "Ekim",
    "Kasım",
    "Aralık",
]
WEEKDAYS = ["Pazartesi", "Salı", "Çarşamba", "Perşembe", "Cuma", "Cumartesi", "Pazar"]

# Fictional hospital signing every message, and its only department
HOSPITAL_NAME = "Şehir Hastanesi"
DEPARTMENT_NAME = "Aile Hekimliği"

CANCEL_NOTE = "Gelemeyecekseniz lütfen iptal edin."


class Kind(StrEnum):
    CONFIRMATION = "confirmation"
    REMINDER = "reminder"


class Status(StrEnum):
    PENDING = "pending"
    SENT = "sent"
    FAILED = "failed"
    CANCELLED = "cancelled"
    EXPIRED = "expired"


def turkish_date_time(moment: datetime) -> str:
    """Date and time in Turkish, for example "19 Ekim 2026 Pazartesi, 13:20"."""
    return (
        f"{moment.day} {MONTHS[moment.month - 1]} {moment.year} "
        f"{WEEKDAYS[moment.weekday()]}, {moment:%H:%M}"
    )


def render(kind: Kind, appointment_start: datetime) -> str:
    """Return the SMS text of a message."""
    when = turkish_date_time(appointment_start)
    if kind is Kind.CONFIRMATION:
        sentence = f"{when} tarihli {DEPARTMENT_NAME} randevunuz alındı."
    else:
        sentence = f"{when} tarihli {DEPARTMENT_NAME} randevunuzu hatırlatırız."
    return f"{sentence} {CANCEL_NOTE} {HOSPITAL_NAME}"
