"""Acceptance checks for the model in models/; every delivered model must pass them."""

import pytest

from overbooking_service.config import settings
from overbooking_service.model_checks import (
    feature_problems,
    probability_problems,
    ranking_problems,
)
from overbooking_service.predictor import Predictor


@pytest.fixture(scope="module")
def predictor() -> Predictor:
    return Predictor.load(settings.model_dir)


def test_schema_matches_computed_features(predictor: Predictor):
    assert feature_problems(predictor) == []


def test_probabilities_are_valid(predictor: Predictor):
    assert probability_problems(predictor) == []


def test_high_risk_profiles_score_higher(predictor: Predictor):
    assert ranking_problems(predictor) == []
