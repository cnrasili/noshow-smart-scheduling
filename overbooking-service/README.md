# Overbooking Service

Decision service behind the booking application. It serves the no-show model, decides slot-level overbooking, sends confirmation and reminder messages, and reports schedule KPIs.

## Tech Stack

- FastAPI + Pydantic
- SQLAlchemy 2 through the shared [`db`](../db/) package
- scikit-learn and joblib for model serving
- APScheduler for reminder jobs
- Mailpit (SMTP) for confirmation and reminder emails in development
- pytest

## Scope

- REST model-serving API called at booking time
- Rule engine for slot-level overbooking
- Scheduled confirmation and reminder jobs
- Logging for the reminder A/B comparison
- Schedule KPIs: utilization, idle time, overtime; shown on the KPI screen of the [admin service](../admin-service/)

## Endpoints

See the [API contract](../docs/api-contract.md).

## Development

From the repository root:

```bash
pip install -e db -e "overbooking-service[dev]"
cd overbooking-service
uvicorn overbooking_service.main:app --reload --port 8001
pytest
```

The service runs on http://localhost:8001 and its documentation is at http://localhost:8001/docs.

## Model

The service loads the model from `models/` at startup:

| File | Content |
|---|---|
| `model.joblib` | Trained classifier or Pipeline with `predict_proba` |
| `feature_schema.json` | Model version, feature names, no-show label, scikit-learn version |

Both files are written by [`ml/export_model.py`](../ml/export_model.py). At startup the service refuses a model when:

- the feature count or trained column names do not match the schema,
- the no-show label (`positive_class`) is not one of the model classes.

Models trained on named columns receive a DataFrame; others receive an array in schema order. Requests whose features do not match the schema are rejected.

`tests/test_model_acceptance.py` checks any model placed in `models/`. See [model features](../docs/features.md) for the delivery steps.

The current model is a placeholder (`dummy-v0`) created by `scripts/make_dummy_model.py`.

## Patient Data

Features are computed from the patient record and appointment history in the `patients` and `appointments` tables. Only appointments with a recorded `attended` value count as history. Access goes through the `PatientDataSource` interface in `overbooking_service/data_source.py`; `/predict` returns `503` when the tables cannot be read.

## Overbooking Rule

`POST /booking-decision` decides whether a patient may be booked into a slot. The rule is the pure function `decide` in `overbooking_service/rules.py`; the decision table is in the [API contract](../docs/api-contract.md#post-booking-decision).

Slot state is read from the `slots` and `appointments` tables through the `SlotDataSource` interface in `overbooking_service/data_source.py`; `/booking-decision` returns `503` when the tables cannot be read.

- Slot capacity is the slot's `max_patients` column.
- The slot date is the date of `start_at` in `clinic_timezone` (`config.yaml`, default `Europe/Istanbul`), the same time zone as the database triggers.
- Daily overbooks are the appointments after the first one in each slot of the doctor on that date.

Rule parameters are read from `config.yaml`. The current values are defaults until the simulation study sets the final ones.

| Setting | Default | Meaning |
|---|---|---|
| `threshold` | 0.30 | Minimum `p_noshow` of the booked patient for an overbook |
| `daily_overbook_limit` | 2 | Maximum overbooks per doctor per day |

Environment variables override the file, for example `OVERBOOKING__THRESHOLD=0.25`. With Docker Compose, rebuild the service after editing `config.yaml`.

Every decision is logged in the `booking_decisions` table.

## Confirmation and Reminder Messages

The web backend reports booked and cancelled appointments to `POST /events/appointment-booked` and `POST /events/appointment-cancelled` (see the [API contract](../docs/api-contract.md)). Each event stores its messages in the `messages` table:

| Message | Sent |
|---|---|
| Confirmation | Within a minute of booking |
| Reminder | `hours_before` hours before the appointment |

A background job (APScheduler) sends due messages every `dispatch_interval_seconds`. Because messages are stored in the database, scheduled reminders survive a restart.

| Status | Meaning |
|---|---|
| `pending` | Waiting to be sent |
| `sent` | Delivered to the mail server |
| `cancelled` | Appointment cancelled before sending |
| `expired` | Appointment started before sending |
| `failed` | Sending failed `max_attempts` times |

Each appointment gets at most one message of each kind, and a sent message is never sent again.

Settings in `config.yaml`:

| Setting | Default | Meaning |
|---|---|---|
| `enabled` | true | Run the background sender |
| `hours_before` | 24 | Reminder lead time in hours |
| `dispatch_interval_seconds` | 60 | How often due messages are sent |
| `max_attempts` | 3 | Send attempts before a message is marked `failed` |

Messages are sent by email when `SMTP_HOST` is set; otherwise they are written to the service log. With Docker Compose, emails go to Mailpit at http://localhost:8025.

## Reminder A/B Test

Each appointment that can get a reminder is assigned to the `reminder` or `control` group, and the assignment is logged in the `ab_assignments` table. The control group gets the confirmation but no reminder. The group is a hash of the patient id and `salt`, so a patient stays in the same group for all appointments and the groups are about equal in size.

`GET /ab/summary` compares the no-show rates of the two groups using `appointments.attended` (see the [API contract](../docs/api-contract.md#get-absummary)). With `unit=patient` each patient counts once, through the earliest appointment with an outcome; this keeps the observations of the z-test independent.

| Setting | Default | Meaning |
|---|---|---|
| `ab_test.enabled` | true | Assign groups; when false, every appointment gets a reminder |
| `ab_test.salt` | `reminder-ab-v1` | Hash salt; changing it reassigns patients |

## KPIs

`GET /kpi` returns utilization, physician idle time, overtime, mean waiting time and overbooked slots for a doctor and a date (see the [API contract](../docs/api-contract.md#get-kpi) and [KPI definitions](../docs/kpi-definitions.md)). The KPI screen of the [admin service](../admin-service/) shows them for the selected date and the days before it, with a chart and a table.

The booking application does not record consultation times, so the KPIs replay the day from the schedule:

- The session runs from the doctor's first slot start to the last slot end.
- Patients with `attended = true` are seen in slot order, each for `service_minutes`, and arrive on time.
- Appointments without a recorded attendance are not counted as seen.

The default consultation length is the simulation's mean service time.

| Setting | Default | Meaning |
|---|---|---|
| `kpi.service_minutes` | 12 | Consultation length in minutes |

## Demo Data

`python -m overbooking_service.demo` adds simulated booking history to the clinic created by the web backend seed (`python -m web_backend.seed`):

- 200 patients without login accounts, with attributes drawn at rates similar to the public dataset. The seeded patients with accounts also take part.
- The generated patients get fictional national ID numbers of the web backend's demo pattern (prefix `99999`, a four-digit number from 1000 up, check digits); numbers already in use are skipped. They are made up and belong to no real person.
- Booking requests for the seeded doctors' slots from three weeks before the demo date to one week after it, processed with the same overbooking rule as `/booking-decision`: the first empty slot, otherwise the first slot the rule allows to overbook.
- Past appointments get an outcome drawn from the model's `p_noshow` and, when a reminder was possible, an A/B group. Future appointments have no outcome, so free slots remain for live bookings.
- Doctor-days the seed already booked are left unchanged, so the doctor can mark attendance in the web application. Their past bookings get an A/B group, so marking attendance changes `/ab/summary`.
- No messages are created for the generated appointments; only appointments reported to `POST /events/appointment-booked` get a confirmation and a reminder.
- Slot length and working hours come from the web backend seed.

| Option | Default | Meaning |
|---|---|---|
| `--today` | today | Demo date in the clinic time zone |
| `--seed` | 42 | Random seed; the same seed gives the same data |
| `--reminder-effect` | 0 | Relative no-show reduction in the reminder group; 0 means reminders have no simulated effect |

The command refuses to run before the web backend seed and when the demo history already exists. To start from an empty database, remove the Docker volume with `docker compose down -v`; this deletes all local data.

### Demo Scenario

1. Start the stack and load the demo data:

   ```bash
   docker compose up --build -d
   docker compose exec web-backend python -m web_backend.seed
   docker compose exec overbooking-service python -m overbooking_service.demo
   ```

   The last command prints an empty and a booked slot of the first doctor with slots after the demo date.

2. Create an administrator (see the [admin service](../admin-service/README.md#setup)) and open the KPI screen at http://localhost:8002. The past days show utilization, idle time, overtime, waiting time and overbooked slots, and the reminder A/B test.
3. Open http://localhost:8001/ab/summary to compare the no-show rates of the reminder and control groups, and http://localhost:8001/ab/summary?unit=patient for one observation per patient.
4. In the API docs at http://localhost:8001/docs, call `POST /booking-decision` for the empty slot (normal booking) and for the booked slot (overbook or reject, with the reason).
5. Call `POST /events/appointment-booked` for a new appointment id. The response shows the A/B group and the scheduled messages; the confirmation appears in Mailpit at http://localhost:8025 within a minute.
