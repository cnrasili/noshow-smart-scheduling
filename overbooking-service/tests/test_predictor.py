import pytest

from overbooking_service.config import settings
from overbooking_service.predictor import Predictor


@pytest.fixture
def predictor() -> Predictor:
    return Predictor.load(settings.model_dir)


def features(predictor: Predictor, **overrides: float) -> dict[str, float]:
    values = dict.fromkeys(predictor.feature_names, 0.0)
    values.update(overrides)
    return values


def test_loads_model_and_schema(predictor: Predictor):
    assert predictor.version
    assert "lead_days" in predictor.feature_names


def test_probability_is_between_zero_and_one(predictor: Predictor):
    p = predictor.predict(features(predictor, lead_days=10, age=30))
    assert 0 <= p <= 1


def test_prior_noshows_raise_risk(predictor: Predictor):
    low = predictor.predict(features(predictor, prior_noshow_count=0))
    high = predictor.predict(features(predictor, prior_noshow_count=3))
    assert high > low


def test_missing_feature_is_rejected(predictor: Predictor):
    values = features(predictor)
    del values["lead_days"]
    with pytest.raises(ValueError, match="missing"):
        predictor.predict(values)


def test_unknown_feature_is_rejected(predictor: Predictor):
    with pytest.raises(ValueError, match="extra"):
        predictor.predict(features(predictor, sms_received=1))


def test_schema_must_match_model(predictor: Predictor):
    with pytest.raises(ValueError, match="expects"):
        Predictor(predictor.model, predictor.feature_names[:-1], "broken")
