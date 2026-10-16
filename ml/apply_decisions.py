"""Rebuild the model and the results from the team's decisions (docs/decisions.json).

Change a decision -> edit docs/decisions.json and docs/KARAR_LISTESI.md -> run this script:

1. Out-of-sample risks of the chosen model for all 27 days (grouped by day, like build_reports).
2. The chosen model is fitted on all days, checked with the overbooking service's acceptance
   checks and written to ml/models/ (model.joblib, feature_schema.json).
3. simulation/experiments.py runs with the decided settings and the new risks
   (docs/IEN_DENEY_SONUCLARI.md, docs/SONUC_OZETI.md).
4. The decision table in docs/KARAR_LISTESI.md is refreshed from decisions.json.

    python ml/apply_decisions.py                 # everything
    python ml/apply_decisions.py --skip-model    # only results and the table
    python ml/apply_decisions.py --table-only    # only the decision table
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
LIST_MD = ROOT / "docs" / "KARAR_LISTESI.md"
RISKS = Path(__file__).parent / "data" / "processed" / "risks_decision_model.csv"
MODELS_DIR = Path(__file__).parent / "models"
BEGIN, END = "<!-- KARARLAR:BASLA -->", "<!-- KARARLAR:BITIS -->"
NAMES = {"random_forest": "Rastgele orman", "decision_tree": "Karar ağacı"}


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
    model = NAMES.get(d["model"], "**Bekliyor** (iki dal: IEN-RandomForest, IEN-DecisionTree)")
    lo, hi = d["service_range_min"]
    return [
        ("1. Model (#7)", model, "Ekip"),
        ("2. En uzun ortalama bekleme", f"{d['wait_limit_min']} dk (poliklinik)", "Ekip"),
        (
            "3. Kural ayarı (#8)",
            f"Eşik %{round(100 * d['threshold'])}, günlük ek randevu sınırı {d['daily_limit']}, "
            f"slot başına en çok {d['max_per_slot']} hasta",
            "Ekip",
        ),
        (
            "4. Muayene süresi (#9)",
            f"Ortalama {d['service_mean_min']:g} dk (aralık {lo:g}–{hi:g} dk); "
            f"slot {d['slot_min']:g} dk x {d['n_slots']} (türetilmiş)",
            "Ekip",
        ),
        (
            "5. Tek doktor kuralı (#61)",
            "Uygulanmayacak" if not d["single_doctor_rule"] else "Uygulanacak",
            "Ekip",
        ),
        ("6. Hatırlatma", "Canlı A/B testi + varsayımsal senaryo", "Ekip"),
        ("7. Teslim edilen kural", "Yalnızca eşik kuralı", "Ekip"),
        (
            "8. Modelin teslimi",
            "`ml/models/` altında, seçilen dalda; CEN o dalı çeker",
            "IEN + CEN",
        ),
        ("9. Canlıda güncel kalma", "CEN2 modele API ile bağlanır", "CEN2"),
        ("10. Son tarih", d["deadline"], "Ekip"),
    ]


def update_table(d: dict) -> None:
    rows = "\n".join(f"| {a} | {b} | {c} |" for a, b, c in decision_rows(d))
    table = f"{BEGIN}\n| Karar | Seçim | Kim |\n|---|---|---|\n{rows}\n{END}"
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
        df, _, _, _ = load()
        risks = cv_risks(df, kind, params)
        risks.to_csv(RISKS, index=False)
        print(f"{NAMES[kind]}: out-of-sample AUC {roc_auc_score(risks['y'], risks['p']):.3f}")
        version = export_and_check(kind, params, d["model_version"], MODELS_DIR)
        print(f"Service acceptance checks passed; wrote {MODELS_DIR} ({version})")
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
    subprocess.run([sys.executable, str(ROOT / "simulation" / "parity_check.py")], check=False)
    print(
        "\nNext: check the numbers quoted in docs/IEN_RAPOR_TASLAGI.md and "
        "docs/DEMO_VE_JURI_HAZIRLIGI.md against docs/SONUC_OZETI.md, then commit."
    )
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
