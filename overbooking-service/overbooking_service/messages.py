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

# Fictional hospital shown as the sender and at the end of every message
HOSPITAL_NAME = "Şehir Hastanesi"

CANCEL_NOTE = (
    "Randevunuza gelemeyecekseniz lütfen iptal edin; böylece randevu saati başka bir hastaya "
    "verilebilir."
)
ARRIVAL_NOTE = "Lütfen randevu saatinden 15 dakika önce poliklinik bankosuna başvurun."


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


def render(kind: Kind, appointment_start: datetime) -> tuple[str, str]:
    """Return the subject and body of a message."""
    when = turkish_date_time(appointment_start)
    if kind is Kind.CONFIRMATION:
        return (
            "Randevunuz onaylandı",
            f"{when} tarihli randevunuz onaylandı.\n\n{CANCEL_NOTE}\n\n{HOSPITAL_NAME}",
        )
    return (
        "Randevu hatırlatması",
        f"Hatırlatma: {when} tarihinde randevunuz var. {ARRIVAL_NOTE}\n\n{CANCEL_NOTE}"
        f"\n\n{HOSPITAL_NAME}",
    )
