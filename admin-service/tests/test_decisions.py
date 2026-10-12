import json
import re
from datetime import UTC, date, datetime, timedelta

import pytest
from fastapi.testclient import TestClient
from sqlalchemy.orm import Session, sessionmaker

from admin_service.decisions import decision_kind
from noshow_db.models.core import Appointment, Patient, Slot
from noshow_db.models.service import BookingDecision

DAY = date(2026, 11, 9)
LATER = date(2026, 11, 11)
DOCTOR = 1


def utc(day: date, hour: int, minute: int) -> datetime:
    """A clinic time in Istanbul (UTC+3) as UTC."""
    return datetime(day.year, day.month, day.day, hour - 3, minute, tzinfo=UTC)


def decision(patient: Patient, slot: Slot, p: float, **kwargs) -> BookingDecision:
    values = {
        "allow": True,
        "overbook": False,
        "booked_p_noshow": None,
        "reason": "Slot is empty",
    } | kwargs
    return BookingDecision(
        patient_id=patient.id,
        slot_id=slot.id,
        booking_date=DAY - timedelta(days=5),
        p_noshow=p,
        threshold=0.3,
        model_version="test-v1",
        **values,
    )


@pytest.fixture
def clinic(session_factory: sessionmaker[Session]) -> None:
    """Dr. Ada's day: a granted extra appointment, a refusal and a booking without a decision."""
    with session_factory() as session:
        names = ["Ayşe Kaya", "Mehmet Demir", "Zeynep Çelik", "Ali Şahin"]
        ayse, mehmet, zeynep, ali = patients = [
            Patient(
                national_id=f"9999900{i:04d}",
                full_name=name,
                email=f"p{i}@example.com",
                age=40,
                gender="F",
            )
            for i, name in enumerate(names, start=1)
        ]
        first, second, empty, last, later = slots = [
            Slot(
                doctor_id=DOCTOR,
                start_at=utc(day, hour, minute),
                end_at=utc(day, hour, minute) + timedelta(minutes=20),
            )
            for day, hour, minute in [
                (DAY, 9, 0),
                (DAY, 9, 20),
                (DAY, 9, 40),
                (DAY, 10, 0),
                (LATER, 9, 0),
            ]
        ]
        session.add_all(patients + slots)
        session.flush()

        def book(patient: Patient, slot: Slot, attended: bool | None) -> None:
            session.add(
                Appointment(
                    patient_id=patient.id,
                    slot_id=slot.id,
                    appointment_date=slot.start_at.date(),
                    booking_date=DAY - timedelta(days=5),
                    attended=attended,
                )
            )

        book(ayse, first, False)
        book(mehmet, first, True)
        book(zeynep, second, True)
        book(ali, last, None)
        book(ayse, later, None)
        session.add_all(
            [
                decision(ayse, first, 0.62),
                decision(mehmet, first, 0.25, overbook=True, booked_p_noshow=0.62),
                decision(zeynep, second, 0.12),
                decision(
                    ali,
                    second,
                    0.40,
                    allow=False,
                    booked_p_noshow=0.12,
                    reason="Slot is booked; booked patient risk 0.12 < 0.30",
                ),
                decision(ayse, later, 0.62),
            ]
        )
        session.commit()


def chart(html: str) -> list[dict]:
    found = re.search(r'<script type="application/json" id="risk-data">(.*?)</script>', html)
    assert found, "risk chart data missing"
    return json.loads(found.group(1))


def test_decisions_page_needs_login(client: TestClient):
    response = client.get("/decisions", follow_redirects=False)
    assert response.headers["location"] == "/login"


def test_day_view_shows_risks_decisions_and_outcomes(client: TestClient, log_in, clinic):
    log_in()
    html = client.get(f"/decisions?doctor_id={DOCTOR}&date={DAY}").text
    assert '/decisions">Model kararları</a>' in html
    assert "09:00–09:20" in html and "Ayşe Kaya" in html
    assert "%62,0" in html and "%25,0" in html
    assert 'class="badge extra"' in html
    assert "Saatteki hastanın riski %62,0, eşik %30,0" in html
    # Ali was refused for Zeynep's slot and booked later without a logged decision
    assert "Reddedildi" in html
    assert "Saatteki hastanın riski eşiğin altında: %12,0, eşik %30,0" in html
    assert "Karar kaydı yok" in html
    assert "Gelmedi" in html and "Geldi" in html and "İşaretlenmedi" in html
    assert "Boş" in html


def test_future_appointments_are_upcoming(client: TestClient, log_in, clinic):
    log_in()
    html = client.get(f"/decisions?doctor_id={DOCTOR}&date={LATER}").text
    assert "Bekleniyor" in html


def test_period_summary_counts_decisions(client: TestClient, log_in, clinic):
    log_in()
    html = client.get(f"/decisions?doctor_id={DOCTOR}&date={DAY}").text
    assert "<span>Randevu talebi</span><strong>4</strong>" in html
    assert "<span>Normal randevu</span><strong>2</strong>" in html
    assert "<span>Ek randevu verildi</span><strong>1</strong>" in html
    assert "<span>Reddedilen talep</span><strong>1</strong>" in html
    assert "Saatteki hastanın riski eşiğin altında: 1" in html
    assert "Eşik %30,0 · model sürümü test-v1" in html


def test_risk_bands_compare_prediction_and_outcome(client: TestClient, log_in, clinic):
    log_in()
    bands = chart(client.get(f"/decisions?doctor_id={DOCTOR}&date={DAY}").text)
    assert len(bands) == 10
    assert bands[6] == {"label": "%60–70", "rate": 100.0, "predicted": 62.0, "count": 1}
    assert bands[2] == {"label": "%20–30", "rate": 0.0, "predicted": 25.0, "count": 1}
    assert bands[1] == {"label": "%10–20", "rate": 0.0, "predicted": 12.0, "count": 1}
    assert sum(band["count"] for band in bands) == 3


def test_extra_appointment_outcomes(client: TestClient, log_in, clinic):
    log_in()
    html = client.get(f"/decisions?doctor_id={DOCTOR}&date={DAY}").text
    rows = re.findall(r"<td>([^<]+)</td>\s*<td>(\d+)</td>", html)
    assert ("En az bir hasta gelmedi; boşluk dolduruldu", "1") in rows
    assert ("Hepsi geldi; bekleme ya da fazla mesai oluştu", "0") in rows


def test_empty_log(client: TestClient, log_in):
    log_in()
    html = client.get("/decisions").text
    assert "Bu dönemde karar kaydı yok." in html
    assert "Bu dönemde geliş kaydı girilmiş randevu yok." in html
    assert "Bu dönemde ek randevu yok." in html
    assert "decisions.js" not in html


@pytest.mark.parametrize(
    ("reason", "kind"),
    [
        ("Slot is full (2/2 patients)", "full"),
        (
            "Slot is booked; booked patient risk 0.40 >= 0.30; daily overbook limit reached (2/2)",
            "limit",
        ),
        ("Patient is already booked in this slot", "duplicate"),
        ("Slot is booked; booked patient risk 0.12 < 0.30", "low_risk"),
    ],
)
def test_refusal_kinds(reason: str, kind: str):
    refusal = BookingDecision(allow=False, overbook=False, reason=reason)
    assert decision_kind(refusal) == kind
