# Overbooking Service

Decision service behind the booking application. It serves the no-show model, decides slot-level overbooking, sends confirmation and reminder messages, and reports schedule KPIs.

## Tech Stack

- FastAPI + Pydantic
- SQLAlchemy 2 through the shared [`db`](../db/) package
- scikit-learn and joblib for model serving
- APScheduler for reminder jobs
- Mailpit (SMTP) for confirmation and reminder emails in development
- Jinja2 + Chart.js for the KPI dashboard
- pytest

## Scope

- REST model-serving API called at booking time
- Rule engine for slot-level overbooking
- Scheduled confirmation and reminder jobs
- Logging for the reminder A/B comparison
- KPI dashboard: utilization, idle time, overtime

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
