# Admin Service

Hospital administration screen, separate from the hospital website and the booking system. Administrators log in here to see the schedule KPIs and the reminder A/B test, and to create patient and doctor accounts; patients and doctors cannot register themselves.

## Tech Stack

- Python, FastAPI
- Jinja2 server-rendered pages, Chart.js (served by the service, no internet access needed)
- PostgreSQL through the shared [`db`](../db/) package

## Security

| Measure | Implementation |
|---|---|
| Separate accounts | Administrators are stored in `admin_users`, not in the website's `user_accounts`; patient and doctor accounts cannot log in here. There is no registration page. |
| Internal network only | Requests from addresses outside `ADMIN_ALLOWED_NETWORKS` get 403 before any page, including the login page. Forwarded headers are ignored, so a client cannot claim an internal address. In Docker Compose the port is published on `127.0.0.1` only. |
| Passwords | scrypt hashes; at least 12 characters. A wrong password and an unknown email get the same answer. |
| Sessions | Random token in an HttpOnly, Secure, SameSite=Strict cookie; only its SHA-256 hash is stored. Sessions expire after `ADMIN_SESSION_MINUTES`. |
| Failed logins | After `ADMIN_MAX_FAILED_LOGINS` failures of one email or one client address within `ADMIN_LOCKOUT_MINUTES`, the login is locked for that window. |
| Audit log | Logins, failed logins, locked logins, logouts, created accounts, password resets and rejected account requests are recorded with time, administrator and client address, and shown at `/audit`. |
| Forms | Every form that changes data carries a token bound to the session (CSRF protection), on top of the SameSite=Strict cookie. |
| Initial passwords | Generated randomly for new accounts and password resets, shown once to the administrator and never stored in plain text or written to the audit log. |
| Browser headers | Content Security Policy without inline scripts, no framing, no caching, no referrer. API docs are disabled. |

### Limitations

A real hospital would also place the admin service behind a VPN or on a separate internal network, serve it over HTTPS and require two-factor login. These are outside the scope of this project; locally, the loopback binding and the network allowlist show the same restriction.

## Pages

| Path | Content |
|---|---|
| `/login` | Administrator login |
| `/kpi` | Schedule KPIs per doctor and day, the last days as chart and table, and the reminder A/B test |
| `/decisions` | The model's predicted no-show risks and the booking decisions: a doctor's slots on a day with each patient's risk, the decision and the outcome; for the last 30 days the decisions by kind, the actual no-show rate per predicted risk band, and the outcomes of slots with an extra appointment |
| `/patients` | Patients with search by name or national ID number; password reset for patients with a login account |
| `/patients/new` | Create a patient account |
| `/doctors` | Doctors with department, working hours and password reset |
| `/doctors/new` | Create a doctor account with weekly working hours; slots are opened for the next two weeks |
| `/audit` | The latest audit log events |

KPIs and the A/B summary come from the overbooking service (`GET /kpi`, `GET /ab/summary`, see the [API contract](../docs/api-contract.md)); the admin service does not compute them itself. The decisions page reads the overbooking service's decision log (`booking_decisions`) and the appointments from the database.

Patient and doctor lists are read from the database. Accounts are created and passwords reset through the web backend's internal account API, which owns the account rules (national ID check, unique email, password hashing); see the [API contract](../docs/api-contract.md#internal-account-api-web-backend).

## Setup

With Docker Compose the service starts with the others at http://localhost:8002. Create the first administrator; the password is asked twice:

```bash
docker compose exec admin-service python -m admin_service.create_admin --email admin@hospital.local
```

Account management needs the same secret in the web backend and the admin service. Copy `.env.example` to `.env`, set `INTERNAL_API_TOKEN` to a random value and restart:

```bash
python -c "import secrets; print(secrets.token_urlsafe(32))"
docker compose up -d
```

Without Docker:

```bash
pip install -e ../db -e ".[dev]"
uvicorn admin_service.main:app --port 8002 --no-proxy-headers
```

`DATABASE_URL` must point to the shared database with the migrations applied.

## Settings

Environment variables:

| Variable | Default | Meaning |
|---|---|---|
| `ADMIN_ALLOWED_NETWORKS` | `127.0.0.0/8,::1/128` | Comma-separated client networks (CIDR) allowed to reach the service |
| `ADMIN_OVERBOOKING_SERVICE_URL` | `http://localhost:8001` | Overbooking service address on the internal network |
| `ADMIN_WEB_BACKEND_URL` | `http://localhost:8000` | Web backend address for the internal account API |
| `ADMIN_INTERNAL_API_TOKEN` | empty | Service token of the internal account API; account management is disabled while it is empty. Docker Compose passes `INTERNAL_API_TOKEN` from `.env`. |
| `ADMIN_SESSION_MINUTES` | 60 | Session lifetime |
| `ADMIN_COOKIE_SECURE` | true | Send the session cookie only over HTTPS; browsers also accept it on `http://localhost` |
| `ADMIN_MAX_FAILED_LOGINS` | 5 | Failed logins that lock the login |
| `ADMIN_LOCKOUT_MINUTES` | 15 | Window for counting failed logins |
| `ADMIN_DASHBOARD_DAYS` | 7 | Days shown in the KPI chart and table |

In Docker Compose, requests from the host do not arrive from `127.0.0.1`: on Windows and Linux they come from the Docker network gateway (`172.16.0.0/12`), on Docker Desktop for Mac from its VM network (`192.168.65.0/24`). The Compose file therefore also allows these ranges; the loopback-only port binding keeps other machines out.

## Tests

```bash
pytest admin-service
```
