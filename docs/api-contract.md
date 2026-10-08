# API Contract

**Status:** Agreed. Changes are agreed by the components involved before they are implemented.

Interfaces between the components:

- the web backend and the overbooking service (prediction, booking decision, booking events),
- the admin service and the overbooking service (A/B summary, KPIs),
- the admin service and the web backend (internal account API),
- the web frontend and the web backend (doctor agenda).

The web frontend calls only the web backend; it never calls the overbooking service or the internal account API.

## Shared Database

All services use one PostgreSQL database with a single Alembic history in [`db/`](../db/). Each table is written by its owner; the other services only read it. The only exception is the overbooking service's demo data generator (`overbooking_service.demo`), which adds demo patients and appointments to the web backend's tables.

| Tables | Written by | Read by |
|---|---|---|
| `patients`, `doctors`, `doctor_schedules`, `slots`, `appointments`, `user_accounts`, `auth_sessions` | Web backend | Overbooking service (`patients`, `doctors`, `doctor_schedules`, `slots`, `appointments`); admin service (`patients`, `doctors`, `doctor_schedules`, `user_accounts`) |
| `predictions`, `booking_decisions`, `messages`, `ab_assignments` | Overbooking service | — |
| `admin_users`, `admin_sessions`, `admin_audit_log` | Admin service | — |

### Attendance

Attendance is not reported by an event. The doctor marks an appointment as attended or missed in the web application, and the web backend stores it in `appointments.attended` (`NULL` until marked). The overbooking service reads this column directly:

- patient history for the model features (`prior_appt_count`, `prior_noshow_count`), counting only appointments with a recorded outcome before the booking date,
- the no-show rates of `GET /ab/summary`,
- the patients seen in `GET /kpi`.

The web backend deletes a cancelled appointment and then reports it with `POST /events/appointment-cancelled`; deleted appointments no longer count anywhere.

## Service Availability

Booking never depends on the overbooking service being available:

- The web backend waits at most 3 seconds for `POST /booking-decision`. Without an answer (timeout, connection error, error status or unexpected body), an empty slot is still booked, but a booked slot is never overbooked.
- Booking events are sent after the response to the patient. A failed event does not undo the booking change; the service ignores repeated events.

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

Rule (`max_patients` is the slot's capacity in the `slots` table; other parameters in `overbooking-service/config.yaml`):

| Slot state | Decision |
|---|---|
| Empty | Allow, normal booking |
| Patient already booked in the slot | Reject |
| Patients in slot >= `max_patients` | Reject |
| Any booked patient's `p_noshow` < `threshold` | Reject |
| Overbooks of the doctor on the slot date >= `daily_overbook_limit` | Reject |
| Otherwise | Allow as overbook |

Errors:

| Status | Reason |
|---|---|
| 404 | Patient or slot not found |
| 422 | Invalid request, or `booking_date` is after the slot date |
| 503 | Patient or slot data cannot be read |

## `POST /events/appointment-booked`

Called by the web backend after an appointment is booked. Schedules a confirmation message, sent within a minute, and a reminder message before the appointment.

Request:

```json
{
  "appointment_id": 501,
  "patient_id": 123,
  "email": "patient@example.com",
  "appointment_start": "2026-11-10T09:30:00+03:00"
}
```

`appointment_start` must include a time zone offset. Message texts show the time as sent.

Response:

```json
{
  "messages": [
    { "kind": "confirmation", "send_at": "2026-11-02T06:00:00Z", "status": "pending" },
    { "kind": "reminder", "send_at": "2026-11-09T06:30:00Z", "status": "pending" }
  ],
  "ab_group": "reminder"
}
```

- No reminder is scheduled when the appointment is closer than the reminder lead time.
- Appointments that can get a reminder take part in the reminder A/B test. `ab_group` is `reminder` or `control`; the control group gets no reminder. The group depends only on the patient. `ab_group` is `null` when the appointment is too close for a reminder or the test is disabled.
- Sending the same event again returns the existing messages and creates no duplicates.
- A message is not sent once the appointment has started.

Errors:

| Status | Reason |
|---|---|
| 422 | Invalid request, `appointment_start` without time zone, or appointment in the past |

## `POST /events/appointment-cancelled`

Called by the web backend after an appointment is cancelled. Cancels its messages that are not sent yet.

Request:

```json
{
  "appointment_id": 501
}
```

Response:

```json
{
  "cancelled": 1
}
```

Errors:

| Status | Reason |
|---|---|
| 422 | Invalid request |

## `GET /ab/summary`

Compares the no-show rate of the reminder and control groups. Read by the admin service's KPI screen. Only appointments with a recorded `attended` value count; deleted (cancelled) appointments are excluded.

Request: `GET /ab/summary?unit=appointment`

| `unit` | Observations |
|---|---|
| `appointment` (default) | Every appointment |
| `patient` | Each patient's earliest appointment, so that frequent patients do not weigh more |

The z-test assumes independent observations. Appointments of the same patient are not independent, so `unit=patient` gives the more reliable p-value.

Response:

```json
{
  "unit": "appointment",
  "groups": [
    { "group": "reminder", "appointments": 120, "no_shows": 18, "no_show_rate": 0.15 },
    { "group": "control", "appointments": 115, "no_shows": 29, "no_show_rate": 0.252 }
  ],
  "difference": 0.102,
  "z": 2.0,
  "p_value": 0.046
}
```

`difference` is the control rate minus the reminder rate. `z` and `p_value` come from a two-sided pooled two-proportion z-test. Values that cannot be computed yet are `null`.

## `GET /kpi`

Returns schedule KPIs for a doctor and a date. Read by the admin service's KPI screen. Definitions are in [KPI definitions](kpi-definitions.md). The date is a clinic calendar day.

Request: `GET /kpi?doctor_id=1&date=2026-11-10`

Response:

```json
{
  "utilization": 0.87,
  "idle_minutes": 40.0,
  "overtime_minutes": 15.0,
  "mean_wait_minutes": 6.5,
  "overbooked_slots": 2,
  "patients_seen": 14
}
```

The session runs from the doctor's first slot start to the last slot end on that date, or over the doctor's working hours of the weekday when the overbooking service's `kpi.session` setting is `schedule` (days without working hours fall back to the slots). Patients with `attended = true` are seen in slot order, each for a fixed consultation length, and are assumed to arrive on time; consultation start and end times are not recorded.

Errors:

| Status | Reason |
|---|---|
| 404 | Doctor not found, or the doctor has no slots on the date |
| 422 | Invalid request |

## Internal account API (web backend)

Served by the web backend for the hospital's admin service. Patients and doctors cannot register themselves; the administration creates their accounts through this API. The public web frontend never calls it, and it is not listed in the web backend's public API documentation.

Every request carries the service token in the `X-Internal-Token` header. The token is set in the web backend's `INTERNAL_API_TOKEN` environment variable; if the variable is not set, the API is disabled.

Errors of every endpoint:

| Status | Reason |
|---|---|
| 401 | `X-Internal-Token` missing or wrong |
| 503 | Internal API is disabled (`INTERNAL_API_TOKEN` not set) |

### `POST /internal/accounts/patients`

Creates a patient record with its login account. The patient logs in with the national ID number and the password.

Request:

```json
{
  "national_id": "99999000184",
  "full_name": "Ayşe Kaya",
  "email": "ayse@example.com",
  "age": 34,
  "gender": "F",
  "scholarship": false,
  "hipertension": false,
  "diabetes": false,
  "alcoholism": false,
  "handcap": 0,
  "password": "initial-password"
}
```

- `national_id`: Turkish national ID number, 11 digits, first digit not 0, official check digits.
- `email`: contact address for messages; stored in lower case.
- `gender`: `F` or `M`. `age`: 0–130. `handcap`: 0–4. The four flags default to `false` and `handcap` to 0.
- `password`: initial password, 8–128 characters. Only its hash is stored.

Response (`201`):

```json
{
  "account_id": 12,
  "patient_id": 9,
  "national_id": "99999000184",
  "full_name": "Ayşe Kaya",
  "email": "ayse@example.com"
}
```

Errors:

| Status | Reason |
|---|---|
| 409 | `National ID number already registered`, or `Email already in use` (by a patient or a doctor) |
| 422 | Invalid request, for example an invalid national ID number or e-mail address |

### `POST /internal/accounts/doctors`

Creates a doctor with login account and weekly working hours, and generates the doctor's slots for the next two weeks from the working hours. The doctor logs in with the e-mail address and the password.

Request:

```json
{
  "full_name": "Dr. Deniz Yıldız",
  "specialty": "Dahiliye",
  "email": "deniz.yildiz@example.com",
  "password": "initial-password",
  "working_hours": [
    { "weekday": 0, "start_time": "09:00", "end_time": "12:00" },
    { "weekday": 2, "start_time": "13:00", "end_time": "16:00" }
  ]
}
```

- `specialty`: the department patients choose when booking.
- `working_hours`: 1–7 intervals, at most one per weekday (`0` = Monday … `6` = Sunday), clinic local time, `end_time` after `start_time`.
- `password`: initial password, 8–128 characters.

Response (`201`):

```json
{
  "account_id": 13,
  "doctor_id": 5,
  "full_name": "Dr. Deniz Yıldız",
  "specialty": "Dahiliye",
  "email": "deniz.yildiz@example.com",
  "slots_created": 54
}
```

Errors:

| Status | Reason |
|---|---|
| 409 | `Email already in use` |
| 422 | Invalid request, for example overlapping weekdays or an invalid time interval |

### `PUT /internal/accounts/{account_id}/password`

Resets the password of a patient's or a doctor's account. The account's open sessions end, so it has to log in again.

Request:

```json
{ "password": "new-password" }
```

Response: `204`, no body.

Errors:

| Status | Reason |
|---|---|
| 404 | Account not found |
| 422 | Invalid request, for example a password shorter than 8 characters |

## `GET /doctors/me/agenda` (web backend)

Served by the web backend for the website's doctor screens. Returns every clinic day of a date range with the signed-in doctor's slot count and booked appointments; the doctor's patient list uses it for the week overview and the upcoming appointments. Read-only; the daily list with attendance marking keeps using `GET /doctors/me/calendar`.

Needs a signed-in doctor (`Authorization: Bearer <token>`).

Query parameters:

| Parameter | Meaning |
|---|---|
| `date_from` | First clinic day, `YYYY-MM-DD` |
| `date_to` | Last clinic day, `YYYY-MM-DD`; on or after `date_from`, at most 31 days in the range |

Response (`200`), one entry per day of the range in order, days without slots included:

```json
[
  {
    "date": "2026-10-20",
    "slot_count": 9,
    "appointments": [
      {
        "id": 373,
        "slot_id": 1204,
        "start_at": "2026-10-20T06:00:00Z",
        "end_at": "2026-10-20T06:20:00Z",
        "patient_name": "Ayşe Kaya",
        "extra": false
      }
    ]
  },
  { "date": "2026-10-21", "slot_count": 0, "appointments": [] }
]
```

- Days are clinic days (`Europe/Istanbul`); times are UTC.
- `slot_count` is 0 on days the doctor has no slots, for example days without working hours.
- Appointments are ordered by slot time and then by booking order. `extra` is `true` for an appointment booked into a slot that already had a patient (an overbook).
- No contact or account data is returned.

Errors:

| Status | Reason |
|---|---|
| 401 | Not signed in or session expired |
| 403 | Signed in as a patient |
| 422 | Invalid dates, `date_to` before `date_from`, or a range of more than 31 days |
