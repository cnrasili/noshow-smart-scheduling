from collections.abc import Iterator

from fastapi import Request
from sqlalchemy.orm import Session

from noshow_db import SessionLocal
from overbooking_service.config import settings
from overbooking_service.data_source import (
    PatientDataSource,
    SlotDataSource,
    UnconfiguredDataSource,
    UnconfiguredSlotSource,
)
from overbooking_service.predictor import Predictor
from overbooking_service.rules import OverbookingRule


def get_predictor(request: Request) -> Predictor:
    return request.app.state.predictor


def get_data_source() -> PatientDataSource:
    return UnconfiguredDataSource()


def get_slot_source() -> SlotDataSource:
    return UnconfiguredSlotSource()


def get_rule() -> OverbookingRule:
    return settings.overbooking


def get_session() -> Iterator[Session]:
    with SessionLocal() as session:
        yield session
