# Outpatient Appointment System: No-Show Prediction and Smart Scheduling

Outpatient clinics lose capacity when patients miss their appointments without notice, while overbooking every slot uniformly leads to congestion, long waiting times and physician overtime. This project builds a working appointment booking application in which a machine learning model estimates each patient's no-show probability at booking time. Slots are overbooked selectively, only where the no-show risk is high, and patients receive automated confirmation and reminder messages. The resulting schedules are evaluated with discrete-event simulation to show that both patient waiting time and physician idle time improve compared with fixed-interval booking, and the system reports utilization, idle time and overtime on an admin dashboard.

The project is developed as an interdisciplinary study combining industrial engineering (appointment template design, overbooking policy, simulation) and computer engineering (web application, model-serving API, reminder engine).

## Scope

- One outpatient clinic session with one physician and fixed-length appointment slots.
- The prediction model is trained on the public Medical Appointment No Shows dataset; the application and the simulation use simulated data.
- Selective overbooking is compared with fixed-interval booking.
- Real patient data and integration with hospital information systems are outside the scope.

## System Overview

```
[Web frontend] --> [Web backend] --HTTP--> [Overbooking service]
                        |                       |-- Feature builder --> No-show model --> p_noshow
                        |                       |-- Overbooking rule engine
                        |                       |-- Reminder scheduler --> Email (SMTP)
                        |                       |-- A/B assignment and logging
                        |                       `-- KPI calculator --> Admin dashboard
                        |                               |
                        `-------> [PostgreSQL] <--------'

[ML pipeline] --> model file --> Overbooking service
[Simulation]  <-- no-show probabilities + overbooking rule
```

## Tech Stack

| Layer | Technology |
|---|---|
| Web frontend | React 19, TypeScript, Vite |
| Web backend | FastAPI, Pydantic |
| Overbooking service | FastAPI, Pydantic, APScheduler, scikit-learn, joblib |
| KPI dashboard | Jinja2, Chart.js (served by the overbooking service) |
| Database | PostgreSQL 16, SQLAlchemy 2, Alembic |
| Email | SMTP; Mailpit in development |
| Prediction model | Python, pandas, scikit-learn, Jupyter |
| Simulation | Python, SimPy |
| Infrastructure | Docker Compose, GitHub Actions |
| Code quality | ruff, pytest, oxlint, Prettier |

## Repository Structure

| Folder | Content |
|---|---|
| [`web/frontend/`](web/frontend/) | Patient and doctor interfaces |
| [`web/backend/`](web/backend/) | Booking API, calendar/slot algorithm |
| [`overbooking-service/`](overbooking-service/) | Model-serving REST API, overbooking rule engine, reminder jobs, A/B logging, KPI dashboard |
| [`db/`](db/) | Shared SQLAlchemy models and Alembic migrations |
| [`ml/`](ml/) | Data preparation, no-show prediction model (logistic regression / random forest), AUC and calibration |
| [`simulation/`](simulation/) | Appointment template, overbooking policy, SimPy discrete-event simulation |
| [`docs/`](docs/) | Shared contracts between components: API, model features, KPI definitions |

## Getting Started

Requirements: Docker Desktop.

```bash
git clone https://github.com/cnrasili/noshow-smart-scheduling.git
cd noshow-smart-scheduling
docker compose up --build
```

| Service | URL |
|---|---|
| Web frontend | http://localhost:5173 |
| Web backend API docs | http://localhost:8000/docs |
| Overbooking service API docs | http://localhost:8001/docs |
| Mailpit (sent emails) | http://localhost:8025 |
| PostgreSQL | `localhost:5432` |

Default settings work without configuration. To change them, copy `.env.example` to `.env`.

Each component can also be run without Docker; see its README.

### Troubleshooting

| Problem | Solution |
|---|---|
| `error during connect` or `cannot find the file specified` | Start Docker Desktop and wait until it is running. |
| `port is already allocated` | Copy `.env.example` to `.env` and change the port of that service, for example `DB_PORT=5433`. |
| Code changes are not picked up | File watching uses polling in Docker; wait a few seconds or restart the service with `docker compose restart <service>`. |
| Database schema is out of date | Run `docker compose up --build migrate`. |
| Start from a clean database | Run `docker compose down -v`. This deletes all local data. |

## Dataset

The prediction model is trained on the public [Medical Appointment No Shows](https://www.kaggle.com/datasets/joniarroba/noshowappointments) dataset (Hoppen, 2016), which contains about 110,000 appointments from public clinics in Vitória, Brazil.

The dataset is **not** stored in this repository. To use it:

1. Download the dataset from Kaggle.
2. Place the CSV file in `ml/data/raw/`.

The dataset is licensed under [CC BY-NC-SA 4.0](https://creativecommons.org/licenses/by-nc-sa/4.0/) by its author and is used for non-commercial academic purposes only.

## Shared Contracts

Components depend on each other through the documents in [`docs/`](docs/).

| Document | Between |
|---|---|
| [API contract](docs/api-contract.md) | Web backend and overbooking service |
| [Model features](docs/features.md) | Prediction model and overbooking service |
| [KPI definitions](docs/kpi-definitions.md) | Simulation and KPI dashboard |

## Workflow

- `main` always contains working code.
- Work on a feature branch, for example `feature/predict-api`, and merge through a pull request.
- Commit messages are one line in the form `type: Imperative short message`, for example `feat: Add prediction endpoint` or `fix: Correct lead time calculation`.
- Database changes go through Alembic migrations in [`db/`](db/).
- Never commit secrets. Copy `.env.example` to `.env` and fill in local values.
- CI runs linters, tests and the frontend build on every push and pull request.

## Course

LMMF405 Interdisciplinary Project, Fall 2026–2027, Department of Industrial Engineering (Eng), Istanbul Arel University.

## License

The source code is released under the [MIT License](LICENSE). The dataset is subject to its own license (see [Dataset](#dataset)).

## References

Hoppen, J. (2016). *Medical appointment no shows* [Data set]. Kaggle. https://www.kaggle.com/datasets/joniarroba/noshowappointments
