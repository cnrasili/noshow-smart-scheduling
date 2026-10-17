import logging
from typing import Protocol

logger = logging.getLogger(__name__)


class MessageSender(Protocol):
    """Delivers one SMS to a patient, addressed by the dataset patient number."""

    def send(self, patient_number: str, text: str) -> None: ...


class DemoSmsSender:
    """Demo SMS: no phone receives the message; the admin service shows it in its SMS inbox."""

    def send(self, patient_number: str, text: str) -> None:
        logger.info("SMS to Hasta %s: %s", patient_number, text)
