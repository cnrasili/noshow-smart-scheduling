from datetime import UTC, datetime, timedelta

import pytest

from noshow_db.models.service import Message

NOW = datetime(2030, 3, 1, 9, 0, tzinfo=UTC)


@pytest.fixture
def patient(make_patient, login):
    patient = make_patient(email="ayse@example.com")
    return patient, login("ayse@example.com")


def _message(patient_id: int, kind: str, status: str, minutes: int, appointment_id: int = 1):
    sent = NOW + timedelta(minutes=minutes)
    return Message(
        appointment_id=appointment_id,
        patient_id=patient_id,
        kind=kind,
        body=f"{kind} {status} {minutes}",
        appointment_start=NOW + timedelta(days=3),
        send_at=sent,
        status=status,
        sent_at=sent if status == "sent" else None,
    )


def test_patient_sees_own_sent_messages_newest_first(db, client, patient, make_patient) -> None:
    patient_row, headers = patient
    other = make_patient(email="other@example.com")
    db.add_all(
        [
            _message(patient_row.id, "confirmation", "sent", 0),
            _message(patient_row.id, "reminder", "sent", 60),
            _message(patient_row.id, "reminder", "pending", 120, appointment_id=2),
            _message(patient_row.id, "confirmation", "failed", 5, appointment_id=3),
            _message(patient_row.id, "reminder", "cancelled", 6, appointment_id=4),
            _message(other.id, "confirmation", "sent", 30, appointment_id=5),
        ]
    )
    db.commit()

    response = client.get("/patients/me/messages", headers=headers)

    assert response.status_code == 200
    assert response.json() == [
        {"kind": "reminder", "sent_at": "2030-03-01T10:00:00Z", "body": "reminder sent 60"},
        {"kind": "confirmation", "sent_at": "2030-03-01T09:00:00Z", "body": "confirmation sent 0"},
    ]


def test_messages_are_for_patients_only(client, make_department, login) -> None:
    make_department()

    response = client.get("/patients/me/messages", headers=login("aile.hekimligi"))

    assert response.status_code == 403
    assert client.get("/patients/me/messages").status_code == 401
