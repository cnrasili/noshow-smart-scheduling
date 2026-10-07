import json
import re
from datetime import UTC, date, datetime

from fastapi.testclient import TestClient

KPIS = {
    "utilization": 0.6,
    "idle_minutes": 24.0,
    "overtime_minutes": 0.0,
    "mean_wait_minutes": 3.5,
    "overbooked_slots": 1,
    "patients_seen": 6,
}


def test_kpi_page_shows_selected_doctor_and_day(client: TestClient, log_in, overbooking):
    overbooking.kpis[(1, date(2026, 11, 10))] = KPIS
    overbooking.kpis[(1, date(2026, 11, 9))] = {**KPIS, "utilization": 0.5}
    log_in()
    html = client.get("/kpi", params={"doctor_id": 1, "date": "2026-11-10"}).text
    assert "Dr. Ada · 10 November 2026" in html
    assert "60.0%" in html
    data = json.loads(re.search(r'id="kpi-data">(.*?)</script>', html).group(1))
    assert [row["date"] for row in data] == ["2026-11-09", "2026-11-10"]
    assert data[-1] == {"date": "2026-11-10", "utilization": 60.0, "idle": 24.0, "overtime": 0.0}


def test_kpi_page_defaults_to_first_doctor_and_today(client: TestClient, log_in, clock):
    # 22:00 UTC is already 11 November in the clinic
    clock.now = datetime(2026, 11, 10, 22, 0, tzinfo=UTC)
    log_in()
    html = client.get("/kpi").text
    assert "Dr. Ada · 11 November 2026" in html
    assert "No slots on this date." in html


def test_kpi_page_shows_ab_summary(client: TestClient, log_in):
    log_in()
    html = client.get("/kpi").text
    assert "Reminder A/B test" in html
    assert "15.0%" in html and "25.0%" in html
    assert "p = 0.258" in html


def test_kpi_page_when_overbooking_service_is_down(client: TestClient, log_in, overbooking):
    overbooking.available = False
    log_in()
    response = client.get("/kpi")
    assert response.status_code == 200
    assert "The overbooking service is not reachable" in response.text


def test_kpi_page_needs_no_external_scripts(client: TestClient, log_in, overbooking):
    overbooking.kpis[(1, date(2026, 11, 10))] = KPIS
    log_in()
    html = client.get("/kpi", params={"doctor_id": 1, "date": "2026-11-10"}).text
    assert re.findall(r'src="(https?://[^"]+)"', html) == [
        "https://admin.test/static/chart.umd.min.js",
        "https://admin.test/static/kpi.js",
    ]


def test_assets_are_served(client: TestClient):
    for name in ["admin.css", "kpi.js", "chart.umd.min.js"]:
        assert client.get(f"/static/{name}").status_code == 200


def test_audit_page_lists_events(client: TestClient, log_in):
    log_in(password="wrong password")
    log_in()
    html = client.get("/audit").text
    assert "login_failed" in html
    assert "admin@hospital.local" in html
    assert "127.0.0.1" in html


def test_security_headers(client: TestClient):
    headers = client.get("/login").headers
    assert headers["x-frame-options"] == "DENY"
    assert headers["cache-control"] == "no-store"
    assert "frame-ancestors 'none'" in headers["content-security-policy"]


def test_api_docs_are_disabled(client: TestClient):
    for path in ["/docs", "/redoc", "/openapi.json"]:
        assert client.get(path).status_code == 404
