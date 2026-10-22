# Reproduction guide

Aim: anyone in the team can produce the IEN results from scratch on their own computer and compare them with the figures written here. Time: about 15 minutes. Every reproduction is added to the table at the bottom.

**What does a clean result mean?** The random numbers use fixed seeds, so the results come out the same. With other library versions, differences may appear only in the third decimal (for example a calibration slope of 1.103 → 1.102) and in the order of rows with equal values. Note any other difference.

## 0. Preparation

- Python 3.11 or later, Git.
- Clone the repository; the IEN work is on `main` (PR #62).

```bash
git clone https://github.com/cnrasili/noshow-smart-scheduling.git
cd noshow-smart-scheduling
git log -1 --format=%H        # write it into the table below
```

- Set up a new virtual environment (do not use an existing one):

```bash
python -m venv ien-env
ien-env\Scripts\activate       # Linux/macOS: source ien-env/bin/activate
pip install -r ml/requirements.txt -r simulation/requirements.txt
pip install pydantic pydantic-settings pyyaml   # for the service's acceptance checks of the model
```

The data comes with the repository in `ml/data/raw/KaggleV2-May-2016.csv`; there is nothing to download.

## 1. Steps and expected values

Compare the output of every step with the values below.

### 1.1 Data cleaning

```bash
python ml/data/clean_data.py
```

| Expected |
|---|
| Raw rows 110527, Clean rows 110521 (5 appointments "before booking" and 1 negative age removed) |
| No-show rate 0.2019 |
| Appointment date range 2016-04-29 to 2016-06-08 |
| Unique patients 62298 |
| Department (every row) General Practice |

### 1.2 Reports and risks per day

```bash
cd ml
python build_reports.py
```

| Expected (test set) | AUC | Brier | LogLoss |
|---|---|---|---|
| LogisticRegression | 0.6576 | 0.1451 | 0.461 |
| RandomForest | 0.7296 | 0.1361 | 0.4233 |
| R4_rules | 0.5767 | 0.1499 | 0.475 |

Last lines: `All-days out-of-sample risks: 110521 appointments, 27 days, AUC RF 0.728, LR 0.663, R4 0.572, paper-style 0.719`.

### 1.3 Model comparison (leak-free protocol)

```bash
python evaluate_models.py          # in ml/; about 5 minutes
```

`docs/model-comparison.md` is refreshed. Expected: selected hyperparameters logistic `C=0.01`, forest `n_estimators=150, min_samples_leaf=20, max_depth=14`, tree `max_depth=4, min_samples_leaf=200`; test ROC-AUC forest 0.729 (confidence interval 0.721–0.736), tree 0.720, logistic 0.658.

### 1.4 Model delivery, experiments and waiting distribution

```bash
python apply_decisions.py          # in ml/; about 3 minutes
```

| Expected output line |
|---|
| `Random forest: out-of-sample AUC 0.728` |
| `Service acceptance checks passed ... (random_forest-v1)` (the service's acceptance checks) |
| `20000 random slots compared: 0 differences` (the service rule and the simulation rule decide the same) |

Since PR #64 the parity check prints `ok` for the service settings `daily_overbook_limit` and `service_minutes`; before it, `DIFFERS` appeared there.

`docs/results-summary.md` (per session, decided setting threshold 30% / limit 4, against no rule):

| Measure | No rule | Decided setting | Difference [95% interval] |
|---|---|---|---|
| Patients seen | 12.81 | 15.60 | +2.78 [+2.74; +2.82] |
| Mean wait (min) | 0.22 | 1.13 | +0.91 [+0.87; +0.95] |
| Idle time (min) | 144.07 | 123.66 | −20.42 [−20.82; −20.01] |
| Overtime (min) | 0.25 | 0.46 | +0.22 [+0.12; +0.31] |
| Utilization | 0.40 | 0.49 | +0.09 |

`docs/waiting-time-distribution.md`: under the rule 0.82% of the patients wait longer than 15 min; in 8.7% of the sessions at least one patient waits longer than 15 min; the rule sees 2.79 extra patients per session at a cost of +15.0 patient-minutes of waiting in total (about 5.4 min per extra patient).

> `apply_decisions.py` rewrites the model files under `ml/models/`. If you do not want to put them back into the repository, restore them with `git checkout -- ml/models` or `git restore ml/models`; do not commit a file trained with another scikit-learn version.

### 1.5 Temporal leakage check

```bash
python leakage_check.py            # in ml/
```

Expected (`docs/temporal-leakage-check.md`): AUC 0.731 with round-robin folds, 0.729 with earlier days only; all five items of the protocol audit "passed".

### 1.6 Optional: all result pages and the service tests

```bash
cd ../simulation
python main.py --no-open           # about 90 seconds; writes pages under simulation/output/
python parity_check.py             # the service rule against the simulation rule
```

The service tests (`overbooking-service/`) are expected to pass (146 tests on 22 October 2026). They need the service's own dependencies (FastAPI, SQLAlchemy, pytest) and the `overbooking-service`, `db` and `ml` folders on the `PYTHONPATH` (details: `docs/service-compatibility.md`).

## 2. Comparing the generated files

After the steps:

```bash
git status --short docs ml
git diff --stat docs
```

- `docs/results-summary.md` and `docs/waiting-time-distribution.md` should **not change at all** (or only in the version line).
- `docs/model-comparison.md` and `docs/experiment-results.md` may change only in the third decimal and in the order of equal rows.
- Any other difference means a problem: write the versions and the difference into the table below.

To clean up the files: `git restore docs ml/models`.

## 3. Reproduction records

Earlier reproduction: 17 October 2026, `IEN` branch, Windows, Python 3.11.2, pandas 3.0.6, numpy 2.4.6, scikit-learn 1.9.1, scipy 1.17.1, simpy 4.1.2 (new virtual environment, same computer). Result: the results summary and the waiting distribution exactly the same; the others different in the third decimal.

| Date | Person | Operating system | Python / pandas / scikit-learn | Commit (short) | Result (matches / differs) | Note |
|---|---|---|---|---|---|---|
| 2026-10-22 | Project manager | Windows 11 | 3.11.9 / 3.0.6 / 1.9.1 | `c052a80` | Matches: the results summary, the waiting distribution and the experiment results are exactly the same; the model comparison (21 values) and the temporal leakage check (1 value) differ in the third decimal | The reports were regenerated in English by the translated scripts; the model files came out unchanged |
| | | | | | | |
