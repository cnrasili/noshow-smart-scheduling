# KPI Definitions

**Status:** Draft.

The simulation and the KPI screen of the admin service use the same definitions so that their results can be compared.

| KPI | Definition | Unit |
|---|---|---|
| Patient waiting time | Consultation start time − max(appointment time, patient arrival time) | minutes |
| Idle time | Time within the session during which the clinic room has no patient to see | minutes |
| Overtime | Time the clinic room is in use after the planned session end | minutes |
| Utilization | Busy time of the clinic room ÷ planned session length | ratio |

## Open Questions

- Session length, slot length and service time distribution
- Whether patient punctuality is modelled
