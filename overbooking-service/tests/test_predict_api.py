from fastapi.testclient import TestClient
from sqlalchemy import select
from sqlalchemy.orm import Session, sessionmaker

from noshow_db.models.service import Prediction
from overbooking_service.dependencies import get_data_source
from overbooking_service.main import app

BODY = {"patient_id": 1, "appointment_date": "2026-11-10", "booking_date": "2026-11-02"}


def test_returns_probability_and_version(client: TestClient):
    response = client.post("/predict", json=BODY)
    assert response.status_code == 200
    data = response.json()
    assert 0 <= data["p_noshow"] <= 1
    assert data["model_version"] == "dummy-v0"


def test_prediction_is_logged(client: TestClient, session_factory: sessionmaker[Session]):
    client.post("/predict", json=BODY)
    with session_factory() as session:
        logged = session.scalars(select(Prediction)).one()
    assert logged.patient_id == 1
    assert logged.model_version == "dummy-v0"
    assert logged.features["prior_noshow_count"] == 1


def test_unknown_patient_returns_404(client: TestClient):
    response = client.post("/predict", json={**BODY, "patient_id": 99})
    assert response.status_code == 404


def test_appointment_before_booking_returns_422(client: TestClient):
    response = client.post("/predict", json={**BODY, "appointment_date": "2026-11-01"})
    assert response.status_code == 422


def test_invalid_patient_id_returns_422(client: TestClient):
    response = client.post("/predict", json={**BODY, "patient_id": 0})
    assert response.status_code == 422


def test_unknown_patient_in_database_returns_404(client: TestClient):
    del app.dependency_overrides[get_data_source]
    response = client.post("/predict", json=BODY)
    assert response.status_code == 404
