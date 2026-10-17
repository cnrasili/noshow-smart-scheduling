"""Re-run the evaluation protocol of Batool et al. (2020), "Predicting Hospital No-Shows Using Machine Learning",
on the cleaned Kaggle data and compare it with a leak-free protocol. See docs/LITERATUR_INCELEMESI.md.

This script needs imbalanced-learn, which pulls newer numpy/scikit-learn versions. Run it in a separate environment
so that the project environment is not changed:

    python -m venv paper-env
    paper-env/Scripts/pip install numpy pandas scikit-learn imbalanced-learn openpyxl
    paper-env/Scripts/python ml/paper_replication.py

It reads ml/data/processed/appointments_clean.xlsx (created by ml/data/clean_data.py).
"""

import time
import warnings
from pathlib import Path

import numpy as np
import pandas as pd
from imblearn.under_sampling import InstanceHardnessThreshold
from sklearn.ensemble import RandomForestClassifier
from sklearn.feature_selection import SelectKBest
from sklearn.metrics import accuracy_score, precision_recall_fscore_support, roc_auc_score
from sklearn.model_selection import train_test_split
from sklearn.tree import DecisionTreeClassifier

warnings.filterwarnings("ignore")
DATA = Path(__file__).parent / "data" / "processed" / "appointments_clean.xlsx"
df = pd.read_excel(DATA, sheet_name="data")
df["gender_f"] = (df["Gender"] == "F").astype(int)
df["hood"] = df["Neighbourhood"].astype("category").cat.codes
PAPER_FEATURES = [
    "gender_f",
    "Age",
    "hood",
    "Scholarship",
    "Hypertension",
    "Diabetes",
    "Alcoholism",
    "Handicap",
    "SMS_received",
    "LeadDays",
]
X, y = df[PAPER_FEATURES].to_numpy(), df["NoShow"].to_numpy()
print(
    f"records {len(df):,}, no-show rate {y.mean():.3f}; 'always predict show' accuracy = {1 - y.mean():.3f}\n"
)

t0 = time.time()
Xb, yb = InstanceHardnessThreshold(random_state=0, n_jobs=-1, cv=5).fit_resample(X, y)
print(
    f"IHT undersampling: {len(y):,} -> {len(yb):,} records, no-show share {yb.mean():.3f} ({time.time() - t0:.0f} s)"
)
print(
    f"  removed {len(y) - len(yb):,} records, all from the majority class (shows): {(1 - y).sum() - (1 - yb).sum():,}\n"
)


def report(name, y_true, y_pred, proba=None):
    p, r, f, _ = precision_recall_fscore_support(
        y_true, y_pred, average="weighted", zero_division=0
    )
    p1, r1, _, _ = precision_recall_fscore_support(
        y_true, y_pred, average="binary", zero_division=0
    )
    auc = f"  AUC {roc_auc_score(y_true, proba):.3f}" if proba is not None else ""
    print(
        f"{name:58s} acc {accuracy_score(y_true, y_pred):.3f} | weighted P/R/F1 {p:.2f}/{r:.2f}/{f:.2f} "
        f"| no-show class P {p1:.2f} R {r1:.2f}{auc}"
    )


print(
    "A) Paper protocol: IHT on ALL data first, random 80/20 split, test set is the balanced/filtered set"
)
for k, label in [(None, "all 10 features"), (1, "SelectKBest K=1")]:
    accs, kept = [], ""
    for seed in range(3):
        Xtr, Xte, ytr, yte = train_test_split(Xb, yb, test_size=0.2, random_state=seed)
        if k:
            sel = SelectKBest(k=k).fit(Xtr, ytr)
            Xtr, Xte = sel.transform(Xtr), sel.transform(Xte)
            kept = PAPER_FEATURES[int(np.argmax(sel.get_support()))]
        dt = DecisionTreeClassifier(min_samples_split=1400, random_state=0).fit(Xtr, ytr)
        accs.append(accuracy_score(yte, dt.predict(Xte)))
    report(
        f"  DT, {label}" + (f" (kept: {kept})" if k else ""),
        yte,
        dt.predict(Xte),
        dt.predict_proba(Xte)[:, 1],
    )
    print(f"    accuracy over 3 splits: {np.mean(accs):.3f}")

print(
    "\nB) Leak-free protocol: split ORIGINAL data first, IHT only on the training part, test on the natural distribution"
)
Xtr, Xte, ytr, yte = train_test_split(X, y, test_size=0.2, random_state=0, stratify=y)
Xtr_b, ytr_b = InstanceHardnessThreshold(random_state=0, n_jobs=-1, cv=5).fit_resample(Xtr, ytr)
dt = DecisionTreeClassifier(min_samples_split=1400, random_state=0).fit(Xtr_b, ytr_b)
report(
    "  DT trained on IHT-balanced train, natural test",
    yte,
    dt.predict(Xte),
    dt.predict_proba(Xte)[:, 1],
)
sel = SelectKBest(k=1).fit(Xtr_b, ytr_b)
dt1 = DecisionTreeClassifier(min_samples_split=1400, random_state=0).fit(
    sel.transform(Xtr_b), ytr_b
)
report(
    "  DT with K=1 feature, natural test",
    yte,
    dt1.predict(sel.transform(Xte)),
    dt1.predict_proba(sel.transform(Xte))[:, 1],
)
print(
    f"    mean predicted no-show probability on the natural test set: {dt.predict_proba(Xte)[:, 1].mean():.3f} (true rate {yte.mean():.3f})"
)
print(
    f"    share of patients flagged as 'no-show' (p >= 0.5): {(dt.predict_proba(Xte)[:, 1] >= 0.5).mean():.3f}; true rate {yte.mean():.3f}"
)

print("\nC) Reference: no resampling, random forest, same split")
rf = RandomForestClassifier(n_estimators=200, min_samples_leaf=50, n_jobs=-1, random_state=0).fit(
    Xtr, ytr
)
pr = rf.predict_proba(Xte)[:, 1]
report("  RF (no resampling), natural test", yte, (pr >= 0.5).astype(int), pr)
print(
    f"    mean predicted probability {pr.mean():.3f}; share with p >= 0.5: {(pr >= 0.5).mean():.4f}"
)

print("\nD) Lead-time ablation (paper Table IX), RF without resampling, natural test, AUC")
for feats, name in [
    (PAPER_FEATURES, "with lead time"),
    ([f for f in PAPER_FEATURES if f != "LeadDays"], "without lead time"),
]:
    a, b = df[feats].to_numpy(), df["NoShow"].to_numpy()
    xa, xb, ya, yb2 = train_test_split(a, b, test_size=0.2, random_state=0, stratify=b)
    m = RandomForestClassifier(
        n_estimators=200, min_samples_leaf=50, n_jobs=-1, random_state=0
    ).fit(xa, ya)
    print(f"  {name:20s} AUC {roc_auc_score(yb2, m.predict_proba(xb)[:, 1]):.3f}")

print("\nE) Neighbourhood as an extra feature, project split (train up to 2016-06-01, test after)")
ours = [
    "LeadDays",
    "Weekday",
    "Age",
    "Scholarship",
    "Hypertension",
    "Diabetes",
    "Alcoholism",
    "Handicap",
    "PriorApptCount",
    "PriorNoShowCount",
]
df["GenderMale"] = (df["Gender"] == "M").astype(int)
ours.append("GenderMale")
train, test = df[df.AppointmentDay <= "2016-06-01"], df[df.AppointmentDay > "2016-06-01"]
for feats, name in [(ours, "project features"), (ours + ["hood"], "+ neighbourhood")]:
    m = RandomForestClassifier(
        n_estimators=300, min_samples_leaf=50, n_jobs=-1, random_state=42
    ).fit(train[feats], train["NoShow"])
    print(
        f"  {name:20s} AUC {roc_auc_score(test['NoShow'], m.predict_proba(test[feats])[:, 1]):.4f}"
    )
