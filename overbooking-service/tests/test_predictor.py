import sys
from pathlib import Path

import numpy as np
import pandas as pd
import pytest
from sklearn.compose import ColumnTransformer
from sklearn.linear_model import LogisticRegression
from sklearn.pipeline import Pipeline
from sklearn.preprocessing import StandardScaler

from overbooking_service.config import settings
from overbooking_service.predictor import Predictor

sys.path.insert(0, str(Path(__file__).resolve().parents[2] / "ml"))
from export_model import export_model  # noqa: E402

NAMES = ["lead_days", "prior_noshow_count"]
X = np.array([[0, 0], [1, 0], [30, 2], [40, 3], [2, 0], [50, 1]], dtype=float)


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
        Predictor(predictor.model, predictor.feature_names[:-1], "broken", 1)


def test_string_labels_use_the_no_show_column():
    y = np.array(["No", "No", "Yes", "Yes", "No", "Yes"])
    model = LogisticRegression().fit(X, y)
    predictor = Predictor(model, NAMES, "test", positive_class="Yes")

    row = {"lead_days": 40.0, "prior_noshow_count": 3.0}
    expected = model.predict_proba(np.array([[40.0, 3.0]]))[0][list(model.classes_).index("Yes")]
    assert predictor.predict(row) == pytest.approx(expected)


def test_unknown_positive_class_is_rejected():
    model = LogisticRegression().fit(X, np.array([0, 0, 1, 1, 0, 1]))
    with pytest.raises(ValueError, match="Positive class"):
        Predictor(model, NAMES, "test", positive_class="Yes")


def test_model_trained_on_named_columns():
    frame = pd.DataFrame(X, columns=NAMES)
    model = Pipeline(
        [
            ("scale", ColumnTransformer([("num", StandardScaler(), NAMES)])),
            ("clf", LogisticRegression()),
        ]
    ).fit(frame, np.array([0, 0, 1, 1, 0, 1]))
    predictor = Predictor(model, NAMES, "test", positive_class=1)

    p = predictor.predict({"lead_days": 40.0, "prior_noshow_count": 3.0})
    assert 0 <= p <= 1


def test_export_round_trip(tmp_path: Path):
    model = LogisticRegression().fit(X, np.array([0, 0, 1, 1, 0, 1]))
    export_model(model, NAMES, "test-v1", positive_class=np.int64(1), output_dir=tmp_path)

    loaded = Predictor.load(tmp_path)
    assert loaded.version == "test-v1"
    assert loaded.positive_class == 1


def test_export_rejects_wrong_positive_class(tmp_path: Path):
    model = LogisticRegression().fit(X, np.array([0, 0, 1, 1, 0, 1]))
    with pytest.raises(ValueError, match="Positive class"):
        export_model(model, NAMES, "test", positive_class="Yes", output_dir=tmp_path)
