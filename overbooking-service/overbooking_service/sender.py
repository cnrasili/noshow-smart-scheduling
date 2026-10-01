import logging
import smtplib
from email.message import EmailMessage
from typing import Protocol

from overbooking_service.config import Settings

logger = logging.getLogger(__name__)


class MessageSender(Protocol):
    """Delivers one message to a patient."""

    def send(self, to: str, subject: str, body: str) -> None: ...


class ConsoleSender:
    """Logs messages instead of sending them."""

    def send(self, to: str, subject: str, body: str) -> None:
        logger.info("Message to %s: %s\n%s", to, subject, body)


class SmtpSender:
    """Sends messages by email over SMTP."""

    def __init__(self, host: str, port: int, mail_from: str) -> None:
        self.host = host
        self.port = port
        self.mail_from = mail_from

    def send(self, to: str, subject: str, body: str) -> None:
        message = EmailMessage()
        message["From"] = self.mail_from
        message["To"] = to
        message["Subject"] = subject
        message.set_content(body)
        with smtplib.SMTP(self.host, self.port, timeout=10) as smtp:
            smtp.send_message(message)


def make_sender(settings: Settings) -> MessageSender:
    """SMTP sender when an SMTP host is set, console sender otherwise."""
    if settings.smtp_host:
        return SmtpSender(settings.smtp_host, settings.smtp_port, settings.mail_from)
    return ConsoleSender()
