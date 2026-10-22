# KPI and assumption comparison

This document answers two questions: (1) do the KPIs of the simulation measure the same thing as the application's KPI screen, and (2) which values in the simulation are **measured**, which are **decisions** and which are **assumptions**. The decisions are in `docs/decision-list.md` and `docs/decisions.json`; the figures come from `docs/experiment-results.md` and `docs/results-summary.md`.

## 1. KPI definitions: simulation and application

The definitions follow `docs/kpi-definitions.md` and are the same on both sides. The way they are computed differs:

| KPI | Simulation (`simulation/clinic_sim.py`) | Application (`GET /kpi`, `docs/api-contract.md`) | What the difference does |
|---|---|---|---|
| Wait | Start of the consultation − max(appointment time, patient's arrival); arrivals vary with real lateness | Patients are assumed to **arrive on time**; consultation start and end are not recorded | The application sees only the waiting caused by the queue; the effect of lateness in the simulation is invisible |
| Consultation time | Log-normal, mean 7.5 min (range 5–10 min), variability 0.5 | A fixed time, `kpi.service_minutes` (7.5 in the service since PR #64) | Variability raises waiting and overtime; a fixed time shows them smaller |
| Idle time | Minutes without a patient within the session | Same definition, with fixed-time patients | Similar; the difference comes from the consultation time |
| Overtime | End of the last consultation − end of the session | Same definition, with fixed-time patients | Same |
| Utilization | Busy time ÷ session length | Same definition | Same |
| Session length | 16 slots x 15 min = 240 min | First slot start – last slot end, or the working hours (`kpi.session`) | Depends on the slot template chosen |

**Conclusion.** Both sides use the same definitions, but the application measures more optimistically (patients on time, a fixed consultation time). If the report puts simulation and application figures side by side, this difference has to be stated. The only "measured" values are the number of patients and the no-show rate from the `attended` records of the application; waiting, idle time and overtime are **model outputs** on both sides, not direct measurements.

## 2. Measured, decision and assumption

| Value | Status | Source | Note |
|---|---|---|---|
| No-show risk | **Measured** (predicted on the 27 days the model did not see) | `ml/data/processed/` | Evaluation split by time (`docs/model-comparison.md`) |
| Show-up / no-show | **Measured** (110,521 real appointments) | Kaggle data | — |
| Consultation time 5–10 min, mean 7.5 min | **Decision** (team) | Turkish state hospital outpatient practice | Source to be added `[APPROVAL]` |
| Threshold 30%, daily limit 4 | **Decision** (team) | `decisions.json` | — |
| Longest mean wait 15 min | **Decision** (team) | `decisions.json` | — |
| Slots of 15 min, 16 slots (4 hours) | **Decision** (team; in Turkey the appointment interval is generally 15 min) | `decisions.json` | Source to be added `[APPROVAL]`; a sensitivity row exists for 10 min slots |
| Consultation variability 0.5 | Assumption | `SessionConfig` | Durations are right-skewed; a source is needed |
| Lateness deviation 4 min | Assumption | `SessionConfig` | The dataset has no arrival times; it cannot be measured |
| Demand: number of slots + 4 requests (20) | Assumption | `SessionConfig` | The data has no times, so the daily demand cannot be related to the slots |
| Number of clinic rooms (sessions) | Decision: the single-doctor rule is **not applied**; the system is one department (General Practice) | #61 | A day's appointments are dealt to the department's clinic-room sessions; results are per session, and the number of rooms is an assumption |
| Reminder effect | **Not measured**; scenario only | `experiments.py` | A real A/B test is needed; `SMS_received` is not a randomised experiment |

## 3. Service and simulation settings

`simulation/parity_check.py` shows that the service's `rules.decide` function and the simulation's threshold rule make **the same decision** in 20,000 random slots (difference 0). After the decision list, the settings were compared as follows; the command prints the differences:

| Setting | Service (`config.yaml`) | Decision |
|---|---|---|
| Threshold | 0.30 | 0.30 |
| Daily overbook limit | 4 | 4 |
| Consultation time (`kpi.service_minutes`) | 7.5 min | 7.5 min |

The service has used the decided values since PR #64 (17 October 2026); before that, the limit was 2 and the consultation time 12 min.

## 4. Sensitivity: how much does each assumption change the result?

The current table is in section 4 of `docs/experiment-results.md` (difference of the decided setting from fixed intervals). With the random forest (600 paired sessions):

| Assumption | Seen | Wait (min) | Idle (min) | Overtime (min) |
|---|---|---|---|---|
| Base (7.5 min, 15 min slots) | +2.76 | +0.95 | −20.7 | +0.27 |
| Consultation 5 min | +2.76 | +0.41 | −14.3 | 0.00 |
| Consultation 10 min | +2.76 | +2.18 | −26.7 | +1.14 |
| Variability 0.3 | +2.76 | +0.78 | −20.7 | +0.10 |
| Variability 0.8 | +2.76 | +1.37 | −20.8 | +0.63 |
| Demand 16 requests (= number of slots) | +0.00 | +0.96 | −0.4 | −0.36 |
| Demand 24 requests | +2.76 | +0.91 | −21.0 | +0.24 |
| Lateness deviation 8 min | +2.76 | +0.90 | −20.5 | +0.55 |
| 10 min slots, 24 slots | +3.12 | +1.71 | −22.8 | +0.68 |
| No-show rate x0.7 | +0.11 | +0.05 | −0.9 | −0.01 |
| No-show rate x1.3 | +2.91 | +0.97 | −21.4 | +0.13 |

**Reading.**

- **What can be said with confidence:** the rule raises the number of patients seen and cuts the idle time; the cost is waiting and, in most cases, overtime. The direction does not change in any sensitivity scenario.
- **What depends on the assumptions:** the size of the cost. With a 5 min consultation the increase in waiting is only +0.4 min, with 10 min it is +2.2 min; the increase in overtime moves between 0.0 and 1.1 min. The upper end of the consultation time (10 min) is critical for waiting and overtime.
- **The value of the rule depends on the no-show rate:** if the no-show rate drops by 30%, the rule hardly ever triggers (+0.11 patients); if it rises by 30%, the gain grows (+2.9). The no-show rate in the data is about 20%.
- **If the demand does not exceed the capacity** (16 requests, 16 slots), the rule is of no use: there has to be enough demand first.

## 5. Assumption register: measured, decision, assumption and how to measure it

| Value | Class | Current value | How a real measurement replaces it | Source status |
|---|---|---|---|---|
| No-show risk, show-up / no-show | **Measured** | 110,521 appointments | The application's `attended` records (`GET /ab/summary`, `/kpi`) | Dataset |
| Consultation time | **Decision** | 5–10 min, mean 7.5; variability 0.5 (assumption) | Recording the start and end times of consultations (the service does not record them today); at least a few hundred consultations | A news report and a Grand National Assembly document, indirect |
| Slot | **Decision** | 15 min x 16 | The department's real calendar setting (15 min in the application since #59) | **Not confirmed**; 5–10 min is reported for state hospitals |
| Patient lateness | **Assumption** | Deviation 4 min | Recording the patient's check-in time | No source; the dataset has no arrival times |
| Demand (number of requests) | **Assumption** | Slots + 4 | Records of daily booking requests (accepted and refused) | No source; the dataset holds only the accepted ones |
| Number of rooms (sessions) | **Assumption** | Derived from the day's appointments (about 220) | The department's real capacity | Decision: no physician is named |
| 15 min waiting limit | **Decision** | Mean wait | A limit per patient could be defined (for example the 95th percentile) | No source; the chosen setting is not binding (`docs/waiting-time-distribution.md`) |
| Reminder effect | **Not measured** | Scenario 0–30% | Live A/B test | `SMS_received` is not an experiment |

Sensitivity: the slot length and the consultation time affect the size of the results most (section 4 and `docs/experiment-results.md`).
