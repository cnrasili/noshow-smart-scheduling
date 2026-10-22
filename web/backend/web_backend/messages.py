# The patient's SMS messages for "Randevularım"; the overbooking service writes the table
from datetime import datetime
from typing import Annotated, Literal

from fastapi import APIRouter, Depends
from pydantic import BaseModel
from sqlalchemy import select
from sqlalchemy.orm import Session

from noshow_db.models.service import Message
from web_backend.auth import PatientAccount
from web_backend.clinic import as_utc
from web_backend.db import get_db

router = APIRouter(tags=["messages"])


class MessageOut(BaseModel):
    kind: Literal["confirmation", "reminder"]
    sent_at: datetime
    body: str


@router.get("/patients/me/messages")
def my_messages(
    account: PatientAccount, db: Annotated[Session, Depends(get_db)]
) -> list[MessageOut]:
    """The patient's own sent SMS, newest first.

    Pending, failed, cancelled and expired messages never reached the patient and are left
    out, as is everything about the A/B test (API contract, Messages).
    """
    messages = db.scalars(
        select(Message)
        .where(
            Message.patient_id == account.patient_id,
            Message.status == "sent",
            Message.sent_at.is_not(None),
        )
        .order_by(Message.sent_at.desc(), Message.id.desc())
    )
    return [
        MessageOut(kind=message.kind, sent_at=as_utc(message.sent_at), body=message.body)
        for message in messages
        if message.kind in ("confirmation", "reminder")
    ]
