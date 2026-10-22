"""Train a model and run the overbooking service's own acceptance checks on it.

Nothing in ml/models/ or overbooking-service/models/ is touched unless --out says so.
`python ml/apply_decisions.py` uses this module to deliver the model chosen in docs/decisions.json.

    python ml/export_candidate.py                         # check only (temporary folder)
    python ml/export_candidate.py --model decision_tree   # decision tree instead of the forest
    python ml/export_candidate.py --out ml/models         # also write the delivery files
"""

from __future__ import annotations

import argparse
import sys
import tempfile
from datetime import date
from pathlib import Path

from build_reports import load
from export_model import export_model
from sklearn.ensemble import RandomForestClassifier
from sklearn.tree import DecisionTreeClassifier

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "overbooking-service"))

# Column names of the cleaned data -> feature names of the service (overbooking_service.features)
RENAME = {
    "LeadDays": "lead_days",
    "Weekday": "weekday",
    "Age": "age",
    "GenderMale": "gender_male",
    "Scholarship": "scholarship",
    "Hypertension": "hipertension",
    "Diabetes": "diabetes",
    "Alcoholism": "alcoholism",
    "Handicap": "handcap",
    "PriorApptCount": "prior_appt_count",
    "PriorNoShowCount": "prior_noshow_count",
}
# Defaults chosen in docs/MODEL_KARSILASTIRMA.md; docs/decisions.json can override them
DEFAULT_PARAMS = {
    "random_forest": {"n_estimators": 150, "min_samples_leaf": 20, "max_depth": 14},
    "decision_tree": {"max_depth": 4, "min_samples_leaf": 200},
}


def make_model(kind: str, params: dict | None = None):
    params = {**DEFAULT_PARAMS[kind], "random_state": 42, **(params or {})}
    if kind == "random_forest":
        return RandomForestClassifier(n_jobs=-1, **params)
    if kind == "decision_tree":
        return DecisionTreeClassifier(**params)
    raise ValueError(f"Unknown model {kind!r}; use one of {sorted(DEFAULT_PARAMS)}")


def export_and_check(kind: str, params: dict | None, version: str, out: Path | None) -> str:
    """Fit on all days, run the service's acceptance checks, optionally write the files."""
    from overbooking_service.install_model import InstallError, check_model

    df, _, _, _ = load()
    X = df[list(RENAME)].rename(columns=RENAME)
    model = make_model(kind, params).fit(X, df["NoShow"])
    version = f"{kind}-{version}"
    with tempfile.TemporaryDirectory() as tmp:
        export_model(model, list(X.columns), version, 1, Path(tmp))
        try:
            check_model(Path(tmp))
        except InstallError as exc:
            raise SystemExit(f"The service REJECTS this model:\n{exc}") from exc
        if out:
            export_model(model, list(X.columns), version, 1, out)
    return version


def main() -> int:
    ap = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawTextHelpFormatter)
    ap.add_argument("--model", choices=sorted(DEFAULT_PARAMS), default="random_forest")
    ap.add_argument("--out", type=Path, help="write model.joblib and feature_schema.json here")
    args = ap.parse_args()
    version = export_and_check(args.model, None, f"candidate-{date.today():%Y%m%d}", args.out)
    print(f"Acceptance checks of the service passed for {version}.")
    if args.out:
        print("Written to", args.out)
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
