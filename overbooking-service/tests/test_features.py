from datetime import date

import pytest

from overbooking_service.features import PastAppointment, PatientRecord, build_features

PATIENT = PatientRecord(1, 45, "M", True, False, True, False, 1)


def test_lead_days_and_weekday():
    features = build_features(PATIENT, [], date(2026, 11, 10), date(2026, 11, 2))
    assert features["lead_days"] == 8
    assert features["weekday"] == 1  # Tuesday


def test_patient_attributes():
    features = build_features(PATIENT, [], date(2026, 11, 10), date(2026, 11, 2))
    assert features["age"] == 45
    assert features["gender_male"] == 1
    assert features["scholarship"] == 1
    assert features["diabetes"] == 1
    assert features["handcap"] == 1


def test_history_uses_only_appointments_before_booking():
    history = [
        PastAppointment(date(2026, 9, 1), attended=False),
        PastAppointment(date(2026, 10, 1), attended=True),
        # Outcome not known yet at booking time
        PastAppointment(date(2026, 11, 5), attended=False),
    ]
    features = build_features(PATIENT, history, date(2026, 11, 10), date(2026, 11, 2))
    assert features["prior_appt_count"] == 2
    assert features["prior_noshow_count"] == 1


def test_same_day_booking_is_allowed():
    features = build_features(PATIENT, [], date(2026, 11, 2), date(2026, 11, 2))
    assert features["lead_days"] == 0


def test_appointment_before_booking_is_rejected():
    with pytest.raises(ValueError):
        build_features(PATIENT, [], date(2026, 11, 1), date(2026, 11, 2))
