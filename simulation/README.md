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
