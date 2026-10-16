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

The installed model is the random forest `random_forest-v1` delivered by the prediction model side (#7).

### Installing a Delivered Model

The prediction model side delivers `model.joblib` and `feature_schema.json` in `ml/models/`. Install them with:

```bash
python -m overbooking_service.install_model --source ../ml/models
```

The command refuses the model, and keeps the installed one, when:

- a file is missing or the model cannot be loaded (feature count, trained column names or `positive_class` do not match the schema),
- the schema features differ from the features the service computes (`overbooking_service/features.py`),
- a no-show probability lies outside 0–1, or long lead times with past no-shows do not score higher than reliable short-notice patients.

A different scikit-learn minor version is reported as a warning. The same checks are the acceptance tests in `tests/test_model_acceptance.py`. Commit the installed files, then restart the service to load the model; with Docker Compose rebuild it, since the model is part of the image:

```bash
docker compose up --build -d overbooking-service
```

The previously installed model stays available in the Git history.

## Patient Data

Features are computed from the patient record in `patients` and the patient's appointment history: the past appointments of the public dataset in `dataset_appointments` and the bookings in `appointments` with a recorded `attended` value. Access goes through the `PatientDataSource` interface in `overbooking_service/data_source.py`; `/predict` returns `503` when the tables cannot be read.

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

The web backend does not retry a failed event. If a booked event is lost, for example while the service is stopped, a second job of the background sender schedules the messages and the A/B group by the same rules: at startup and then every `interval_seconds`, each future appointment booked within the last `lookback_hours` that has no message is handled as if its event had arrived. The patient's email and the appointment time are read from the booking database. A booked event and the job never create a second message or A/B group for the same appointment. After the database is reset, the job also schedules messages for the upcoming appointments of the demo data, which are stored without events.

| Setting | Default | Meaning |
|---|---|---|
| `message_recovery.enabled` | true | Run the recovery job |
| `message_recovery.interval_seconds` | 300 | How often the job runs after its first run at startup |
| `message_recovery.lookback_hours` | 48 | Only appointments booked within this many hours are handled |

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

- The session runs from the doctor's first slot start to the last slot end (`kpi.session: slots`), or over the doctor's working hours of the weekday (`kpi.session: schedule`). With `schedule`, time within the working hours without slots counts as idle and work after the working hours as overtime; a day without working hours falls back to `slots`.
- Patients with `attended = true` are seen in slot order, each for `service_minutes`, and arrive on time.
- Appointments without a recorded attendance are not counted as seen.

The default consultation length is the simulation's mean service time.

| Setting | Default | Meaning |
|---|---|---|
| `kpi.service_minutes` | 12 | Consultation length in minutes |
| `kpi.session` | `slots` | Session definition: `slots` or `schedule`; the final choice belongs to the session parameters decided with the simulation side |

## Demo Scenario

The service generates no demo data. It works on the dataset patients and on the bookings made in the web application, so the decisions page, the KPI screen and the reminder A/B test fill as bookings are made and attendance is marked.

1. Start the stack, load the demo data and create an administrator (see [Getting Started](../README.md#getting-started)).
2. Book an appointment in the web application with a demo patient account. The decision and the patient's predicted no-show risk appear on the decisions page of the admin service at http://localhost:8002/decisions; the risk counts the patient's past appointments in the dataset. The confirmation appears in Mailpit at http://localhost:8025 within a minute.
3. Book the same time with another demo patient. The rule adds the patient as an overbook when the first patient's risk reaches the threshold, and otherwise rejects the booking; the decisions page shows the reason.
4. Log in as the doctor and mark the appointments as attended or missed. The KPI screen of the admin service and http://localhost:8001/ab/summary count them.
