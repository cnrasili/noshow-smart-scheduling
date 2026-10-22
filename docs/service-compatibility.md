# Service compatibility report (IEN model and decisions, overbooking service)

**Aim:** to show that the model and the decided settings of the `IEN` branch work with the overbooking service, and which service tests had to change. **Limit:** this check was made on the IEN side on a **copy** of the service; the service files were not touched. It was not verified in CEN's real environment (Docker, PostgreSQL, Python 3.12); CEN repeats the commands of this report in its own environment.

## 1. How it was tried

- The service (`overbooking-service/`), the database package (`db/`) and `ml/export_model.py` were copied to a temporary folder.
- Environment: Python 3.11, scikit-learn 1.9.1, pandas 3.0.6, pytest; the service's own tests (in-memory SQLite, fake patient and slot sources).
- The model location was given with the `MODEL_DIR` environment variable (`overbooking_service/config.py` → `model_dir`).

```bash
# in the service folder (CEN environment)
MODEL_DIR=../ml/models pytest
```

## 2. Results

| Case | Result |
|---|---|
| Unchanged service, `dummy-v0` model | 150 tests passed (the environment is sound) |
| Selected random forest (`ml/models/`) | 148 passed, 2 failed: `test_predict_api.py::test_returns_probability_and_version` and `::test_prediction_is_logged` expect only `model_version == "dummy-v0"`; the API now returns `random_forest-v1` |
| Decision tree candidate (`ml/models/candidates/decision_tree/`) | The same: 148 passed, the same 2 tests failed because of `dummy-v0` |
| `config.yaml` with the decided values (`daily_overbook_limit: 4`, `service_minutes: 7.5`) and the random forest | 144 passed, 6 failed (list below) |

The model's acceptance tests (`test_model_acceptance.py`: feature schema, probability range, ordering) **passed** with both models.

## 3. Tests that CEN had to update

All of them came from old values written into the tests:

| Test | Why it failed | What to do |
|---|---|---|
| `test_predict_api.py::test_returns_probability_and_version` | Expects `dummy-v0` | Replace the expected version with the new model's version (`random_forest-v1`) or with `predictor.version` |
| `test_predict_api.py::test_prediction_is_logged` | The same | The same |
| `test_booking_api.py::test_default_rule_comes_from_config` | Expects `daily_overbook_limit == 2` | 4 |
| `test_kpi.py::test_default_settings_come_from_config` | Expects `service_minutes == 12` | 7.5 |
| `test_kpi.py::test_kpi_endpoint` | Expected values computed with a 12 min consultation time | Recompute with 7.5 min |
| `test_kpi.py::test_day_without_working_hours_falls_back_to_slots` | The same | The same |

The service code (`rules.py`, `predictor.py`) works unchanged; only `config.yaml` (two values) and these tests change.

**Update (17 October 2026).** The decided settings and the 4 related tests (`test_booking_api`, `test_kpi`) were updated on the `IEN-service-settings` branch (`config.yaml`, the service `README.md`); all 150 service tests pass with the `dummy-v0` model. The remaining 2 tests (`test_predict_api.py`) change when the model is installed (`install_model`), because the model version changes with the model.

## 4. The real model and rule through the HTTP API

The real model and the `config.yaml` rule (threshold 0.30, daily limit 4) were called through the `/predict` and `/booking-decision` endpoints. The patient and slot data were fake; the model and the rule were real.

| Call | Random forest | Decision tree |
|---|---|---|
| `/predict`: young, 3 earlier no-shows, booked 40 days ahead | p = 0.358 | p = 0.370 |
| `/predict`: elderly, 5 attended appointments, booked 1 day ahead | p = 0.118 | p = 0.186 |
| `/predict`: new patient | p = 0.346 | p = 0.370 |
| `/booking-decision`: empty slot | allowed, normal | allowed, normal |
| `/booking-decision`: the booked patient is high-risk (0.36 / 0.37 ≥ 0.30) | allowed, **overbook**, "daily overbooks 0/4" | the same |
| `/booking-decision`: the booked patient is low-risk (0.12 / 0.19 < 0.30) | **refused** | **refused** |

So `dummy-v0` goes out of use (the `model_version` in the response is the new model's name), the risk changes with the patient, and the decision changes with the risk.

## 5. What this check did not cover

- The real database (PostgreSQL), the Docker image and Python 3.12.
- The call from the web application (CEN-1) and the KPI screen (admin service), the whole chain.
- Installing the model file with the service's own `install_model` command: the acceptance checks ran on the IEN side (`ml/apply_decisions.py`); the installation step belonged to CEN.

The end-to-end check (prediction → decision → booking → KPI) was therefore left open as work together with CEN.

**Update (17 October 2026, later).** The random forest reached `main` and was installed in the service (PR #65, `94f9c93`); `dummy-v0` and `make_dummy_model.py` were removed, and `test_predict_api.py` was updated to expect the new version. The 2 failing tests of this report therefore no longer apply. The service settings (limit 4, 7.5 min) reached `main` with PR #64 the same day.
