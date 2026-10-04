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

`web_backend.seed` creates a fictional clinic: one doctor working weekdays 09:00–12:00, eight patients, their login accounts, slots from a week ago to two weeks ahead and a few example appointments. Running it again only adds missing slots.

```bash
python -m web_backend.seed
# or, with Docker Compose
docker compose exec web-backend python -m web_backend.seed
```

Sign in as `doktor@demo.local` or as a patient such as `ayse@demo.local`. All demo accounts use the password `demo1234`; these are local demo values only.

## Authentication

`POST /auth/login` returns a bearer token that is valid for 12 hours; send it as `Authorization: Bearer <token>`. Passwords are hashed with scrypt and only a hash of each token is stored (`user_accounts` and `auth_sessions` tables).

## Overbooking

Before booking, `POST /appointments` asks the overbooking service (`OVERBOOKING_SERVICE_URL`, default `http://localhost:8001`) for a `/booking-decision`. A rejected booking returns `409`. If the service does not answer within 3 seconds or returns an error, empty slots are still booked but booked slots are never overbooked. A slot that has reached its `max_patients` is rejected without asking the service.

`GET /slots` marks a slot `available` while it is below capacity, so partly booked slots can be requested as extra appointments; the service decides when the patient books.
