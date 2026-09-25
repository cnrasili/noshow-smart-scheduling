"""Export a trained no-show model in the format the overbooking service loads."""

import json
from pathlib import Path
from typing import Any

import joblib
import sklearn

MODEL_FILE = "model.joblib"
SCHEMA_FILE = "feature_schema.json"


def export_model(
    model: Any,
    feature_names: list[str],
    version: str,
    positive_class: Any,
    output_dir: Path,
) -> None:
    """Save a fitted classifier and its feature schema.

    positive_class is the label that means "no-show" in the training data.
    """
    classes = list(getattr(model, "classes_", []))
    if positive_class not in classes:
        raise ValueError(f"Positive class {positive_class!r} is not in model classes {classes}")

    n_features = getattr(model, "n_features_in_", len(feature_names))
    if n_features != len(feature_names):
        raise ValueError(f"Model expects {n_features} features, got {len(feature_names)} names")

    names_in = getattr(model, "feature_names_in_", None)
    if names_in is not None and set(names_in) != set(feature_names):
        raise ValueError("Feature names do not match the columns the model was trained on")

    # NumPy scalars are not JSON serializable
    label = positive_class.item() if hasattr(positive_class, "item") else positive_class

    output_dir.mkdir(parents=True, exist_ok=True)
    joblib.dump(model, output_dir / MODEL_FILE)
    schema = {
        "version": version,
        "features": list(feature_names),
        "positive_class": label,
        "sklearn_version": sklearn.__version__,
    }
    (output_dir / SCHEMA_FILE).write_text(json.dumps(schema, indent=2) + "\n", encoding="utf-8")
