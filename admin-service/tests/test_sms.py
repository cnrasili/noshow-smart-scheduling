from datetime import UTC, datetime, timedelta

import pytest
from fastapi.testclient import TestClient
from sqlalchemy.orm import Session, sessionmaker

from noshow_db.models.core import Patient
from noshow_db.models.service import Message

# 10 November 2026, 11:00 in Istanbul
SENT = datetime(2026, 11, 10, 8, 0, tzinfo=UTC)
START = datetime(2026, 11, 12, 6, 15, tzinfo=UTC)
CONFIRMATION = "Randevunuz alındı."
REMINDER = "Randevunuzu hatırlatırız."


def message(patient_id: int, appointment_id: int, kind: str, body: str, **values) -> Message:
    return Message(
        appointment_id=appointment_id,
        patient_id=patient_id,
        kind=kind,
        body=body,
        appointment_start=START,
        **({"send_at": SENT, "status": "sent", "attempts": 1, "sent_at": SENT} | values),
    )


@pytest.fixture
def inbox(session_factory: sessionmaker[Session]) -> None:
    """Two dataset patients' messages and one of a patient without a patient number."""
    with session_factory() as session:
        first, second, unnumbered = patients = [
            Patient(
                patient_number=number,
                full_name=f"Hasta {number}" if number else "Patient",
                email=f"{number or 'x'}@hasta.sehirhastanesi.example",
                age=33,
                gender="F",
            )
            for number in ["93779.52927", "1421986987763", None]
        ]
        session.add_all(patients)
        session.flush()
        session.add_all(
            [
                message(first.id, 1, "confirmation", CONFIRMATION),
                message(
                    first.id,
                    1,
                    "reminder",
                    REMINDER,
                    send_at=START - timedelta(hours=24),
                    status="pending",
                    attempts=0,
                    sent_at=None,
                ),
                message(second.id, 2, "confirmation", "İkinci hasta."),
                message(unnumbered.id, 3, "confirmation", "Numarasız.", status="failed"),
            ]
        )
        session.commit()


def test_sms_page_needs_login(client: TestClient):
    response = client.get("/sms", follow_redirects=False)
    assert response.headers["location"] == "/login"


def test_sms_page_lists_messages_by_patient_number(client: TestClient, log_in, inbox):
    log_in()
    html = client.get("/sms").text
    assert "Hasta 93779.52927" in html
    assert "Hasta 1421986987763" in html
    assert CONFIRMATION in html and REMINDER in html
    assert "Onay" in html and "Hatırlatma" in html
    assert "Gönderildi" in html and "Bekliyor" in html and "Gönderilemedi" in html
    # Sent messages show their sending time, pending ones the planned time
    assert "10.11.2026 11:00:00" in html
    assert "11.11.2026 09:15:00" in html
    # Planned reminder first, as the latest sending time
    assert html.index(REMINDER) < html.index(CONFIRMATION)


def test_sms_page_filters_by_patient_number(client: TestClient, log_in, inbox):
    log_in()
    html = client.get("/sms", params={"q": "9377"}).text
    assert CONFIRMATION in html
    assert "İkinci hasta." not in html
    assert "Numarasız." not in html


def test_sms_page_without_messages(client: TestClient, log_in):
    log_in()
    assert "SMS bulunamadı." in client.get("/sms").text


def test_navigation_links_to_the_sms_inbox(client: TestClient, log_in):
    log_in()
    assert '/sms">SMS kutusu</a>' in client.get("/audit").text
