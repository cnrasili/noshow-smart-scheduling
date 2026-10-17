# Web Backend

REST API of the appointment booking application.

## Tech Stack

- FastAPI + Pydantic
- SQLAlchemy 2 through the shared [`db`](../../db/) package
- pytest

## Scope

- Patients, the department, slots and appointments (tables in `db/noshow_db/models/core.py`). Patients are the patients of the public dataset; the system has one department, "Aile Hekimliği" (`General Practice` in the database), and no doctor. The department is the one record in `doctors`, so tables, columns and some API paths keep the doctor names.
- Calendar/slot algorithm: slot generation from the department's working hours, conflict checks, more than one patient per slot for overbooking
- Calls the overbooking service at booking time (see [API contract](../../docs/api-contract.md))

## Development

From the repository root:

```bash
pip install -e db -e "web/backend[dev]"
cd web/backend
uvicorn web_backend.main:app --reload
pytest
```

The API runs on http://localhost:8000 and its documentation is at http://localhost:8000/docs.

Slot capacity and appointment dates are enforced by PostgreSQL triggers. Their tests are skipped unless `NOSHOW_TEST_DATABASE_URL` points to a disposable PostgreSQL database; the tests drop and recreate its `public` schema:

```bash
NOSHOW_TEST_DATABASE_URL=postgresql+psycopg://noshow:noshow@localhost:5432/noshow_test pytest
```

## Slot Length

`SLOT_MINUTES` sets the length of newly generated slots in minutes, both for the department opening slots and for the demo seed. It defaults to `15`, which gives 16 slots in the session from 08:00 to 12:00 (#9), and must be a whole number from 5 to 120; any other value stops the web backend at startup with a clear message.

```bash
SLOT_MINUTES=20 uvicorn web_backend.main:app --reload
```

Existing slots are not changed. Generating slots again after a change only fills working hours that no existing slot covers, so slots of different lengths never overlap.

## Demo Data

The patients and their appointment history come from the public dataset, which the `migrate` service loads (`python -m noshow_db.load_dataset`). `web_backend.seed` invents nothing: it creates the department with its working hours (Monday to Friday, 08:00–12:00) and staff account, opens the department's slots for the next four weeks, and opens login accounts for five dataset patients with different histories. Running it again only adds what is missing.

```bash
python -m web_backend.seed
# or, with Docker Compose
docker compose exec web-backend python -m web_backend.seed
```

The seed needs the dataset patients, and it refuses a database that still holds the doctors of the earlier multi-department demo; recreate such a database with `docker compose down -v` and `docker compose up --build -d`.

All demo accounts use the password `demo1234`; these are local demo values only.

| Account | Login | History in the dataset |
| --- | --- | --- |
| Department "Aile Hekimliği" | Username `aile.hekimligi` | — |
| Patient | Patient number `1421986987763` | 18 appointments, all missed |
| Patient | Patient number `26886125921145` | 70 appointments, all attended |
| Patient | Patient number `93779.52927` | 1 appointment |
| Patient | Patient number `1411446711177` | 9 appointments, 3 missed |
| Patient | Patient number `11241475371456` | 4 appointments, 1 missed |

## Public Hospital Site

`GET /public/doctors` returns the department's record with its weekly working hours, without sign-in. It returns no account data (see the [API contract](../../docs/api-contract.md#get-publicdoctors-web-backend)).

## Authentication

`POST /auth/login` takes the role of the login form and the credentials of that role:

- Patients: `{"role": "patient", "patient_number": "…", "password": "…"}`. The patient number is the dataset's `PatientId` as stored in `patients.patient_number`, for example `93779.52927` for a number written in exponent form in the dataset. Patients have no national ID number, phone number or e-mail address of their own.
- The department's staff: `{"role": "department", "username": "…", "password": "…"}`. The staff account has the role `doctor` in the database and keeps its username in `user_accounts.email`.

Wrong credentials and a login through the other role's form get the same `401` ("Wrong patient number or password" or "Wrong username or password"). There is no self-registration; accounts are opened by the hospital. A successful login returns a bearer token that is valid for 12 hours; send it as `Authorization: Bearer <token>`. `GET /auth/me` returns the role and the name: `Hasta <PatientId>` for patients, the department's name for its staff. Passwords are hashed with scrypt and only a hash of each token is stored (`user_accounts` and `auth_sessions` tables).

Failed logins are limited to slow down password guessing. After 5 failures within 15 minutes for one login name (patient number or username, known or not), further logins for that name get `429` ("Too many failed login attempts; try again later") until the window has passed, even with the correct password. Other accounts are not affected, so a few wrong passwords on a shared computer, or from browsers that reach the backend through the same address (a hospital gateway, or every browser on a Docker Desktop host), do not lock anyone else. A much higher limit per client address, 50 failures within 15 minutes across any login names, still stops one client from trying many names. Failures are kept in the `login_failures` table with a SHA-256 hash of the role and login name instead of the name itself; a successful login clears the failures of its name.

Both limits are settings; any value other than a whole number from 1 to 10000 stops the web backend at startup with a clear message:

| Variable | Default | Meaning |
| --- | --- | --- |
| `LOGIN_MAX_FAILURES_PER_NAME` | `5` | Failed logins of one login name within 15 minutes before that name is locked |
| `LOGIN_MAX_FAILURES_PER_ADDRESS` | `50` | Failed logins from one client address within 15 minutes, across all names, before that address is locked |

Every response carries the headers `X-Content-Type-Options: nosniff`, `Referrer-Policy: no-referrer`, `X-Frame-Options: DENY` and `Cache-Control: no-store`.

## Accounts

Nobody can register; the hospital opens the accounts. The account rules (one account per dataset patient, unique login names, password hashing, the department's working hours) are in `web_backend/accounts.py`, which both the demo seed and the internal account API use.

The internal account API (`/internal/accounts/...`) lets the hospital's admin service open login accounts for dataset patients by patient number and reset passwords; it never creates a patient. Every request needs the service token from the `INTERNAL_API_TOKEN` environment variable in the `X-Internal-Token` header; without the variable the API is disabled and answers `503`. The public frontend never calls it, and it is left out of the public API documentation at `/docs`. Requests, responses and errors are described in the [API contract](../../docs/api-contract.md#internal-account-api-web-backend).

```bash
INTERNAL_API_TOKEN=change-me uvicorn web_backend.main:app --reload
```

## Patient Messages

`GET /patients/me/messages` returns the signed-in patient's demo SMS for "Randevularım": only their own messages with the status `sent`, newest first, with `kind` (`confirmation` or `reminder`), `sent_at` and `body`. The web backend only reads the overbooking service's `messages` table (see the [API contract](../../docs/api-contract.md#messages)); nothing about the A/B test is returned.

## Department Panel

- `GET /doctors/me/calendar?date=…` and `GET /doctors/me/agenda` give the department's days and weeks (the paths keep the doctor names of the API contract).
- `PATCH /appointments/{id}/attendance` with `{"attended": true}`, `false` or `null` (takes a mark back) works only on the appointment day; other days get `422`.
- `GET /department/dataset-days` lists the days of the dataset with their number of appointments and no-shows, and `GET /department/dataset-days/{date}` returns every appointment of such a day with the patient (`Hasta <PatientId>`), the age and the recorded outcome. They read `dataset_appointments` and are read-only.

## Overbooking

Before booking, `POST /appointments` asks the overbooking service (`OVERBOOKING_SERVICE_URL`, default `http://localhost:8001`) for a `/booking-decision`. A rejected booking returns `409`. If the service does not answer within 3 seconds or returns an error, empty slots are still booked but booked slots are never overbooked. A slot that has reached its `max_patients` is rejected without asking the service.

`GET /slots` lists the department's upcoming slots (by default the next two weeks; `date_from` and `date_to` choose a range) as the patient sees them: `available` ("Müsait") or not ("Dolu"), and `booked_by_me`. A booked slot below its capacity stays available, because the service decides when the patient books; the number of patients in a slot and any risk are not sent.

After a booking or a cancellation is saved, the web backend sends `/events/appointment-booked` (appointment, patient and start time) or `/events/appointment-cancelled` so the service schedules or cancels the confirmation and reminder messages. The events are sent after the response; if one fails it is logged and the booking change stays.
