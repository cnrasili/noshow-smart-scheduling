# Admin Service

Hospital administration screen, separate from the hospital website and the booking system. Administrators log in here to see the schedule KPIs and the reminder A/B test. Account management screens follow in a later step.

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
| Audit log | Logins, failed logins, locked logins and logouts are recorded with time, email and client address, and shown at `/audit`. |
| Browser headers | Content Security Policy without inline scripts, no framing, no caching, no referrer. API docs are disabled. |

### Limitations

A real hospital would also place the admin service behind a VPN or on a separate internal network, serve it over HTTPS and require two-factor login. These are outside the scope of this project; locally, the loopback binding and the network allowlist show the same restriction.

## Pages

| Path | Content |
|---|---|
| `/login` | Administrator login |
| `/kpi` | Schedule KPIs per doctor and day, the last days as chart and table, and the reminder A/B test |
| `/audit` | The latest audit log events |

KPIs and the A/B summary come from the overbooking service (`GET /kpi`, `GET /ab/summary`, see the [API contract](../docs/api-contract.md)); the admin service does not compute them itself.

## Setup

With Docker Compose the service starts with the others at http://localhost:8002. Create the first administrator; the password is asked twice:

```bash
docker compose exec admin-service python -m admin_service.create_admin --email admin@hospital.local
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
| `ADMIN_SESSION_MINUTES` | 60 | Session lifetime |
| `ADMIN_COOKIE_SECURE` | true | Send the session cookie only over HTTPS; browsers also accept it on `http://localhost` |
| `ADMIN_MAX_FAILED_LOGINS` | 5 | Failed logins that lock the login |
| `ADMIN_LOCKOUT_MINUTES` | 15 | Window for counting failed logins |
| `ADMIN_DASHBOARD_DAYS` | 7 | Days shown in the KPI chart and table |

In Docker Compose, requests from the host reach the container through the Docker network gateway, so the Compose file also allows the Docker address ranges; the loopback-only port binding keeps other machines out.

## Tests

```bash
pytest admin-service
```
