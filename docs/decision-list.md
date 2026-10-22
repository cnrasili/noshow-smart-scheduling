# Team decision list (IEN)

This file is the **single record** of the project's decisions. The machine-readable side is `docs/decisions.json`. When a decision changes, both are updated together and `python ml/apply_decisions.py` runs; the model and the results are rebuilt (section 3). Current figures: `docs/results-summary.md`.

## 1. Current decisions

<!-- DECISIONS:BEGIN -->
| Decision | Choice | Who |
|---|---|---|
| 1. Model (#7) | Random forest (final); Decision tree for comparison under `ml/models/candidates/` | Team |
| 2. Longest mean wait | 15 min (outpatient clinic) | Team |
| 3. Rule setting (#8) | Threshold 30%, daily overbook limit 4, at most 2 patients per slot | Team |
| 4. Consultation time (#9) | Mean 7.5 min (range 5–10 min); slots of 15 min x 16 (common in Turkey; source to be added) | Team |
| 5. Single-doctor rule (#61) | Not applied; main README scope: one department, no physician named or assigned | Team |
| 5b. Unit | The department: `Department` = General Practice (in every row of the cleaned data); no physician | Team |
| 6. Reminder | Live A/B test + hypothetical scenario | Team |
| 7. Delivered rule | Threshold rule only | Team |
| 8. Model delivery | Under `ml/models/` (selected model); reached `main` with PR #65 | IEN + CEN |
| 9. Keeping the model current | CEN2 connects to the model through the API | CEN2 |
| 10. Deadline | 2026-12-16 | Team |
| 11. Simulation assumptions and the 15 min limit | Provisionally approved (2026-10-17, IEN lead); the academic justification and source (the advisor's approval) follow later | Team + advisor |
| 12. End-to-end test and final demo | Not an IEN task; separate work together with CEN | CEN |
<!-- DECISIONS:END -->

Notes and derived values:

- The **"15k" wait** was read as **15 minutes**. If that is wrong, row 2 and `wait_limit_min` have to change.
- **Slots of 15 min x 16 slots (4 hours):** team decision (17 October 2026): in Turkey the appointment interval is generally 15 minutes; a source is still to be added. The first draft derived 10 min, which was withdrawn. The mean consultation is 7.5 min (the middle of the 5–10 range). The result for 10 min slots is in the sensitivity table ("10 min slots, 24 slots"). If the slot changes, `slot_min` and `n_slots` in `docs/decisions.json` change. The web application uses the same 15 min slots, 16 a day, since #59.
- The **reminder** choice is a proposal of the IEN side and needs the team's approval.
- **Model: the random forest is final** (17 October 2026) and was handed over to CEN. The decision tree is kept for comparison only (section 2).
- **Source search (17 October 2026):** news reports and Grand National Assembly documents support the 5–10 min consultation time indirectly; **no source was found for the 15 min slot** (the MHRS interval in state hospitals is reported to be 5 min), and none for the waiting limit. The decisions stay provisionally approved and have to be discussed with the advisor.
- **The assumptions are provisionally approved (17 October 2026).** Slot length, consultation time, lateness, demand and the 15 min waiting limit are approved for now; **the academic justification and source (the advisor's approval) follow later.** Until then the reports call them "assumptions". Sources are needed for: the 5–10 min consultation time, the variability of 0.5, the lateness of 4 min, the demand (slots + 4 requests) and the 10 min slot.
- **Scope update (maintainer, 17 October 2026, main `README.md`):** the system has one department, and no physician is named or assigned; capacity and results belong to the department. This agrees with decision 5, and the simulation follows it.
- **Department level (17 October 2026):** every row of the cleaned data (`appointments_clean.xlsx`) has the column `Department` = `General Practice` (written by `ml/data/clean_data.py`; it is not a column of the dataset and not a model feature). The simulation and the IEN documents describe the department instead of physicians: a **clinic room (session)** takes the place of a "doctor"; the appointments of a day are dealt to the department's clinic rooms, and the number of rooms is an assumption.
- **The end-to-end test and the final demo are not IEN tasks;** they are separate work together with CEN (row 12).

## 2. Model files and branches

**Model:** the random forest, `ml/models/model.joblib` and `feature_schema.json` on `main` (PR #65). The service installs it (`python -m overbooking_service.install_model`). The decision tree stays under `ml/models/candidates/decision_tree/` for comparison and can be deleted.

**Branches:** new work starts on a new branch from `main`. The commits of the old `IEN` branch are in `main` (PR #62); the branch itself is not merged again.

No other model branch is needed: if the model changes, `model` is changed in `docs/decisions.json` and `python ml/apply_decisions.py` runs.

## 3. When a decision changes

1. Change the value in `docs/decisions.json` (or tell the IEN side).
2. Update the note of the decision in section 4 of `docs/decision-list.md`.
3. Run:

```bash
python ml/apply_decisions.py
```

The command predicts the 27 days with the chosen model, passes the model through the service's acceptance checks and writes it under `ml/models/`, runs the experiments again with the new settings, refreshes `docs/experiment-results.md` and `docs/results-summary.md`, and updates the decision table above. Compare the figures quoted in reports with `docs/results-summary.md`.

## 4. Decision record (question, decision, reason)

**1. Which model? (#7)** *Decision: the random forest (final, 17 October 2026).* Random forest test AUC 0.729; decision tree (4 levels) 0.720; logistic regression 0.658 (`docs/model-comparison.md`). The logistic regression was dropped. Both remaining models passed the service's acceptance checks. The random forest was handed over to CEN; the decision tree stays under `ml/models/candidates/decision_tree/` for comparison only.

**2. How long may patients wait at most?** *Decision: 15 min.* Reason: outpatient clinic conditions in Turkey. Whether the mean wait of the decided setting stays within this limit is written in the "Waiting limit check" line of `docs/results-summary.md`. Even with the mean inside the limit, some patients wait longer; `docs/waiting-time-distribution.md` reports the waits of single patients.

**3. Threshold and daily limit? (#8)** *Decision: threshold 30%, daily limit 4, at most 2 patients per slot.* The overbooking service uses these values since PR #64 (`overbooking-service/config.yaml`).

**4. Consultation time and demand? (#9)** *Decision: 5–10 min per patient (state hospital outpatient practice), mean 7.5 min.* The service uses `kpi.service_minutes` 7.5 since PR #64. The variability of 0.5, the lateness deviation of 4 min and the demand (number of slots + 4 requests) are assumptions that were not measured. Sensitivity results are produced for 5 and 10 min.

**5. The "one department, one doctor" rule (#61)?** *Decision: not applied.* The simulation keeps dealing a day's appointments to the clinic-room sessions of the department; the results are per session. The report states that "the number of clinic rooms is an assumption". The maintainer's scope of 17 October (one department, no physician named) agrees with this, and the acceptance criterion of #61 was updated to it the same day.

**6. Effect of the reminder?** *Decision (IEN proposal): live A/B test + hypothetical scenario.* The scenario (0–30% effect) is labelled clearly as an "assumption" in the report; the dataset's SMS field is not used to measure the effect.

**7. Which rule is delivered?** *Decision: the threshold rule only.* The cost-based rule and the airline rule stay in the report as comparisons.

**8. Delivering the model to the service?** *Decision:* the model is under `ml/models/` on `main` (PR #65). The models were trained with scikit-learn 1.9.1, the version the service uses (written in `feature_schema.json`); under the same conditions the test AUC was the same as with 1.2.2 (0.729 and 0.720). To retrain: `python ml/apply_decisions.py --model-only`; the service installs it with `python -m overbooking_service.install_model`.

**9. Keeping the model current in production?** *Decision:* CEN2 solves it by connecting to the model through the API; no extra work on the IEN side.

**10. Deadline and owners?** *Decision: 16 December 2026; the team moves it forward, not a single person.*

## 5. Handed over to CEN

1. **Model:** the random forest is installed on `main` (PR #65 and `94f9c93`: `ml/models/` and `overbooking-service/models/`, scikit-learn 1.9.1, `random_forest-v1`); the service's `dummy-v0` was removed.
2. **Service settings:** on `main` since PR #64 (`config.yaml`: daily limit 4, `service_minutes` 7.5; the README and the related tests were updated).
3. **The 2 tests that expected `dummy-v0`** (`tests/test_predict_api.py`) were updated by the maintainer in `94f9c93`.
4. **Rule code:** the service's `rules.decide` function and the simulation's rule make the same decision (no difference in 20,000 random slots); no code change is needed.
5. **Connecting to the model through the API (CEN2):** the feature names are in `ml/models/feature_schema.json`.
