# KPI Definitions

**Status:** Agreed on the IEN side on 17 October 2026 (review in pull request #62). The session parameters below are decisions of the team; slot length, consultation time and the other values still need an academic source, see `docs/decision-list.md`.

The simulation and the KPI screen of the admin service use the same definitions so that their results can be compared.

| KPI | Definition | Unit |
|---|---|---|
| Patient waiting time | Consultation start time − max(appointment time, patient arrival time) | minutes |
| Idle time | Time within the session during which the clinic room has no patient to see | minutes |
| Overtime | Time the clinic room is in use after the planned session end | minutes |
| Utilization | Busy time of the clinic room ÷ planned session length | ratio |

## Unit

The system is one department (`General Practice`); no physician is named or assigned. A session is one clinic room of the department; capacity and results belong to the department.

## Session parameters (decided 17 October 2026)

| Parameter | Value | Basis |
|---|---|---|
| Slot length | 15 minutes | Usual appointment interval in Turkish outpatient clinics (team knowledge, source to be added) |
| Slots per session | 16 (4 hours) | Half-day clinic session |
| Consultation time | 5 to 10 minutes, mean 7.5, coefficient of variation 0.5 (log-normal) | State hospital outpatient practice (source to be added); the variation is an assumption |
| Patient punctuality | Modelled: arrival offset with a standard deviation of 4 minutes; a consultation never starts before the appointment time | Assumption |
| Session for the KPIs | First slot start to last slot end (`kpi.session: slots` in the overbooking service) | Service default |
| Booking requests per session | Number of slots + 4 (simulation) | Assumption |

The web application currently uses 20-minute slots; they have to be aligned to 15 minutes.

## Open Questions

- Source for the slot length and the consultation time
