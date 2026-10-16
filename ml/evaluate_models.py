"""Leak-free comparison of Logistic Regression, Random Forest and Decision Tree.

Protocol (written to docs/MODEL_KARSILASTIRMA.md):
- Time split: the first ~80 % of the appointment days train, the last ~20 % test (build_reports.load).
  The test set keeps its natural class distribution; nothing is rebalanced or resampled.
- Every transformation (scaling) is fitted on training rows only (it is inside the pipeline).
- Hyperparameters: expanding-window cross-validation over date blocks of the training period,
  chosen by mean validation log-loss (a proper score for calibrated risks), AUC reported beside it.
- The decision threshold is chosen on out-of-fold training predictions (maximum F1), never on the
  test set. Fixed operating thresholds 0.20 / 0.30 / 0.40 are reported too.
- Sub-groups: patients without an earlier appointment and returning patients.

    python ml/evaluate_models.py          # full run
    python ml/evaluate_models.py --quick  # tiny grid to check the code
"""

from __future__ import annotations

import argparse
import itertools
import platform
from pathlib import Path

import numpy as np
import pandas as pd
import sklearn
from build_reports import FEATURES, bootstrap_auc_ci, calibration_stats, load, r4_predict
from sklearn.ensemble import RandomForestClassifier
from sklearn.linear_model import LogisticRegression
from sklearn.metrics import (
    average_precision_score,
    brier_score_loss,
    f1_score,
    log_loss,
    precision_score,
    recall_score,
    roc_auc_score,
)
from sklearn.pipeline import make_pipeline
from sklearn.preprocessing import StandardScaler
from sklearn.tree import DecisionTreeClassifier

ROOT = Path(__file__).resolve().parents[1]
REPORT = ROOT / "docs" / "MODEL_KARSILASTIRMA.md"
CSV = Path(__file__).parent / "data" / "processed" / "model_comparison.csv"
SEED = 42
FIXED_THRESHOLDS = (0.20, 0.30, 0.40)


def make_model(name: str, params: dict):
    if name == "Logistic Regression":
        return make_pipeline(StandardScaler(), LogisticRegression(max_iter=2000, **params))
    if name == "Random Forest":
        return RandomForestClassifier(n_jobs=-1, random_state=SEED, **params)
    return DecisionTreeClassifier(random_state=SEED, **params)


def grids(quick: bool) -> dict[str, list[dict]]:
    def expand(**kw):
        keys = list(kw)
        return [dict(zip(keys, v, strict=True)) for v in itertools.product(*kw.values())]

    if quick:
        return {
            "Logistic Regression": expand(C=[1.0]),
            "Random Forest": expand(n_estimators=[30], min_samples_leaf=[50]),
            "Decision Tree": expand(max_depth=[6], min_samples_leaf=[200]),
        }
    return {
        "Logistic Regression": expand(C=[0.01, 0.1, 1.0, 10.0]),
        "Random Forest": expand(
            n_estimators=[150], min_samples_leaf=[20, 50, 100], max_depth=[8, 14]
        ),
        "Decision Tree": expand(max_depth=[4, 6, 8, 12], min_samples_leaf=[50, 200, 500]),
    }


def date_blocks(train: pd.DataFrame, n_blocks: int = 5) -> np.ndarray:
    """Block index (0..n-1) of every training row, by appointment date."""
    day = train["AppointmentDay"].dt.normalize()
    edges = day.drop_duplicates().sort_values().quantile(np.linspace(0, 1, n_blocks + 1)).to_numpy()
    return np.clip(np.searchsorted(edges[1:-1], day.to_numpy(), side="right"), 0, n_blocks - 1)


def cross_validate(name, params, train, blocks):
    """Expanding window: train on blocks < k, validate on block k (k = 1..n-1)."""
    X, y = train[FEATURES], train["NoShow"].to_numpy()
    oof = np.full(len(train), np.nan)
    ll, auc = [], []
    for k in range(1, blocks.max() + 1):
        tr, va = blocks < k, blocks == k
        m = make_model(name, params).fit(X[tr], y[tr])
        p = m.predict_proba(X[va])[:, 1]
        oof[va] = p
        ll.append(log_loss(y[va], p, labels=[0, 1]))
        auc.append(roc_auc_score(y[va], p))
    return float(np.mean(ll)), float(np.mean(auc)), oof


def best_f1_threshold(y, p) -> float:
    cand = np.unique(np.round(np.quantile(p, np.linspace(0.05, 0.95, 91)), 4))
    scores = [f1_score(y, p >= t, zero_division=0) for t in cand]
    return float(cand[int(np.argmax(scores))])


def evaluate(y, p, thresholds: dict[str, float]) -> dict:
    a, slope = calibration_stats(y, np.clip(p, 1e-3, 1 - 1e-3))
    lo, hi = bootstrap_auc_ci(y, p, n=200)
    out = {
        "n": len(y),
        "no_show_rate": float(np.mean(y)),
        "mean_risk": float(np.mean(p)),
        "ROC_AUC": roc_auc_score(y, p),
        "AUC_ci_low": lo,
        "AUC_ci_high": hi,
        "PR_AUC": average_precision_score(y, p),
        "Brier": brier_score_loss(y, p),
        "LogLoss": log_loss(y, np.clip(p, 1e-3, 1 - 1e-3)),
        "cal_intercept": a,
        "cal_slope": slope,
    }
    for label, t in thresholds.items():
        pred = p >= t
        out[f"precision@{label}"] = precision_score(y, pred, zero_division=0)
        out[f"recall@{label}"] = recall_score(y, pred, zero_division=0)
        out[f"F1@{label}"] = f1_score(y, pred, zero_division=0)
        out[f"flagged@{label}"] = float(pred.mean())
    return out


def md(df: pd.DataFrame, fmt: str = "{:.3f}") -> str:
    head = "| " + " | ".join(df.columns) + " |\n|" + "|".join("---" for _ in df.columns) + "|"
    rows = [
        "| "
        + " | ".join(fmt.format(v) if isinstance(v, float | np.floating) else str(v) for v in r)
        + " |"
        for r in df.itertuples(index=False)
    ]
    return head + "\n" + "\n".join(rows)


def main() -> None:
    ap = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawTextHelpFormatter)
    ap.add_argument("--quick", action="store_true")
    args = ap.parse_args()

    df, train, test, cut = load()
    train = train.reset_index(drop=True)
    blocks = date_blocks(train)
    y_tr, y_te = train["NoShow"].to_numpy(), test["NoShow"].to_numpy()

    chosen, cv_rows, preds, oofs = {}, [], {}, {}
    for name, grid in grids(args.quick).items():
        best = None
        for params in grid:
            ll, auc, oof = cross_validate(name, params, train, blocks)
            cv_rows.append(
                {"Model": name, "Parametreler": str(params), "CV LogLoss": ll, "CV AUC": auc}
            )
            if best is None or ll < best[0]:
                best = (ll, params, oof)
        chosen[name] = best[1]
        oofs[name] = best[2]
        model = make_model(name, best[1]).fit(train[FEATURES], y_tr)
        preds[name] = model.predict_proba(test[FEATURES])[:, 1]
        print(name, best[1])

    # baselines for reference
    r4, _ = r4_predict(train, test)
    preds["Kural R4 (referans)"] = np.asarray(r4)
    preds["Sabit oran (referans)"] = np.full(len(test), y_tr.mean())

    rows, sub_rows = [], []
    is_new = test["PriorApptCount"].to_numpy() == 0
    for name, p in preds.items():
        if name in oofs:
            mask = ~np.isnan(oofs[name])
            t_f1 = best_f1_threshold(y_tr[mask], oofs[name][mask])
        else:  # reference predictors: flag the 20 % highest risks
            t_f1 = float(np.quantile(p, 0.8))
        ths = {"F1-eşiği": t_f1, **{f"{t:.2f}": t for t in FIXED_THRESHOLDS}}
        rows.append({"Model": name, "eşik(F1)": t_f1, **evaluate(y_te, p, ths)})
        for grp, m in (("Yeni hasta (geçmişi yok)", is_new), ("Tekrar gelen hasta", ~is_new)):
            if m.sum() > 100 and len(set(y_te[m])) == 2 and name != "Sabit oran (referans)":
                sub_rows.append(
                    {"Model": name, "Grup": grp, **evaluate(y_te[m], p[m], {"0.30": 0.30})}
                )
    res = pd.DataFrame(rows)
    sub = pd.DataFrame(sub_rows)
    res.to_csv(CSV, index=False)
    write_report(res, sub, pd.DataFrame(cv_rows), chosen, train, test, cut, blocks, preds, y_te)
    print("Saved:", REPORT)


def write_report(res, sub, cv, chosen, train, test, cut, blocks, preds, y_te):
    main_cols = [
        "Model",
        "ROC_AUC",
        "AUC_ci_low",
        "AUC_ci_high",
        "PR_AUC",
        "Brier",
        "LogLoss",
        "cal_intercept",
        "cal_slope",
    ]
    a = res[main_cols].copy()
    a.columns = [
        "Model",
        "ROC-AUC",
        "AUC alt",
        "AUC üst",
        "PR-AUC",
        "Brier",
        "LogLoss",
        "Kalibrasyon kesişimi",
        "Kalibrasyon eğimi",
    ]
    # build threshold table directly from the dataframe (column names contain special characters)
    thr_rows = []
    for _, r in res.iterrows():
        for label in ("F1-eşiği", "0.20", "0.30", "0.40"):
            thr_rows.append(
                {
                    "Model": r["Model"],
                    "Eşik": f"F1-eşiği ({r['eşik(F1)']:.2f})" if label == "F1-eşiği" else label,
                    "Precision": r[f"precision@{label}"],
                    "Recall": r[f"recall@{label}"],
                    "F1": r[f"F1@{label}"],
                    "İşaretlenen pay": r[f"flagged@{label}"],
                }
            )
    thr_df = pd.DataFrame(thr_rows)
    sub_cols = [
        "Model",
        "Grup",
        "n",
        "no_show_rate",
        "mean_risk",
        "ROC_AUC",
        "Brier",
        "cal_intercept",
        "cal_slope",
    ]
    s = sub[sub_cols].copy()
    s.columns = [
        "Model",
        "Grup",
        "n",
        "Gerçek no-show",
        "Ortalama tahmin",
        "ROC-AUC",
        "Brier",
        "Kalibrasyon kesişimi",
        "Kalibrasyon eğimi",
    ]
    s["n"] = s["n"].astype(int)
    best_ll = res[~res["Model"].str.contains("referans")].sort_values("LogLoss").iloc[0]["Model"]
    ml_models = [m for m in preds if "referans" not in m]
    cal_tables = []
    for m in ml_models:
        q = pd.qcut(preds[m], 10, duplicates="drop")
        g = (
            pd.DataFrame({"p": preds[m], "y": y_te})
            .groupby(q, observed=True)
            .agg(Tahmin=("p", "mean"), Gerçek=("y", "mean"), n=("y", "size"))
            .reset_index(drop=True)
        )
        g.insert(0, "Dilim", range(1, len(g) + 1))
        cal_tables.append(f"**{m}**\n\n{md(g)}")
    text = f"""# Model karşılaştırması (otomatik üretilir)

Bu dosya `ml/evaluate_models.py` tarafından üretilir; elle düzenlemeyin. Python {platform.python_version()}, scikit-learn {sklearn.__version__}, pandas {pd.__version__}.

## 1. Değerlendirme protokolü (veri sızıntısı yok)

- **Zamana göre ayrım:** {train["AppointmentDay"].min():%d.%m.%Y} – {pd.Timestamp(cut):%d.%m.%Y} arası eğitim ({len(train):,} randevu), sonrası test ({len(test):,} randevu). Test kümesi doğal sınıf dağılımını korur; hiçbir yeniden örnekleme yapılmaz. (Literatürdeki %95 doğruluk, bölmeden önce tüm veriyi dengelemekten gelir; bkz. `docs/LITERATUR_INCELEMESI.md`.)
- **Dönüşümler yalnızca eğitimde öğrenilir:** ölçekleme boru hattının içindedir.
- **Özellikler** `docs/features.md`'ye uyar; `SMS_received` kullanılmaz. Hasta geçmişi (`PriorApptCount`, `PriorNoShowCount`) yalnızca randevu tarihi, bu randevunun alındığı günden önce olan randevulardan hesaplanır.
- **Hiperparametreler:** eğitim dönemi tarihe göre 5 bloğa bölünür; genişleyen pencereyle 4 doğrulama katı. Seçim ölçütü ortalama doğrulama log-loss'u (kalibre olasılıklar için doğru puan), AUC yanında verilir.
- **Eşik:** F1'i en yükseğe çıkaran eşik, eğitimin katlama dışı tahminlerinden seçilir; test kümesi seçime karışmaz. 0,20 / 0,30 / 0,40 sabit eşikleri de verilir.
- Test kümesindeki gerçek no-show oranı %{100 * float(np.mean(y_te)):.1f}; eğitimde %{100 * float(train["NoShow"].mean()):.1f}.

## 2. Seçilen hiperparametreler

{chr(10).join(f"- **{k}:** `{v}`" for k, v in chosen.items())}

Tüm adaylar:

{md(cv, "{:.4f}")}

## 3. Test sonuçları

{md(a)}

Log-loss ölçütüne göre en iyi model: **{best_ll}**. AUC güven aralığı 200 bootstrap ile alınmıştır. Kalibrasyon eğimi 1'e, kesişim 0'a yakınsa olasılıklar güvenilirdir; eğim 1'den küçükse tahminler fazla uçtadır.

## 4. Karar eşiği: precision, recall, F1

No-show sınıfı için (pozitif = gelmeyecek):

{md(thr_df)}

## 5. Alt gruplar (eşik 0,30)

{md(s)}

Geçmişi olmayan hastalarda hasta geçmişi özelliği bilgi taşımaz; bu grubun sonucu ayrı değerlendirilmelidir.

## 6. Kalibrasyon (onluk dilimler, test kümesi)

{(chr(10) * 2).join(cal_tables)}

## 7. Sınırlılıklar

- Tek bir zaman bölmesi kullanıldı; farklı kesim tarihleri sonucu değiştirebilir.
- Veri 27 günü kapsıyor; mevsimsellik değerlendirilemez.
- Nihai model seçimi (#7) ve operasyonel eşik (#8) bir ekip kararıdır; bu rapor veri sağlar, karar vermez.
"""
    REPORT.write_text(text, encoding="utf-8")


if __name__ == "__main__":
    main()
