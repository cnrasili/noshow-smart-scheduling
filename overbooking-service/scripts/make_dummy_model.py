"""Create the placeholder no-show model used until the trained model is delivered."""

import json
from pathlib import Path

import joblib
import numpy as np
from sklearn.linear_model import LogisticRegression

VERSION = "dummy-v0"
OUTPUT_DIR = Path(__file__).resolve().parents[1] / "models"

# Placeholder coefficients; lead time and prior no-shows raise the risk
COEFFICIENTS = {
    "lead_days": 0.02,
    "weekday": 0.0,
    "age": -0.01,
    "gender_male": 0.0,
    "scholarship": 0.2,
    "hipertension": -0.1,
    "diabetes": 0.0,
    "alcoholism": 0.2,
    "handcap": 0.0,
    "prior_appt_count": -0.05,
    "prior_noshow_count": 0.5,
}
INTERCEPT = -1.3


def main() -> None:
    features = list(COEFFICIENTS)

    model = LogisticRegression()
    model.classes_ = np.array([0, 1])
    model.coef_ = np.array([[COEFFICIENTS[name] for name in features]])
    model.intercept_ = np.array([INTERCEPT])
    model.n_features_in_ = len(features)

    OUTPUT_DIR.mkdir(exist_ok=True)
    joblib.dump(model, OUTPUT_DIR / "model.joblib")
    schema = {"version": VERSION, "features": features}
    (OUTPUT_DIR / "feature_schema.json").write_text(json.dumps(schema, indent=2) + "\n")


if __name__ == "__main__":
    main()
