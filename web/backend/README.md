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

## Demo Data

`web_backend.seed` creates a fictional clinic: four doctors in three branches (Dahiliye, Kardiyoloji, Göz Hastalıkları) with their own working hours, eight patients, the login accounts, slots from three weeks ago to two weeks ahead and a few example appointments per doctor. Running it again only adds missing doctors, patients and slots, so it also upgrades a database seeded by an earlier version.

```bash
python -m web_backend.seed
# or, with Docker Compose
docker compose exec web-backend python -m web_backend.seed
```

Doctors sign in at `/giris/hekim` (for example `doktor@demo.local`; the others are printed by the seed command) and patients at `/giris/hasta` (for example `ayse@demo.local`). All demo accounts use the password `demo1234`; these are local demo values only.

## Authentication

`POST /auth/login` takes the e-mail, the password and the role of the login form (`patient` or `doctor`); an account can only sign in through its own form, and a mismatch gets the same `401` as a wrong password. It returns a bearer token that is valid for 12 hours; send it as `Authorization: Bearer <token>`. Passwords are hashed with scrypt and only a hash of each token is stored (`user_accounts` and `auth_sessions` tables).

## Overbooking

Before booking, `POST /appointments` asks the overbooking service (`OVERBOOKING_SERVICE_URL`, default `http://localhost:8001`) for a `/booking-decision`. A rejected booking returns `409`. If the service does not answer within 3 seconds or returns an error, empty slots are still booked but booked slots are never overbooked. A slot that has reached its `max_patients` is rejected without asking the service.

`GET /slots` marks a slot `available` while it is below capacity, so partly booked slots can be requested as extra appointments; the service decides when the patient books.

After a booking or a cancellation is saved, the web backend sends `/events/appointment-booked` or `/events/appointment-cancelled` so the service schedules or cancels the confirmation and reminder messages. The events are sent after the response; if one fails it is logged and the booking change stays.
