from datetime import timedelta

from fastapi.testclient import TestClient
from sqlalchemy import select
from sqlalchemy.orm import Session, sessionmaker

from admin_service.security import csrf_token, hash_password
from noshow_db.models.admin import AdminAuditLog, AdminSession
from noshow_db.models.core import Patient, UserAccount

PASSWORD = "correct horse battery"


def actions(session_factory: sessionmaker[Session]) -> list[str]:
    with session_factory() as session:
        return list(session.scalars(select(AdminAuditLog.action).order_by(AdminAuditLog.id)))


def test_login_page_is_served(client: TestClient):
    response = client.get("/login")
    assert response.status_code == 200
    assert 'name="password"' in response.text
    assert "<title>Yönetici girişi · Şehir Hastanesi Yönetim Paneli</title>" in response.text
    assert "<h1>Şehir Hastanesi Yönetim Paneli</h1>" in response.text


def test_pages_need_login(client: TestClient):
    for path in ["/", "/kpi", "/audit"]:
        response = client.get(path, follow_redirects=False)
        assert response.status_code == 303
        assert response.headers["location"] == "/login"


def test_login_opens_kpi_page(client: TestClient, log_in, session_factory):
    response = log_in()
    assert response.status_code == 200
    assert response.url.path == "/kpi"
    assert "Randevu göstergeleri" in response.text
    assert "<title>Randevu göstergeleri · Şehir Hastanesi Yönetim Paneli</title>" in response.text
    assert "<strong>Şehir Hastanesi Yönetim Paneli</strong>" in response.text
    assert actions(session_factory) == ["login"]


def test_session_cookie_is_protected(client: TestClient, log_in):
    response = client.post(
        "/login",
        data={"email": "Admin@Hospital.local ", "password": PASSWORD},
        follow_redirects=False,
    )
    assert response.status_code == 303
    cookie = response.headers["set-cookie"].lower()
    assert "httponly" in cookie
    assert "secure" in cookie
    assert "samesite=strict" in cookie


def test_only_token_hash_is_stored(client: TestClient, log_in, session_factory):
    log_in()
    token = client.cookies["admin_session"]
    with session_factory() as session:
        stored = session.scalar(select(AdminSession.token_hash))
    assert stored != token and len(stored) == 64


def test_wrong_password_and_unknown_email_get_same_answer(
    client: TestClient, log_in, session_factory
):
    wrong = log_in(password="wrong password")
    unknown = log_in(email="nobody@hospital.local")
    assert wrong.status_code == unknown.status_code == 401
    assert "E-posta veya şifre hatalı." in wrong.text
    assert "E-posta veya şifre hatalı." in unknown.text
    assert actions(session_factory) == ["login_failed", "login_failed"]


def test_website_accounts_cannot_log_in(client: TestClient, log_in, session_factory):
    with session_factory() as session:
        # Fictional national ID number of the web backend demo pattern
        patient = Patient(
            national_id="99999000184", full_name="P", email="p@demo.local", age=30, gender="F"
        )
        session.add(patient)
        session.flush()
        session.add(
            UserAccount(
                email="p@demo.local",
                password_hash=hash_password(PASSWORD),
                role="patient",
                patient_id=patient.id,
            )
        )
        session.commit()
    assert log_in(email="p@demo.local").status_code == 401


def test_failed_logins_lock_the_login(client: TestClient, log_in, clock, session_factory):
    for _ in range(3):
        assert log_in(password="wrong password").status_code == 401
    locked = log_in()
    assert locked.status_code == 429
    assert "Çok fazla başarısız giriş denemesi" in locked.text
    assert actions(session_factory)[-1] == "login_locked"

    # The lock ends when the failures leave the window
    clock.now += timedelta(minutes=16)
    assert log_in().url.path == "/kpi"


def test_lock_also_counts_failures_from_the_same_address(client: TestClient, log_in):
    for n in range(3):
        log_in(email=f"guess{n}@hospital.local")
    assert log_in().status_code == 429


def test_session_expires(client: TestClient, log_in, clock):
    log_in()
    assert client.get("/kpi").url.path == "/kpi"
    clock.now += timedelta(minutes=61)
    assert client.get("/kpi").url.path == "/login"


def test_logout_ends_the_session(client: TestClient, log_in, session_factory):
    log_in()
    token = client.cookies["admin_session"]
    response = client.post("/logout", data={"csrf_token": csrf_token(token)})
    assert response.url.path == "/login"
    client.cookies.set("admin_session", token, domain="admin.test")
    assert client.get("/kpi").url.path == "/login"
    assert actions(session_factory) == ["login", "logout"]


def test_logout_needs_the_form_token(client: TestClient, log_in, session_factory):
    log_in()
    assert client.post("/logout").status_code == 403
    assert client.post("/logout", data={"csrf_token": "forged"}).status_code == 403
    assert client.get("/kpi").url.path == "/kpi"
    assert actions(session_factory) == ["login"]
