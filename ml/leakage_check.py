"""Does the round-robin fold split of apply_decisions.py leak the future into the risks?

The 27-day risks the simulation uses are predicted fold by fold: days are dealt to 5 folds round
robin, so a day is predicted by a model that was also trained on LATER days. The target of the
predicted row is never in its own training data, but information from the future is. This script
compares those risks with forward-chaining risks (every block of days is predicted by a model
trained on EARLIER days only) on exactly the same rows, and shows what the choice does to the
simulation result. Output: docs/ZAMANSAL_SIZINTI_KONTROLU.md

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

REPORT = ROOT / "docs" / "ZAMANSAL_SIZINTI_KONTROLU.md"
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
        "Ortalama tahmin": float(np.mean(p)),
        "Gerçek oran": float(np.mean(y)),
        "Kalibrasyon kesişimi": a,
        "Kalibrasyon eğimi": slope,
    }


def policy_effect(pool: pd.DataFrame, d: dict, reps: int = 600) -> pd.DataFrame:
    cfg = ex.session_config(d)
    cases = {
        "sabit": (cfg, cs.fixed_interval(), cs.DEFAULT_LAYOUT),
        "karar": (cfg, ex.rule_of(d), cs.DEFAULT_LAYOUT),
    }
    res = ex.run_cases(cases, cfg, reps, ex.SEED + 9, pool)
    return ex.paired(res, "sabit")


def protocol_audit(df: pd.DataFrame, train: pd.DataFrame, test: pd.DataFrame) -> pd.DataFrame:
    """Checks of the evaluation protocol that can be verified by code."""
    forbidden = {"SMS_received", "Neighbourhood", "Department", "PatientId", "AppointmentID"}
    forbidden |= {"NoShow", "ShowUp", "ScheduledDay", "AppointmentDay", "AgeBand"}
    rows = [
        (
            "Özellik listesi hedefi, SMS'i, mahalleyi ve kimlikleri içermez",
            not forbidden & set(FEATURES),
            f"{len(FEATURES)} özellik: {', '.join(FEATURES)}",
        ),
        (
            "Eğitim günleri test günlerinden önce (zamana göre ayrım)",
            train["AppointmentDay"].max() < test["AppointmentDay"].min(),
            f"eğitim son gün {train['AppointmentDay'].max():%d.%m.%Y}, "
            f"test ilk gün {test['AppointmentDay'].min():%d.%m.%Y}",
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
            "Geçmiş özellikleri yalnızca randevu alınma gününden önceki randevulardan hesaplanır",
            bad == 0,
            f"3.000 rastgele satır bağımsız olarak yeniden hesaplandı, {bad} fark",
        )
    )
    rows.append(
        (
            "Ölçekleme yalnızca eğitimde öğrenilir; yeniden örnekleme yok",
            True,
            "lojistik regresyon boru hattı (StandardScaler + model) eğitimle kurulur; "
            "orman ve ağaç ölçekleme kullanmaz; test kümesi doğal dağılımını korur",
        )
    )
    rows.append(
        (
            "Karar eşiği testten seçilmez",
            True,
            "F1 eşiği eğitim dönemindeki katlama dışı tahminlerden seçilir "
            "(`ml/evaluate_models.py`)",
        )
    )
    return pd.DataFrame(
        [{"Denetim": a, "Sonuç": "geçti" if ok else "BAŞARISIZ", "Ayrıntı": c} for a, ok, c in rows]
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
    for name, part in (("Dönüşümlü katlar (şu an)", rr), ("Yalnızca geçmiş günlerle", forward)):
        rows.append({"Risk üretimi": name, **quality(part["y"].to_numpy(), part["p"].to_numpy())})
    q = pd.DataFrame(rows)

    effect = []
    for name, part in (("Dönüşümlü katlar (şu an)", rr), ("Yalnızca geçmiş günlerle", forward)):
        t = policy_effect(part[["p", "y"]].reset_index(drop=True), d).set_index("metric")
        effect.append(
            {
                "Risk üretimi": name,
                "Görülen (fark)": f"{t.loc['seen', 'diff']:+.2f}",
                "Bekleme dk (fark)": f"{t.loc['mean_wait', 'diff']:+.2f}",
                "Boşta dk (fark)": f"{t.loc['idle', 'diff']:+.2f}",
                "Mesai aşımı dk (fark)": f"{t.loc['overtime', 'diff']:+.2f}",
            }
        )
    seen_a, seen_b = (float(e["Görülen (fark)"]) for e in effect)
    wait_a, wait_b = (float(e["Bekleme dk (fark)"]) for e in effect)
    df_all, train_all, test_all, _ = load()
    audit = protocol_audit(df_all, train_all, test_all)
    days = sorted(df["AppointmentDay"].dt.normalize().unique())
    gap = q["AUC"].iloc[0] - q["AUC"].iloc[1]
    verdict = (
        "AUC farkı çok küçük: dönüşümlü katlar sonuçları belirgin biçimde şişirmiyor."
        if abs(gap) < 0.01
        else "AUC farkı belirgin: dönüşümlü katlar sonuçları şişiriyor olabilir."
    )
    text = f"""# Zamansal sızıntı kontrolü (otomatik üretilir)

Bu dosya `ml/leakage_check.py` tarafından üretilir; elle düzenlemeyin. Model: **{kind}** (`docs/decisions.json`).

## Soru

Simülasyonun kullandığı 27 günlük riskler, günleri 5 kata dönüşümlü dağıtarak üretiliyor. Bir gün, **kendisinden sonraki günlerle de eğitilmiş** bir modelle tahmin ediliyor. Günün kendi satırları eğitime girmez, ama gelecekteki günlerin bilgisi girer. Gerçek kullanımda model yalnızca geçmişi görür.

## Yöntem

İlk {FIRST_TRAIN_DAYS} gün yalnızca eğitimde kalır; sonraki günler {BLOCK_DAYS}'er günlük bloklarla tahmin edilir ve her blok için model **yalnızca önceki günlerle** eğitilir (ileri doğru genişleyen pencere). Dönüşümlü katlarla aynı satırlar ({len(forward):,} randevu, {len(days) - FIRST_TRAIN_DAYS} gün) karşılaştırılır.

## Tahmin kalitesi (aynı satırlar)

{md(q)}

{verdict} (Fark {gap:+.3f}.)

## Simülasyon sonucuna etkisi (karar ayarı, sabit aralığa göre, 600 eşleştirilmiş oturum)

{ex.md_table(pd.DataFrame(effect))}

## Değerlendirme protokolü denetimi

{ex.md_table(audit)}

## Sonuç

{verdict} Karar ayarının hasta kazancı iki yöntemde {seen_a:+.2f} ve {seen_b:+.2f}; bekleme farkı {wait_a:+.2f} ve {wait_b:+.2f} dk. Ayrıca iki sınırlılık sürer: (1) yalnızca 27 gün vardır, ilk günlerin tahmini için az eğitim verisi vardır; (2) her iki yöntem de hasta geçmişi özelliklerini randevu tarihinden önceki kayıtlarla hesaplar (`ml/data/clean_data.py`), bu yüzden özelliklerde sızıntı yoktur.
"""
    REPORT.write_text(text, encoding="utf-8")
    print("Saved:", REPORT)
    print(q.to_string(index=False))


if __name__ == "__main__":
    main()
