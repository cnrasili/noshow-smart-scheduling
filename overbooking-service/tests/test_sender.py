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
        "patient@example.com", "Appointment reminder", "Body"
    )
    address, message = FakeSmtp.sent[-1]
    assert address == ("mailpit", 1025)
    assert message["From"] == "clinic@noshow.local"
    assert message["To"] == "patient@example.com"
    assert message["Subject"] == "Appointment reminder"
    assert message.get_content().strip() == "Body"


def test_default_reminder_settings_come_from_config():
    assert settings.reminders.hours_before == 24
    assert settings.reminders.max_attempts == 3
