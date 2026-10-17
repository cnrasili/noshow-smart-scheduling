import re
from datetime import time

import pytest
from fastapi.testclient import TestClient
from sqlalchemy import select
from sqlalchemy.orm import Session, sessionmaker

from admin_service.security import csrf_token, generate_password, hash_password
from noshow_db.models.admin import AdminAuditLog
from noshow_db.models.core import DoctorSchedule, Patient, UserAccount

# Patients of the public dataset, identified by the dataset's patient number
WITH_ACCOUNT = "29872499824296"
WITHOUT_ACCOUNT = "93779.52927"
# A patient created before the dataset was loaded; not in the dataset
OUTSIDE = "Mehmet Demir"
NAMES = [f"Hasta {WITH_ACCOUNT}", f"Hasta {WITHOUT_ACCOUNT}", OUTSIDE]


def dataset_patient(number: str, age: int) -> Patient:
    return Patient(
        patient_number=number,
        full_name=f"Hasta {number}",
        email=f"{number}@hasta.sehirhastanesi.example",
        age=age,
        gender="F",
    )


@pytest.fixture(autouse=True)
def clinic(session_factory: sessionmaker[Session]) -> None:
    with session_factory() as session:
        with_account = dataset_patient(WITH_ACCOUNT, 62)
        outside = Patient(full_name=OUTSIDE, email="m@demo.local", age=58, gender="M")
        session.add_all([with_account, dataset_patient(WITHOUT_ACCOUNT, 33), outside])
        session.flush()
        session.add_all(
            [
                UserAccount(
                    id=7,
                    email=with_account.email,
                    password_hash=hash_password("demo1234"),
                    role="patient",
                    patient_id=with_account.id,
                ),
                # The department's staff account and working hours
                UserAccount(
                    id=8,
                    email="aile.hekimligi",
                    password_hash=hash_password("demo1234"),
                    role="doctor",
                    doctor_id=1,
                ),
                DoctorSchedule(doctor_id=1, weekday=0, start_time=time(9), end_time=time(12)),
            ]
        )
        session.commit()


def account_path(session_factory: sessionmaker[Session], name: str) -> str:
    with session_factory() as session:
        patient_id = session.scalars(select(Patient.id).where(Patient.full_name == name)).one()
    return f"/patients/{patient_id}/account"


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


@pytest.mark.parametrize("path", ["/patients", "/department"])
def test_pages_need_login(client: TestClient, path: str):
    assert client.get(path, follow_redirects=False).headers["location"] == "/login"


def test_patient_list_and_search(client: TestClient, log_in):
    log_in()
    html = client.get("/patients").text
    assert all(name in html for name in NAMES)
    assert f"<td>{WITHOUT_ACCOUNT}</td>" in html
    # One patient has an account, one dataset patient can get one, Mehmet is not in the dataset
    assert html.count("Şifreyi sıfırla") == 1
    assert html.count("Giriş hesabı aç") == 1
    assert "Giriş hesabı yok" in html
    by_name = client.get("/patients", params={"q": "mehmet"}).text
    assert OUTSIDE in by_name and f"Hasta {WITH_ACCOUNT}" not in by_name
    by_number = client.get("/patients", params={"q": "93779.5"}).text
    assert f"Hasta {WITHOUT_ACCOUNT}" in by_number and OUTSIDE not in by_number


@pytest.mark.parametrize("q", ["%", "_", "\\", "9999%", "Ay_e", "%ehmet"])
def test_patient_search_has_no_wildcards(client: TestClient, log_in, q: str):
    log_in()
    html = client.get("/patients", params={"q": q}).text
    assert not any(name in html for name in NAMES)


WILDCARD_NAMES = ["Yüzde%Bir", "Alt_Çizgi", "Ters\\Bölü"]


@pytest.mark.parametrize(("q", "name"), list(zip(["%", "_", "\\"], WILDCARD_NAMES, strict=True)))
def test_patient_search_finds_names_with_wildcard_characters(
    client: TestClient, log_in, session_factory: sessionmaker[Session], q: str, name: str
):
    with session_factory() as session:
        session.add_all(
            Patient(
                full_name=full_name,
                email=f"wildcard{n}@demo.local",
                age=40,
                gender="F",
            )
            for n, full_name in enumerate(WILDCARD_NAMES)
        )
        session.commit()
    log_in()
    html = client.get("/patients", params={"q": q}).text
    shown = [n for n in [*WILDCARD_NAMES, *NAMES] if n in html]
    assert shown == [name]


def test_department_page_shows_working_hours_and_account(client: TestClient, log_in):
    log_in()
    html = client.get("/department").text
    assert "Aile Hekimliği" in html
    assert "Pazartesi" in html and "09:00–12:00" in html
    assert "aile.hekimligi" in html
    assert html.count("Şifreyi sıfırla") == 1
    assert "General Practice" not in html


@pytest.mark.parametrize("path", ["/doctors", "/doctors/new"])
def test_doctor_pages_are_gone(client: TestClient, log_in, path: str):
    log_in()
    assert client.get(path).status_code == 404


def test_open_account_for_a_dataset_patient(client: TestClient, log_in, accounts, session_factory):
    log_in()
    response = post(client, account_path(session_factory, f"Hasta {WITHOUT_ACCOUNT}"))
    assert response.status_code == 200
    [(kind, sent)] = accounts.requests
    assert kind == "patient"
    assert sent == {"patient_number": WITHOUT_ACCOUNT, "password": sent["password"]}
    # The generated password is shown once and never written to the audit log
    assert initial_password(response.text) == sent["password"]
    assert WITHOUT_ACCOUNT in response.text
    assert audit(session_factory)[-1] == ("patient_created", "hesap 101, hasta 1101")
    assert sent["password"] not in str(audit(session_factory))


def test_open_account_needs_the_form_token(client: TestClient, log_in, accounts, session_factory):
    log_in()
    path = account_path(session_factory, f"Hasta {WITHOUT_ACCOUNT}")
    assert client.post(path).status_code == 403
    assert accounts.requests == []


def test_accounts_only_for_dataset_patients(client: TestClient, log_in, accounts, session_factory):
    log_in()
    outside = post(client, account_path(session_factory, OUTSIDE))
    unknown = post(client, "/patients/999/account")
    assert (outside.status_code, unknown.status_code) == (404, 404)
    assert "yalnızca veri setindeki hastalara" in outside.text
    assert accounts.requests == []


def test_rejected_account_is_shown_and_logged(
    client: TestClient, log_in, accounts, session_factory
):
    accounts.reject = "Bu hastanın zaten giriş hesabı var."
    log_in()
    response = post(client, account_path(session_factory, f"Hasta {WITH_ACCOUNT}"))
    assert response.status_code == 400
    assert "Bu hastanın zaten giriş hesabı var." in response.text
    assert audit(session_factory)[-1] == ("account_rejected", "Bu hastanın zaten giriş hesabı var.")


def test_reset_password(client: TestClient, log_in, accounts, session_factory):
    log_in()
    response = post(client, "/accounts/7/password")
    [(kind, sent)] = accounts.requests
    assert (kind, sent["account_id"]) == ("reset", 7)
    assert len(sent["password"]) == 14
    assert initial_password(response.text) == sent["password"]
    assert WITH_ACCOUNT in response.text and "Hasta numarası" in response.text
    assert audit(session_factory)[-1] == ("password_reset", "hesap 7")


def test_reset_password_of_the_department_account(client: TestClient, log_in, accounts):
    log_in()
    response = post(client, "/accounts/8/password")
    [(kind, sent)] = accounts.requests
    assert (kind, sent["account_id"]) == ("reset", 8)
    assert "Aile Hekimliği" in response.text
    assert "aile.hekimligi" in response.text and "Giriş adı" in response.text


def test_reset_password_of_unknown_account(client: TestClient, log_in, accounts):
    log_in()
    assert post(client, "/accounts/999/password").status_code == 404
    assert accounts.requests == []


def test_disabled_account_management(client: TestClient, log_in, accounts, session_factory):
    accounts.enabled = False
    log_in()
    listing = client.get("/patients").text
    assert "Hesap yönetimi kapalı" in listing
    assert "Giriş hesabı aç" not in listing
    department = client.get("/department").text
    assert "Hesap yönetimi kapalı" in department
    assert "Şifreyi sıfırla" not in department
    response = post(client, account_path(session_factory, f"Hasta {WITHOUT_ACCOUNT}"))
    assert response.status_code == 400
    assert "Hesap yönetimi kapalı" in response.text


def test_generated_passwords():
    passwords = {generate_password() for _ in range(50)}
    assert len(passwords) == 50
    assert all(len(p) == 14 and not set(p) & set("0O1lI") for p in passwords)
