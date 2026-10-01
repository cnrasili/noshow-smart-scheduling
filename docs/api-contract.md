# API Contract

**Status:** Draft.

Interface between the web backend and the overbooking service. The web frontend does not call the overbooking service directly.

## `POST /predict`

Returns the no-show probability of a patient for an appointment.

Request:

```json
{
  "patient_id": 123,
  "appointment_date": "2026-11-10",
  "booking_date": "2026-11-02"
}
```

Response:

```json
{
  "p_noshow": 0.34,
  "model_version": "dummy-v0"
}
```

Errors:

| Status | Reason |
|---|---|
| 404 | Patient not found |
| 422 | Invalid request, or `appointment_date` is before `booking_date` |
| 503 | Patient data cannot be read |

## `POST /booking-decision`

Called by the web backend before a patient is booked into a slot.

Request:

```json
{
  "patient_id": 123,
  "slot_id": 45,
  "booking_date": "2026-11-02"
}
```

Response:

```json
{
  "allow": true,
  "overbook": true,
  "p_noshow": 0.34,
  "reason": "Slot is booked; booked patient risk 0.41 >= 0.30; daily overbooks 1/2"
}
```

`p_noshow` is the risk of the requesting patient for the slot date. `overbook` is `true` when the patient is added to an already booked slot.

Rule (parameters in `overbooking-service/config.yaml`):

| Slot state | Decision |
|---|---|
| Empty | Allow, normal booking |
| Patient already booked in the slot | Reject |
| Patients in slot >= `max_patients_per_slot` | Reject |
| Any booked patient's `p_noshow` < `threshold` | Reject |
| Overbooks of the doctor on the slot date >= `daily_overbook_limit` | Reject |
| Otherwise | Allow as overbook |

Errors:

| Status | Reason |
|---|---|
| 404 | Patient or slot not found |
| 422 | Invalid request, or `booking_date` is after the slot date |
| 503 | Patient or slot data cannot be read |

## `GET /kpi`

Returns schedule KPIs for a doctor and a date. Definitions are in [KPI definitions](kpi-definitions.md).

Request: `GET /kpi?doctor_id=1&date=2026-11-10`

Response:

```json
{
  "utilization": 0.87,
  "idle_minutes": 40,
  "overtime_minutes": 15,
  "overbooked_slots": 2
}
```
