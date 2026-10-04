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
