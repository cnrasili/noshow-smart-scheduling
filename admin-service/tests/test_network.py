from ipaddress import ip_network

import pytest
from fastapi.testclient import TestClient

from admin_service.config import Settings
from admin_service.main import app
from admin_service.network import is_allowed

NETWORKS = [ip_network("127.0.0.0/8"), ip_network("10.20.0.0/16"), ip_network("::1/128")]


@pytest.mark.parametrize(
    ("host", "allowed"),
    [
        ("127.0.0.1", True),
        ("10.20.3.4", True),
        ("::1", True),
        ("10.21.0.1", False),
        ("203.0.113.7", False),
        ("testclient", False),
        (None, False),
    ],
)
def test_is_allowed(host, allowed):
    assert is_allowed(host, NETWORKS) is allowed


def test_networks_are_read_from_a_comma_separated_list(monkeypatch: pytest.MonkeyPatch):
    monkeypatch.setenv("ADMIN_ALLOWED_NETWORKS", "10.0.0.0/8, 192.168.1.0/24")
    assert Settings().allowed_networks == [ip_network("10.0.0.0/8"), ip_network("192.168.1.0/24")]


def test_default_allows_only_the_local_machine():
    assert Settings().allowed_networks == [ip_network("127.0.0.0/8"), ip_network("::1/128")]


@pytest.mark.parametrize("path", ["/login", "/kpi", "/health", "/static/admin.css"])
def test_outside_clients_are_rejected_before_any_page(path: str):
    with TestClient(app, client=("203.0.113.7", 40000)) as outside:
        response = outside.get(path)
    assert response.status_code == 403
    assert "hastane iç ağından" in response.text


def test_forwarded_headers_do_not_grant_access():
    with TestClient(app, client=("203.0.113.7", 40000)) as outside:
        response = outside.get("/login", headers={"X-Forwarded-For": "127.0.0.1"})
    assert response.status_code == 403


def test_inside_clients_reach_the_login_page(client: TestClient):
    assert client.get("/login").status_code == 200
