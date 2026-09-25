"""Acceptance checks for the model in models/; every delivered model must pass them."""

from datetime import date, timedelta

import pytest

from overbooking_service.config import settings
from overbooking_service.features import PastAppointment, PatientRecord, build_features
from overbooking_service.predictor import Predictor

BOOKING = date(2026, 11, 2)


@pytest.fixture(scope="module")
def predictor() -> Predictor:
    return Predictor.load(settings.model_dir)


def patient(age: int) -> PatientRecord:
    return PatientRecord(1, age, "F", False, False, False, False, 0)


def history(appointments: int, no_shows: int) -> list[PastAppointment]:
    return [
        PastAppointment(BOOKING - timedelta(days=30 * (i + 1)), attended=i >= no_shows)
        for i in range(appointments)
    ]


def test_schema_matches_computed_features(predictor: Predictor):
    computed = build_features(patient(30), [], BOOKING, BOOKING)
    assert set(predictor.feature_names) == set(computed)


def test_probabilities_are_valid(predictor: Predictor):
    for age in (5, 30, 70):
        for lead in (0, 7, 60):
            for no_shows in (0, 2):
                features = build_features(
                    patient(age), history(3, no_shows), BOOKING + timedelta(days=lead), BOOKING
                )
                assert 0 <= predictor.predict(features) <= 1


def test_high_risk_profiles_score_higher(predictor: Predictor):
    ages = (20, 40, 60)
    low = [
        predictor.predict(build_features(patient(a), history(5, 0), BOOKING, BOOKING)) for a in ages
    ]
    high = [
        predictor.predict(
            build_features(patient(a), history(3, 3), BOOKING + timedelta(days=60), BOOKING)
        )
        for a in ages
    ]
    assert sum(high) / len(high) > sum(low) / len(low)
