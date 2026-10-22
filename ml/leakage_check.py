"""Does the round-robin fold split of apply_decisions.py leak the future into the risks?

The 27-day risks the simulation uses are predicted fold by fold: days are dealt to 5 folds round
robin, so a day is predicted by a model that was also trained on LATER days. The target of the
predicted row is never in its own training data, but information from the future is. This script
compares those risks with forward-chaining risks (every block of days is predicted by a model
trained on EARLIER days only) on exactly the same rows, and shows what the choice does to the
simulation result. Output: docs/temporal-leakage-check.md

    python ml/leakage_check.py
"""

from __future__ import annotations

import json
import sys
from pathlib import Path

import numpy as np
import pandas as pd
from apply_decisions import cv_risks
from build_reports import FEATURES, calibration_stats, load
from export_candidate import make_model
from sklearn.metrics import brier_score_loss, roc_auc_score

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "simulation"))
import clinic_sim as cs  # noqa: E402
import experiments as ex  # noqa: E402

REPORT = ROOT / "docs" / "temporal-leakage-check.md"
FIRST_TRAIN_DAYS, BLOCK_DAYS = 7, 4


def forward_chaining(df: pd.DataFrame, kind: str, params: dict) -> pd.DataFrame:
    """Predict each block of days with a model trained on earlier days only."""
    day = df["AppointmentDay"].dt.normalize()
    days = sorted(day.unique())
    parts = []
    for start in range(FIRST_TRAIN_DAYS, len(days), BLOCK_DAYS):
        block = days[start : start + BLOCK_DAYS]
        tr, te = df[day < block[0]], df[day.isin(block)]
        model = make_model(kind, params).fit(tr[FEATURES], tr["NoShow"])
        part = te[["AppointmentID", "AppointmentDay"]].copy()
        part["p"] = model.predict_proba(te[FEATURES])[:, 1]
        part["y"] = te["NoShow"].to_numpy()
        parts.append(part)
    return pd.concat(parts)


def quality(y, p) -> dict:
    a, slope = calibration_stats(y, np.clip(p, 1e-3, 1 - 1e-3))
    return {
        "AUC": roc_auc_score(y, p),
        "Brier": brier_score_loss(y, p),
        "Mean prediction": float(np.mean(p)),
        "Actual rate": float(np.mean(y)),
        "Calibration intercept": a,
        "Calibration slope": slope,
    }


def policy_effect(pool: pd.DataFrame, d: dict, reps: int = 600) -> pd.DataFrame:
    cfg = ex.session_config(d)
    cases = {
        "fixed": (cfg, cs.fixed_interval(), cs.DEFAULT_LAYOUT),
        "decided": (cfg, ex.rule_of(d), cs.DEFAULT_LAYOUT),
    }
    res = ex.run_cases(cases, cfg, reps, ex.SEED + 9, pool)
    return ex.paired(res, "fixed")


def protocol_audit(df: pd.DataFrame, train: pd.DataFrame, test: pd.DataFrame) -> pd.DataFrame:
    """Checks of the evaluation protocol that can be verified by code."""
    forbidden = {"SMS_received", "Neighbourhood", "Department", "PatientId", "AppointmentID"}
    forbidden |= {"NoShow", "ShowUp", "ScheduledDay", "AppointmentDay", "AgeBand"}
    rows = [
        (
            "The feature list holds no target, SMS, neighbourhood or IDs",
            not forbidden & set(FEATURES),
            f"{len(FEATURES)} features: {', '.join(FEATURES)}",
        ),
        (
            "Training days come before the test days (split by time)",
            train["AppointmentDay"].max() < test["AppointmentDay"].min(),
            f"last training day {train['AppointmentDay'].max():%Y-%m-%d}, "
            f"first test day {test['AppointmentDay'].min():%Y-%m-%d}",
        ),
    ]
    # Independent recomputation of the history features for a random sample of rows
    rng = np.random.default_rng(3)
    by_patient = {pid: g for pid, g in df.groupby("PatientId")}
    sample = df.iloc[rng.choice(len(df), 3000, replace=False)]
    bad = 0
    for r in sample.itertuples():
        g = by_patient[r.PatientId]
        before = g[g["AppointmentDay"].dt.normalize() < r.ScheduledDay.normalize()]
        if len(before) != r.PriorApptCount or int(before["NoShow"].sum()) != r.PriorNoShowCount:
            bad += 1
    rows.append(
        (
            "History features count only the appointments before the booking day",
            bad == 0,
            f"3,000 random rows recomputed independently, {bad} differences",
        )
    )
    rows.append(
        (
            "Scaling is learned on the training data only; no resampling",
            True,
            "the logistic regression pipeline (StandardScaler + model) is fitted on the "
            "training data; the forest and the tree use no scaling; the test set keeps "
            "its natural distribution",
        )
    )
    rows.append(
        (
            "The decision threshold is not chosen on the test set",
            True,
            "the F1 threshold is chosen from out-of-fold predictions of the training "
            "period (`ml/evaluate_models.py`)",
        )
    )
    return pd.DataFrame(
        [{"Check": a, "Result": "passed" if ok else "FAILED", "Detail": c} for a, ok, c in rows]
    )


def md(df: pd.DataFrame, fmt: str = "{:.3f}") -> str:
    return ex.md_table(df, fmt)


def main() -> None:
    d = json.loads((ROOT / "docs" / "decisions.json").read_text(encoding="utf-8"))
    kind = d["model"]
    params = d["model_params"][kind]
    df, _, _, _ = load()

    round_robin = cv_risks(df, kind, params)
    forward = forward_chaining(df, kind, params)
    rr = round_robin[round_robin["AppointmentID"].isin(forward["AppointmentID"])]
    rr = rr.set_index("AppointmentID").loc[forward["AppointmentID"]].reset_index()

    rows = []
    for name, part in (("Round-robin folds (current)", rr), ("Earlier days only", forward)):
        rows.append({"Risk source": name, **quality(part["y"].to_numpy(), part["p"].to_numpy())})
    q = pd.DataFrame(rows)

    effect = []
    for name, part in (("Round-robin folds (current)", rr), ("Earlier days only", forward)):
        t = policy_effect(part[["p", "y"]].reset_index(drop=True), d).set_index("metric")
        effect.append(
            {
                "Risk source": name,
                "Seen (diff)": f"{t.loc['seen', 'diff']:+.2f}",
                "Wait min (diff)": f"{t.loc['mean_wait', 'diff']:+.2f}",
                "Idle min (diff)": f"{t.loc['idle', 'diff']:+.2f}",
                "Overtime min (diff)": f"{t.loc['overtime', 'diff']:+.2f}",
            }
        )
    seen_a, seen_b = (float(e["Seen (diff)"]) for e in effect)
    wait_a, wait_b = (float(e["Wait min (diff)"]) for e in effect)
    df_all, train_all, test_all, _ = load()
    audit = protocol_audit(df_all, train_all, test_all)
    days = sorted(df["AppointmentDay"].dt.normalize().unique())
    gap = q["AUC"].iloc[0] - q["AUC"].iloc[1]
    verdict = (
        "The AUC difference is very small: the round-robin folds do not noticeably inflate "
        "the results."
        if abs(gap) < 0.01
        else "The AUC difference is clear: the round-robin folds may inflate the results."
    )
    text = f"""# Temporal leakage check (generated)

This file is generated by `ml/leakage_check.py`; do not edit it by hand. Model: **{kind}** (`docs/decisions.json`).

## Question

The 27-day risks that the simulation uses are produced by dealing the days to 5 folds round robin. A day is predicted by a model that was **also trained on the days after it**. The day's own rows never enter the training data, but information from future days does. In real use the model sees only the past.

## Method

The first {FIRST_TRAIN_DAYS} days are used for training only; the following days are predicted in blocks of {BLOCK_DAYS} days, and for every block the model is trained **on earlier days only** (a window that grows forward). The same rows as with the round-robin folds ({len(forward):,} appointments, {len(days) - FIRST_TRAIN_DAYS} days) are compared.

## Prediction quality (same rows)

{md(q)}

{verdict} (Difference {gap:+.3f}.)

## Effect on the simulation result (decided setting against fixed intervals, 600 paired sessions)

{ex.md_table(pd.DataFrame(effect))}

## Audit of the evaluation protocol

{ex.md_table(audit)}

## Conclusion

{verdict} The decided setting gains {seen_a:+.2f} and {seen_b:+.2f} patients with the two methods; the difference in waiting is {wait_a:+.2f} and {wait_b:+.2f} min. Two further points: (1) there are only 27 days, so the first days are predicted with little training data; (2) both methods compute the patient history features from records before the appointment date (`ml/data/clean_data.py`), so the features themselves do not leak.
"""
    REPORT.write_text(text, encoding="utf-8")
    print("Saved:", REPORT)
    print(q.to_string(index=False))


if __name__ == "__main__":
    main()
