"""Turkish texts and formats of the admin pages, independent of the server's locale."""

from datetime import UTC, date, datetime
from zoneinfo import ZoneInfo

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
SHORT_WEEKDAYS = ["Pzt", "Sal", "Çar", "Per", "Cum", "Cmt", "Paz"]

AUDIT_EVENTS = {
    "login": "Giriş",
    "login_failed": "Başarısız giriş",
    "login_locked": "Kilitli giriş denemesi",
    "logout": "Çıkış",
    "patient_created": "Hasta hesabı açıldı",
    "doctor_created": "Hekim hesabı açıldı",
    "password_reset": "Şifre sıfırlandı",
    "account_rejected": "Hesap isteği reddedildi",
}
AB_GROUPS = {"reminder": "Hatırlatma", "control": "Kontrol"}


def long_date(day: date) -> str:
    """For example "10 Kasım 2026 Salı"."""
    return f"{day.day} {MONTHS[day.month - 1]} {day.year} {WEEKDAYS[day.weekday()]}"


def date_time(moment: datetime, timezone: ZoneInfo) -> str:
    """Clinic time of a stored moment, for example "10.11.2026 09:05:31"."""
    # SQLite returns naive datetimes; they are stored in UTC
    if moment.tzinfo is None:
        moment = moment.replace(tzinfo=UTC)
    return f"{moment.astimezone(timezone):%d.%m.%Y %H:%M:%S}"


def decimal(value: float, digits: int = 1) -> str:
    """Decimal comma, for example 3,5."""
    return f"{value:.{digits}f}".replace(".", ",")


def percent(ratio: float) -> str:
    """Percent sign first, for example %60,0."""
    return f"%{decimal(ratio * 100)}"


# Account API errors from the web backend, by message
API_ERRORS = {
    "National ID number already registered": "Bu T.C. kimlik numarası zaten kayıtlı.",
    "Email already in use": "Bu e-posta adresi zaten kullanılıyor.",
    "Account already exists": "Bu hesap zaten var.",
    "Account not found": "Hesap bulunamadı.",
}
FIELDS = {
    "national_id": "T.C. kimlik numarası",
    "full_name": "Ad soyad",
    "email": "E-posta",
    "age": "Yaş",
    "gender": "Cinsiyet",
    "handcap": "Engellilik düzeyi",
    "password": "Şifre",
    "specialty": "Bölüm",
    "working_hours": "Çalışma saatleri",
    "start_time": "Başlangıç saati",
    "end_time": "Bitiş saati",
}
VALIDATION_ERRORS = {
    "Invalid national ID number": "T.C. kimlik numarası geçerli değil.",
    "Invalid email address": "E-posta adresi geçerli değil.",
    "end_time must be after start_time": "Bitiş saati başlangıç saatinden sonra olmalı.",
    "At most one working interval per weekday": (
        "Her gün için en fazla bir çalışma aralığı girilebilir."
    ),
}


def validation_error(error: dict) -> str:
    message = str(error.get("msg", ""))
    for english, turkish in VALIDATION_ERRORS.items():
        if english in message:
            return turkish
    fields = [str(part) for part in error.get("loc", []) if str(part) in FIELDS]
    label = FIELDS[fields[-1]] if fields else "Bir alan"
    return f"{label} alanındaki değer geçersiz."


def api_error(status: int, detail: object) -> str:
    """Turkish text of an error answer of the internal account API."""
    if isinstance(detail, str):
        return API_ERRORS.get(detail, f"İstek reddedildi ({status}).")
    if isinstance(detail, list) and detail:
        return " ".join(dict.fromkeys(validation_error(error) for error in detail))
    return f"İstek reddedildi ({status})."
