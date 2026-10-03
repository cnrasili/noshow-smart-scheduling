# Simulation

Appointment template, overbooking policy and discrete-event simulation of a clinic session.

## Tech Stack

- Python 3.12
- SimPy for discrete-event simulation
- NumPy and pandas for input distributions and results
- matplotlib for charts

## Scope

- Clinic session parameters: slot length, number of slots, service time, patient punctuality
- Appointment template design
- No-show-aware overbooking policy
- Simulation of fixed-interval booking and selective overbooking
- Comparison of patient waiting time, physician idle time and overtime (see [KPI definitions](../docs/kpi-definitions.md))

## Development

```bash
python -m venv .venv
pip install -r requirements.txt
```

## Clinic Session Simulation

[`clinic_sim.py`](clinic_sim.py) simulates one physician session with SimPy and compares booking policies on the KPIs in [`docs/kpi-definitions.md`](../docs/kpi-definitions.md).

```bash
python main.py                          # everything in one go (about 30 s), then opens output/index.html
python main.py --quick                  # fast preview
python live_day.py --trace              # animated clinic day + SimPy event log in the terminal
python real_days.py                     # every real appointment record of each test day (output/whole_day.html)
python clinic_sim.py                    # fixed-interval vs threshold rule vs cost-based rule R5-A
python clinic_sim.py --sweep            # sweep the threshold of the threshold rule
python clinic_sim.py --risks risks.csv  # empirical risks (column p, optional y = 1 for no-show)
python plots.py                         # trade-off chart and one-session timeline (PNG files in output/)
python value_ladder.py --risks ../ml/data/processed/risks_random_forest.csv  # what each layer adds
python dashboard.py --risks ../ml/data/processed/risks_random_forest.csv    # KPI-card dashboard: output/dashboard.html
```

- Policies: `fixed_interval`, `threshold_rule` (same logic as `overbooking-service/overbooking_service/rules.py`), `cost_rule` (R5-A: add a patient if P(shows >= capacity) < 1/(1+r), adapted from airline overbooking).
- All policies see the same booking requests, show-ups, arrival offsets and service times in each replication, so differences are paired.
- Defaults (16 slots of 15 min, mean consultation 12 min, CV 0.5, arrival sd 4 min, 4 extra requests, Beta(2, 8) risks) are **assumptions**, not measured values. Replace them with agreed values before drawing conclusions.
