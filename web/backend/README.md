# Web Backend

REST API of the appointment booking application.

## Tech Stack

- FastAPI + Pydantic
- SQLAlchemy 2 through the shared [`db`](../../db/) package
- pytest

## Scope

- Patients, doctors, slots and appointments (tables in `db/noshow_db/models/core.py`)
- Calendar/slot algorithm: slot generation from doctor working hours, conflict checks, more than one patient per slot for overbooking
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

`SLOT_MINUTES` sets the length of newly generated slots in minutes, both for doctors opening slots and for the demo seed. It defaults to `20` and must be a whole number from 5 to 120; any other value stops the web backend at startup with a clear message. The value itself is one of the session parameters decided by IEN-1.

```bash
SLOT_MINUTES=15 uvicorn web_backend.main:app --reload
```

Existing slots are not changed. Generating slots again after a change only fills working hours that no existing slot covers, so slots of different lengths never overlap.

## Demo Data

`web_backend.seed` creates a fictional clinic through the account module: four doctors in three branches (Dahiliye, Kardiyoloji, Göz Hastalıkları) with their own working hours, eight patients, the login accounts, slots from three weeks ago to two weeks ahead and a few example appointments per doctor. Running it again only adds missing doctors, patients and slots, so it also upgrades a database seeded by an earlier version.

```bash
python -m web_backend.seed
# or, with Docker Compose
docker compose exec web-backend python -m web_backend.seed
```

Doctors sign in at `/giris/hekim` with their e-mail address (for example `doktor@demo.local`; the others are printed by the seed command) and patients at `/giris/hasta` with their national ID number. All demo accounts use the password `demo1234`; these are local demo values only.

The demo patients' national ID numbers are **fictional**. They are valid by the check digit rules but start with the fixed prefix `99999`, followed by a four-digit sequence number and the check digits (`web_backend/national_id.py`). Never use real people's numbers in demo or test data.

| Patient      | National ID number (fictional) | Contact e-mail      |
| ------------ | ------------------------------ | ------------------- |
| Ayşe Kaya    | `99999000184`                  | `ayse@demo.local`   |
| Mehmet Demir | `99999000252`                  | `mehmet@demo.local` |
| Zeynep Çelik | `99999000320`                  | `zeynep@demo.local` |
| Ali Şahin    | `99999000498`                  | `ali@demo.local`    |
| Elif Arslan  | `99999000566`                  | `elif@demo.local`   |
| Burak Koç    | `99999000634`                  | `burak@demo.local`  |
| Selin Aydın  | `99999000702`                  | `selin@demo.local`  |
| Hasan Öztürk | `99999000870`                  | `hasan@demo.local`  |

The migration that adds the national ID column gives existing patients a fictional number built from their id with the same pattern, so a database seeded before it gets the numbers above. Alternatively, recreate the database, run `alembic upgrade head` and the seed again.

## Authentication

`POST /auth/login` takes the role of the login form and the credentials of that role:

- Patients: `{"role": "patient", "national_id": "…", "password": "…"}`. Every patient has exactly one record, identified by the Turkish national ID number (11 digits, first digit not 0, official check digits); the database rejects a second patient with the same number. The patient's e-mail address is only a contact address for messages and is not a login name.
- Doctors: `{"role": "doctor", "email": "…", "password": "…"}`.

Wrong credentials, an invalid national ID number and a login through the other role's form all get the same `401` ("Wrong national ID number or password" or "Wrong email or password"). There is no self-registration; accounts are created by the hospital. A successful login returns a bearer token that is valid for 12 hours; send it as `Authorization: Bearer <token>`. Passwords are hashed with scrypt and only a hash of each token is stored (`user_accounts` and `auth_sessions` tables).

## Accounts

Patients and doctors cannot register themselves; the hospital creates their accounts. The account rules (national ID number, unique e-mail, password hashing, the doctor's department and working hours) are in `web_backend/accounts.py`, which both the demo seed and the internal account API use.

The internal account API (`/internal/accounts/...`) lets the hospital's admin service create patients and doctors and reset passwords. Every request needs the service token from the `INTERNAL_API_TOKEN` environment variable in the `X-Internal-Token` header; without the variable the API is disabled and answers `503`. The public frontend never calls it, and it is left out of the public API documentation at `/docs`. Requests, responses and errors are described in the [API contract](../../docs/api-contract.md#internal-account-api-web-backend).

```bash
INTERNAL_API_TOKEN=change-me uvicorn web_backend.main:app --reload
```

## Overbooking

Before booking, `POST /appointments` asks the overbooking service (`OVERBOOKING_SERVICE_URL`, default `http://localhost:8001`) for a `/booking-decision`. A rejected booking returns `409`. If the service does not answer within 3 seconds or returns an error, empty slots are still booked but booked slots are never overbooked. A slot that has reached its `max_patients` is rejected without asking the service.

`GET /slots` marks a slot `available` while it is below capacity, so partly booked slots can be requested as extra appointments; the service decides when the patient books.

After a booking or a cancellation is saved, the web backend sends `/events/appointment-booked` or `/events/appointment-cancelled` so the service schedules or cancels the confirmation and reminder messages. The events are sent after the response; if one fails it is logged and the booking change stays.
