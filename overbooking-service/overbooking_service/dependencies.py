from collections.abc import Iterator

from fastapi import Request
from sqlalchemy.orm import Session

from noshow_db import SessionLocal
from overbooking_service.data_source import PatientDataSource, UnconfiguredDataSource
from overbooking_service.predictor import Predictor


def get_predictor(request: Request) -> Predictor:
    return request.app.state.predictor


def get_data_source() -> PatientDataSource:
    return UnconfiguredDataSource()


def get_session() -> Iterator[Session]:
    with SessionLocal() as session:
        yield session
