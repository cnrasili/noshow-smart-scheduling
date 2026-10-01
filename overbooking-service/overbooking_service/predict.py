from datetime import date
from typing import Annotated

from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.orm import Session

from noshow_db.models.service import Prediction
from overbooking_service.data_source import DataSourceUnavailable, PatientDataSource
from overbooking_service.dependencies import get_data_source, get_predictor, get_session
from overbooking_service.features import build_features
from overbooking_service.predictor import Predictor
from overbooking_service.schemas import PredictRequest, PredictResponse

router = APIRouter()


def score_patient(
    data_source: PatientDataSource,
    predictor: Predictor,
    patient_id: int,
    appointment_date: date,
    booking_date: date,
) -> tuple[dict[str, float], float] | None:
    """Return features and no-show probability, or None if the patient is unknown."""
    patient = data_source.get_patient(patient_id)
    if patient is None:
        return None
    history = data_source.get_history(patient_id)
    features = build_features(patient, history, appointment_date, booking_date)
    return features, predictor.predict(features)


@router.post(
    "/predict",
    responses={
        404: {"description": "Patient not found"},
        503: {"description": "Patient data source unavailable"},
    },
)
def predict(
    body: PredictRequest,
    predictor: Annotated[Predictor, Depends(get_predictor)],
    data_source: Annotated[PatientDataSource, Depends(get_data_source)],
    session: Annotated[Session, Depends(get_session)],
) -> PredictResponse:
    if body.appointment_date < body.booking_date:
        raise HTTPException(422, "appointment_date must not be before booking_date")

    try:
        scored = score_patient(
            data_source, predictor, body.patient_id, body.appointment_date, body.booking_date
        )
    except DataSourceUnavailable as exc:
        raise HTTPException(503, str(exc)) from exc
    if scored is None:
        raise HTTPException(404, f"Patient {body.patient_id} not found")
    features, p_noshow = scored

    # Prediction log
    session.add(
        Prediction(
            patient_id=body.patient_id,
            appointment_date=body.appointment_date,
            booking_date=body.booking_date,
            features=features,
            p_noshow=p_noshow,
            model_version=predictor.version,
        )
    )
    session.commit()

    return PredictResponse(p_noshow=p_noshow, model_version=predictor.version)
