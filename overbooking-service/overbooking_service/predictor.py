import json
from pathlib import Path
from typing import Any

import joblib
import numpy as np

MODEL_FILE = "model.joblib"
SCHEMA_FILE = "feature_schema.json"


class Predictor:
    """No-show model with the feature order it was trained on."""

    def __init__(self, model: Any, feature_names: list[str], version: str) -> None:
        n_features = getattr(model, "n_features_in_", len(feature_names))
        if n_features != len(feature_names):
            raise ValueError(
                f"Model expects {n_features} features, schema lists {len(feature_names)}"
            )
        self.model = model
        self.feature_names = feature_names
        self.version = version

    @classmethod
    def load(cls, model_dir: Path) -> "Predictor":
        schema = json.loads((model_dir / SCHEMA_FILE).read_text(encoding="utf-8"))
        model = joblib.load(model_dir / MODEL_FILE)
        return cls(model, schema["features"], schema["version"])

    def predict(self, features: dict[str, float]) -> float:
        """Return the no-show probability for one appointment."""
        missing = set(self.feature_names) - features.keys()
        extra = features.keys() - set(self.feature_names)
        if missing or extra:
            raise ValueError(
                f"Feature mismatch; missing: {sorted(missing)}, extra: {sorted(extra)}"
            )

        row = np.array([[features[name] for name in self.feature_names]], dtype=float)
        return float(self.model.predict_proba(row)[0][1])
