from collections.abc import Iterator
from datetime import UTC, datetime
from typing import Annotated

from fastapi import Depends, Request
from sqlalchemy.orm import Session

from noshow_db import SessionLocal
from overbooking_service.config import ReminderSettings, settings
from overbooking_service.data_source import (
    DbPatientSource,
    DbSlotSource,
    PatientDataSource,
    SlotDataSource,
)
from overbooking_service.predictor import Predictor
from overbooking_service.rules import OverbookingRule


def get_predictor(request: Request) -> Predictor:
    return request.app.state.predictor


def get_session() -> Iterator[Session]:
    with SessionLocal() as session:
        yield session


def get_data_source(session: Annotated[Session, Depends(get_session)]) -> PatientDataSource:
    return DbPatientSource(session)


def get_slot_source(session: Annotated[Session, Depends(get_session)]) -> SlotDataSource:
    return DbSlotSource(session, settings.clinic_timezone)


def get_rule() -> OverbookingRule:
    return settings.overbooking


def get_reminder_settings() -> ReminderSettings:
    return settings.reminders


def get_now() -> datetime:
    return datetime.now(UTC)
