"""Rebuild the model and the results from the team's decisions (docs/decisions.json).

Change a decision -> edit docs/decisions.json and docs/decision-list.md -> run this script:

1. Out-of-sample risks of the chosen model for all 27 days (grouped by day, like build_reports).
2. The chosen model is fitted on all days, checked with the overbooking service's acceptance
   checks and written to ml/models/ (model.joblib, feature_schema.json); the other model goes to
   ml/models/candidates/<model>/ so that a change of decision needs no rework.
3. simulation/experiments.py runs with the decided settings and the new risks
   (docs/experiment-results.md, docs/results-summary.md).
4. The decision table in docs/decision-list.md is refreshed from decisions.json.

    python ml/apply_decisions.py                 # everything
    python ml/apply_decisions.py --skip-model    # only results and the table
    python ml/apply_decisions.py --table-only    # only the decision table
    python ml/apply_decisions.py --model-only    # only fit and export the models (no results)
"""

from __future__ import annotations

import argparse
import json
import subprocess
import sys
from pathlib import Path

import pandas as pd
from build_reports import FEATURES, load
from export_candidate import DEFAULT_PARAMS, export_and_check, make_model
from sklearn.metrics import roc_auc_score

ROOT = Path(__file__).resolve().parents[1]
DECISIONS = ROOT / "docs" / "decisions.json"
LIST_MD = ROOT / "docs" / "decision-list.md"
RISKS = Path(__file__).parent / "data" / "processed" / "risks_decision_model.csv"
MODELS_DIR = Path(__file__).parent / "models"
BEGIN, END = "<!-- DECISIONS:BEGIN -->", "<!-- DECISIONS:END -->"
NAMES = {"random_forest": "Random forest", "decision_tree": "Decision tree"}


def cv_risks(df: pd.DataFrame, kind: str, params: dict, folds: int = 5) -> pd.DataFrame:
    """Out-of-sample risk of every appointment: days dealt to folds round-robin."""
    days = sorted(df["AppointmentDay"].dt.normalize().unique())
    fold_of = {d: i % folds for i, d in enumerate(days)}
    df = df.assign(fold=df["AppointmentDay"].dt.normalize().map(fold_of))
    parts = []
    for k in range(folds):
        tr, te = df[df.fold != k], df[df.fold == k]
        model = make_model(kind, params).fit(tr[FEATURES], tr["NoShow"])
        part = te[["AppointmentID", "AppointmentDay"]].copy()
        part["p"] = model.predict_proba(te[FEATURES])[:, 1]
        part["y"] = te["NoShow"].to_numpy()
        parts.append(part)
    return pd.concat(parts).sort_values(["AppointmentDay", "AppointmentID"])


def decision_rows(d: dict) -> list[tuple[str, str, str]]:
    chosen = d["model"]
    if chosen in NAMES:
        other = ", ".join(NAMES[k] for k in NAMES if k != chosen)
        status = {
            "final": "final",
            "alternative": "alternative branch; the selected model is the random forest, "
            "kept for comparison",
        }.get(d.get("model_status"), "provisional choice, awaiting the team's approval")
        model = f"{NAMES[chosen]} ({status}); {other} for comparison under `ml/models/candidates/`"
    else:
        model = "**Pending**"
    lo, hi = d["service_range_min"]
    a = d.get("assumptions_approval", {})
    approval = (
        f"Provisionally approved ({a.get('date', '')}, {a.get('by', '')}); {a.get('note', '')}"
        if a.get("status") == "provisional"
        else "Awaiting approval"
    )
    return [
        ("1. Model (#7)", model, "Team"),
        ("2. Longest mean wait", f"{d['wait_limit_min']} min (outpatient clinic)", "Team"),
        (
            "3. Rule setting (#8)",
            f"Threshold {round(100 * d['threshold'])}%, daily overbook limit {d['daily_limit']}, "
            f"at most {d['max_per_slot']} patients per slot",
            "Team",
        ),
        (
            "4. Consultation time (#9)",
            f"Mean {d['service_mean_min']:g} min (range {lo:g}–{hi:g} min); slots of "
            f"{d['slot_min']:g} min x {d['n_slots']} (common in Turkey; source to be added)",
            "Team",
        ),
        (
            "5. Single-doctor rule (#61)",
            (
                "Not applied; main README scope: one department, no physician named or assigned"
                if not d["single_doctor_rule"]
                else "Applied"
            ),
            "Team",
        ),
        (
            "5b. Unit",
            f"The department: `Department` = {d['department']} "
            "(in every row of the cleaned data); no physician",
            "Team",
        ),
        ("6. Reminder", "Live A/B test + hypothetical scenario", "Team"),
        ("7. Delivered rule", "Threshold rule only", "Team"),
        (
            "8. Model delivery",
            "Under `ml/models/` (selected model); reached `main` with PR #65",
            "IEN + CEN",
        ),
        ("9. Keeping the model current", "CEN2 connects to the model through the API", "CEN2"),
        ("10. Deadline", d["deadline"], "Team"),
        ("11. Simulation assumptions and the 15 min limit", approval, "Team + advisor"),
        (
            "12. End-to-end test and final demo",
            "Not an IEN task; separate work together with CEN",
            "CEN",
        ),
    ]


def update_table(d: dict) -> None:
    rows = "\n".join(f"| {a} | {b} | {c} |" for a, b, c in decision_rows(d))
    table = f"{BEGIN}\n| Decision | Choice | Who |\n|---|---|---|\n{rows}\n{END}"
    text = LIST_MD.read_text(encoding="utf-8")
    if BEGIN not in text or END not in text:
        raise SystemExit(f"{LIST_MD} has no decision-table markers")
    head, rest = text.split(BEGIN, 1)
    _, tail = rest.split(END, 1)
    LIST_MD.write_text(head + table + tail, encoding="utf-8")
    print("Updated the decision table in", LIST_MD.name)


def main() -> int:
    ap = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawTextHelpFormatter)
    ap.add_argument("--skip-model", action="store_true", help="do not retrain or export the model")
    ap.add_argument(
        "--model-only", action="store_true", help="only fit and export the models, no results"
    )
    ap.add_argument("--table-only", action="store_true", help="only refresh the decision table")
    ap.add_argument("--decisions", type=Path, default=DECISIONS)
    args = ap.parse_args()

    d = json.loads(args.decisions.read_text(encoding="utf-8"))
    update_table(d)
    if args.table_only:
        return 0
    kind = d["model"]
    if kind not in DEFAULT_PARAMS:
        print(f"docs/decisions.json: model is {kind!r}; set it to one of {sorted(DEFAULT_PARAMS)}")
        return 1
    params = d["model_params"][kind]

    if not args.skip_model:
        if not args.model_only:
            df, _, _, _ = load()
            risks = cv_risks(df, kind, params)
            risks.to_csv(RISKS, index=False)
            print(f"{NAMES[kind]}: out-of-sample AUC {roc_auc_score(risks['y'], risks['p']):.3f}")
        version = export_and_check(kind, params, d["model_version"], MODELS_DIR)
        print(f"Service acceptance checks passed; wrote {MODELS_DIR} ({version})")
        for other in DEFAULT_PARAMS:  # the other candidate, so the team can switch without rework
            if other != kind:
                folder = MODELS_DIR / "candidates" / other
                export_and_check(other, d["model_params"][other], d["model_version"], folder)
                print(f"Candidate {NAMES[other]} written to {folder}")
        if args.model_only:
            return 0
    elif not RISKS.exists():
        print("No risks file yet; run without --skip-model first")
        return 1

    cmd = [
        sys.executable,
        str(ROOT / "simulation" / "experiments.py"),
        "--decisions",
        str(args.decisions),
        "--risks",
        str(RISKS),
    ]
    subprocess.run(cmd, check=True, cwd=ROOT / "simulation")
    wait = [
        sys.executable,
        str(ROOT / "simulation" / "wait_distribution.py"),
        "--decisions",
        str(args.decisions),
        "--risks",
        str(RISKS),
    ]
    subprocess.run(wait, check=True, cwd=ROOT / "simulation")
    subprocess.run([sys.executable, str(ROOT / "simulation" / "parity_check.py")], check=False)
    print(
        "\nNext: check the numbers quoted in the reports against docs/results-summary.md, "
        "then commit."
    )
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
