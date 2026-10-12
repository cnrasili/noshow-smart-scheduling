# Clinic-wide time settings; the database triggers use the same time zone
from datetime import UTC, date, datetime
from zoneinfo import ZoneInfo

CLINIC_TZ = ZoneInfo("Europe/Istanbul")


def today() -> date:
    return datetime.now(CLINIC_TZ).date()


def as_utc(moment: datetime) -> datetime:
    """Normalize a stored datetime; SQLite drops the offset of values written in UTC."""
    return moment.astimezone(UTC) if moment.tzinfo else moment.replace(tzinfo=UTC)
