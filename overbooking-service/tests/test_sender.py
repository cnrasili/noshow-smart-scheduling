import logging
from email.message import EmailMessage

import pytest

from overbooking_service import sender as sender_module
from overbooking_service.config import settings
from overbooking_service.sender import ConsoleSender, SmtpSender, make_sender


class FakeSmtp:
    sent: list[tuple[tuple[str, int], EmailMessage]] = []

    def __init__(self, host: str, port: int, timeout: float) -> None:
        self.address = (host, port)

    def __enter__(self) -> "FakeSmtp":
        return self

    def __exit__(self, *args: object) -> None:
        pass

    def send_message(self, message: EmailMessage) -> None:
        FakeSmtp.sent.append((self.address, message))


def test_console_sender_without_smtp_host():
    sender = make_sender(settings.model_copy(update={"smtp_host": None}))
    assert isinstance(sender, ConsoleSender)


def test_smtp_sender_with_smtp_host():
    sender = make_sender(settings.model_copy(update={"smtp_host": "mailpit"}))
    assert isinstance(sender, SmtpSender)


def test_console_sender_logs_message(caplog: pytest.LogCaptureFixture):
    with caplog.at_level(logging.INFO):
        ConsoleSender().send("patient@example.com", "Subject", "Body")
    assert "patient@example.com" in caplog.text


def test_smtp_sender_builds_email(monkeypatch: pytest.MonkeyPatch):
    monkeypatch.setattr(sender_module.smtplib, "SMTP", FakeSmtp)
    SmtpSender("mailpit", 1025, "clinic@noshow.local").send(
        "patient@example.com", "Randevu hatırlatması", "Çarşamba günü randevunuz var."
    )
    address, message = FakeSmtp.sent[-1]
    assert address == ("mailpit", 1025)
    assert message["From"] == "clinic@noshow.local"
    assert message["To"] == "patient@example.com"
    # Turkish characters survive the email encoding
    assert message["Subject"] == "Randevu hatırlatması"
    assert message.get_content().strip() == "Çarşamba günü randevunuz var."
    assert "=?utf-8?" in message.as_string()


def test_smtp_sender_shows_hospital_name(monkeypatch: pytest.MonkeyPatch):
    monkeypatch.setattr(sender_module.smtplib, "SMTP", FakeSmtp)
    smtp_settings = settings.model_copy(
        update={"smtp_host": "mailpit", "mail_from": "randevu@sehirhastanesi.example"}
    )
    make_sender(smtp_settings).send("patient@example.com", "Randevunuz onaylandı", "Metin")
    _, message = FakeSmtp.sent[-1]
    sender = message["From"].addresses[0]
    assert sender.display_name == "Şehir Hastanesi"
    assert sender.addr_spec == "randevu@sehirhastanesi.example"


def test_default_reminder_settings_come_from_config():
    assert settings.reminders.hours_before == 24
    assert settings.reminders.max_attempts == 3
