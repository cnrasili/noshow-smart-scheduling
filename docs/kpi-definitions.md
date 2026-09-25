# KPI Definitions

**Status:** Draft.

The simulation and the admin dashboard use the same definitions so that their results can be compared.

| KPI | Definition | Unit |
|---|---|---|
| Patient waiting time | Consultation start time − max(appointment time, patient arrival time) | minutes |
| Physician idle time | Time within the session during which the physician has no patient to see | minutes |
| Overtime | Time the physician works after the planned session end | minutes |
| Utilization | Physician busy time ÷ planned session length | ratio |

## Open Questions

- Session length, slot length and service time distribution
- Whether patient punctuality is modelled
