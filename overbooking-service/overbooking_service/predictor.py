import json
import logging
from pathlib import Path
from typing import Any

import joblib
import numpy as np
import pandas as pd
import sklearn

MODEL_FILE = "model.joblib"
SCHEMA_FILE = "feature_schema.json"

logger = logging.getLogger(__name__)


class Predictor:
    """No-show model with the feature order and no-show label it was trained on."""

    def __init__(
        self, model: Any, feature_names: list[str], version: str, positive_class: Any
    ) -> None:
        n_features = getattr(model, "n_features_in_", len(feature_names))
        if n_features != len(feature_names):
            raise ValueError(
                f"Model expects {n_features} features, schema lists {len(feature_names)}"
            )

        classes = list(model.classes_)
        if positive_class not in classes:
            raise ValueError(f"Positive class {positive_class!r} is not in model classes {classes}")

        # Models trained on named columns receive a DataFrame
        names_in = getattr(model, "feature_names_in_", None)
        if names_in is not None and set(names_in) != set(feature_names):
            raise ValueError("Schema features do not match the columns the model was trained on")

        self.model = model
        self.feature_names = feature_names
        self.version = version
        self.positive_class = positive_class
        self._positive_index = classes.index(positive_class)
        self._use_frame = names_in is not None

    @classmethod
    def load(cls, model_dir: Path) -> "Predictor":
        schema = json.loads((model_dir / SCHEMA_FILE).read_text(encoding="utf-8"))
        trained_with = schema.get("sklearn_version", "")
        if trained_with.split(".")[:2] != sklearn.__version__.split(".")[:2]:
            logger.warning(
                "Model saved with scikit-learn %s, running %s", trained_with, sklearn.__version__
            )
        model = joblib.load(model_dir / MODEL_FILE)
        return cls(model, schema["features"], schema["version"], schema["positive_class"])

    def predict(self, features: dict[str, float]) -> float:
        """Return the no-show probability for one appointment."""
        missing = set(self.feature_names) - features.keys()
        extra = features.keys() - set(self.feature_names)
        if missing or extra:
            raise ValueError(
                f"Feature mismatch; missing: {sorted(missing)}, extra: {sorted(extra)}"
            )

        values = [[features[name] for name in self.feature_names]]
        if self._use_frame:
            row = pd.DataFrame(values, columns=self.feature_names)
        else:
            row = np.array(values, dtype=float)
        return float(self.model.predict_proba(row)[0][self._positive_index])
