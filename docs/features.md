# Model Features

**Status:** Draft.

The model may only use features that are known at booking time. The overbooking service computes the same features when it calls the model.

| Feature | Source | Known at booking time | Note |
|---|---|---|---|
| `lead_days` | AppointmentDay − ScheduledDay | Yes | |
| `weekday` | AppointmentDay | Yes | |
| `age` | Patient record | Yes | |
| `gender` | Patient record | Yes | |
| `scholarship` | Patient record | Yes | |
| `hipertension` | Patient record | Yes | |
| `diabetes` | Patient record | Yes | |
| `alcoholism` | Patient record | Yes | |
| `handcap` | Patient record | Yes | |
| `prior_appt_count` | Patient's earlier appointments | Yes | Only appointments before the current one |
| `prior_noshow_count` | Patient's earlier appointments | Yes | Only appointments before the current one |
| `SMS_received` | — | **No** | Sent after booking; excluded |
| `Neighbourhood` | — | — | No equivalent in the application; proposed to exclude |

## Open Questions

- Final feature list and encoding (for example `gender`, `weekday`)
- Model file format and input column order
