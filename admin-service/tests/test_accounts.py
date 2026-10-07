import re
from datetime import time

import pytest
from fastapi.testclient import TestClient
from sqlalchemy import select
from sqlalchemy.orm import Session, sessionmaker

from admin_service.security import csrf_token, generate_password, hash_password
from noshow_db.models.admin import AdminAuditLog
from noshow_db.models.core import DoctorSchedule, Patient, UserAccount

# Fictional national ID numbers of the web backend demo pattern
AYSE = "99999000184"
MEHMET = "99999000252"

PATIENT_FORM = {
    "national_id": "99999000320",
    "full_name": "Zeynep Çelik",
    "email": "zeynep@demo.local",
    "age": "22",
    "gender": "F",
    "handcap": "0",
    "scholarship": "on",
}
DOCTOR_FORM = {
    "full_name": "Dr. Ece Tan",
    "specialty": "Dahiliye",
    "email": "ece.tan@demo.local",
    "start_0": "09:00",
    "end_0": "12:00",
    "start_2": "13:00",
    "end_2": "16:00",
}


@pytest.fixture(autouse=True)
def clinic(session_factory: sessionmaker[Session]) -> None:
    with session_factory() as session:
        ayse = Patient(
            national_id=AYSE, full_name="Ayşe Kaya", email="ayse@demo.local", age=34, gender="F"
        )
        mehmet = Patient(
            national_id=MEHMET, full_name="Mehmet Demir", email="m@demo.local", age=58, gender="M"
        )
        session.add_all([ayse, mehmet])
        session.flush()
        session.add_all(
            [
                UserAccount(
                    id=7,
                    email="ayse@demo.local",
                    password_hash=hash_password("demo1234"),
                    role="patient",
                    patient_id=ayse.id,
                ),
                UserAccount(
                    id=8,
                    email="ada@demo.local",
                    password_hash=hash_password("demo1234"),
                    role="doctor",
                    doctor_id=1,
                ),
                DoctorSchedule(doctor_id=1, weekday=0, start_time=time(9), end_time=time(12)),
            ]
        )
        session.commit()


def form_token(client: TestClient) -> str:
    return csrf_token(client.cookies["admin_session"])


def post(client: TestClient, path: str, data: dict | None = None):
    return client.post(path, data={**(data or {}), "csrf_token": form_token(client)})


def audit(session_factory: sessionmaker[Session]) -> list[tuple[str, str | None]]:
    with session_factory() as session:
        return [
            (row.action, row.detail)
            for row in session.scalars(select(AdminAuditLog).order_by(AdminAuditLog.id))
        ]


def initial_password(html: str) -> str:
    return re.findall(r"<code>([^<]+)</code>", html)[-1]


@pytest.mark.parametrize("path", ["/patients", "/doctors", "/patients/new", "/doctors/new"])
def test_pages_need_login(client: TestClient, path: str):
    assert client.get(path, follow_redirects=False).headers["location"] == "/login"


def test_patient_list_and_search(client: TestClient, log_in):
    log_in()
    html = client.get("/patients").text
    assert "Ayşe Kaya" in html and "Mehmet Demir" in html
    # Ayşe has a login account, Mehmet does not
    assert html.count("Şifreyi sıfırla") == 1
    assert "Giriş hesabı yok" in html
    by_name = client.get("/patients", params={"q": "ayşe"}).text
    assert "Ayşe Kaya" in by_name and "Mehmet Demir" not in by_name
    by_id = client.get("/patients", params={"q": "999990002"}).text
    assert "Mehmet Demir" in by_id and "Ayşe Kaya" not in by_id


def test_doctor_list_shows_department_hours_and_account(client: TestClient, log_in):
    log_in()
    html = client.get("/doctors").text
    assert "Dr. Ada" in html and "Dr. Bora" in html
    assert "ada@demo.local" in html
    assert "Pzt 09:00–12:00" in html
    assert html.count("Şifreyi sıfırla") == 1


def test_create_patient(client: TestClient, log_in, accounts, session_factory):
    log_in()
    response = post(client, "/patients/new", PATIENT_FORM)
    assert response.status_code == 200
    kind, sent = accounts.requests[0]
    assert kind == "patient"
    assert sent | {"password": "x"} == {
        "national_id": "99999000320",
        "full_name": "Zeynep Çelik",
        "email": "zeynep@demo.local",
        "age": 22,
        "gender": "F",
        "handcap": 0,
        "scholarship": True,
        "hipertension": False,
        "diabetes": False,
        "alcoholism": False,
        "password": "x",
    }
    # The generated password is shown once and never written to the audit log
    assert initial_password(response.text) == sent["password"]
    assert "99999000320" in response.text
    assert audit(session_factory)[-1] == ("patient_created", "hesap 101, hasta 1101")
    assert sent["password"] not in str(audit(session_factory))


def test_create_patient_needs_the_form_token(client: TestClient, log_in, accounts):
    log_in()
    assert client.post("/patients/new", data=PATIENT_FORM).status_code == 403
    assert accounts.requests == []


def test_rejected_patient_keeps_the_form(client: TestClient, log_in, accounts, session_factory):
    accounts.reject = "Bu T.C. kimlik numarası zaten kayıtlı."
    log_in()
    response = post(client, "/patients/new", PATIENT_FORM)
    assert response.status_code == 400
    assert "Bu T.C. kimlik numarası zaten kayıtlı." in response.text
    assert 'value="Zeynep Çelik"' in response.text
    assert audit(session_factory)[-1] == (
        "account_rejected",
        "Bu T.C. kimlik numarası zaten kayıtlı.",
    )


def test_invalid_age_is_not_sent(client: TestClient, log_in, accounts):
    log_in()
    response = post(client, "/patients/new", {**PATIENT_FORM, "age": "old"})
    assert response.status_code == 400
    assert "tam sayı olmalıdır" in response.text
    assert accounts.requests == []


def test_create_doctor(client: TestClient, log_in, accounts, session_factory):
    log_in()
    response = post(client, "/doctors/new", DOCTOR_FORM)
    assert response.status_code == 200
    kind, sent = accounts.requests[0]
    assert kind == "doctor"
    assert sent["working_hours"] == [
        {"weekday": 0, "start_time": "09:00", "end_time": "12:00"},
        {"weekday": 2, "start_time": "13:00", "end_time": "16:00"},
    ]
    assert initial_password(response.text) == sent["password"]
    assert "18 slot açıldı" in response.text
    assert audit(session_factory)[-1] == ("doctor_created", "hesap 101, hekim 1101")


@pytest.mark.parametrize(
    ("changes", "message"),
    [
        ({"end_2": ""}, "Çarşamba için başlangıç ve bitiş saatini birlikte girin"),
        ({"start_0": "", "end_0": "", "start_2": "", "end_2": ""}, "En az bir çalışma günü girin"),
    ],
)
def test_doctor_hours_are_checked(client: TestClient, log_in, accounts, changes, message):
    log_in()
    response = post(client, "/doctors/new", {**DOCTOR_FORM, **changes})
    assert response.status_code == 400
    assert message in response.text
    assert accounts.requests == []


def test_reset_password(client: TestClient, log_in, accounts, session_factory):
    log_in()
    response = post(client, "/accounts/7/password")
    [(kind, sent)] = accounts.requests
    assert (kind, sent["account_id"]) == ("reset", 7)
    assert len(sent["password"]) == 14
    assert initial_password(response.text) == sent["password"]
    assert AYSE in response.text
    assert audit(session_factory)[-1] == ("password_reset", "hesap 7")


def test_reset_password_of_unknown_account(client: TestClient, log_in, accounts):
    log_in()
    assert post(client, "/accounts/999/password").status_code == 404
    assert accounts.requests == []


def test_disabled_account_management(client: TestClient, log_in, accounts):
    accounts.enabled = False
    log_in()
    listing = client.get("/patients").text
    assert "Hesap yönetimi kapalı" in listing
    assert "Hasta hesabı aç" not in listing
    response = post(client, "/patients/new", PATIENT_FORM)
    assert response.status_code == 400
    assert "Hesap yönetimi kapalı" in response.text


def test_generated_passwords():
    passwords = {generate_password() for _ in range(50)}
    assert len(passwords) == 50
    assert all(len(p) == 14 and not set(p) & set("0O1lI") for p in passwords)
