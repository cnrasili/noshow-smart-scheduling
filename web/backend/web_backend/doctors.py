from typing import Annotated

from fastapi import APIRouter, Depends
from pydantic import BaseModel
from sqlalchemy import select
from sqlalchemy.orm import Session

from noshow_db.models.core import Doctor
from web_backend.auth import current_account
from web_backend.db import get_db

router = APIRouter(prefix="/doctors", tags=["doctors"], dependencies=[Depends(current_account)])


class DoctorOut(BaseModel):
    id: int
    full_name: str
    specialty: str | None


@router.get("")
def list_doctors(db: Annotated[Session, Depends(get_db)]) -> list[DoctorOut]:
    doctors = db.scalars(select(Doctor).order_by(Doctor.full_name))
    return [DoctorOut(id=d.id, full_name=d.full_name, specialty=d.specialty) for d in doctors]
