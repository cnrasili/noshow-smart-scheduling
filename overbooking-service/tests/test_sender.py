import logging

import pytest

from overbooking_service.config import settings
from overbooking_service.sender import DemoSmsSender


def test_demo_sms_is_logged_for_the_patient_number(caplog: pytest.LogCaptureFixture):
    with caplog.at_level(logging.INFO):
        DemoSmsSender().send("93779.52927", "Randevunuz alındı.")
    assert "SMS to Hasta 93779.52927: Randevunuz alındı." in caplog.text


def test_default_reminder_settings_come_from_config():
    assert settings.reminders.hours_before == 24
    assert settings.reminders.max_attempts == 3
