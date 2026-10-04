import hashlib
import math
from enum import StrEnum
from typing import Annotated

from fastapi import APIRouter, Depends
from sqlalchemy import func, select
from sqlalchemy.orm import Session

from noshow_db.models.core import Appointment
from noshow_db.models.service import AbAssignment
from overbooking_service.dependencies import get_session
from overbooking_service.schemas import AbGroupSummary, AbSummary

router = APIRouter(prefix="/ab")


class Group(StrEnum):
    REMINDER = "reminder"
    CONTROL = "control"


def assign_group(patient_id: int, salt: str) -> Group:
    """Deterministic group of a patient; the same patient always gets the same group."""
    digest = hashlib.sha256(f"{salt}:{patient_id}".encode()).digest()
    return Group.REMINDER if digest[0] % 2 == 0 else Group.CONTROL


def two_proportion_test(k1: int, n1: int, k2: int, n2: int) -> tuple[float, float] | None:
    """Pooled two-proportion z-test; return z and the two-sided p-value."""
    if n1 == 0 or n2 == 0:
        return None
    pooled = (k1 + k2) / (n1 + n2)
    variance = pooled * (1 - pooled) * (1 / n1 + 1 / n2)
    if variance == 0:
        return None
    z = (k1 / n1 - k2 / n2) / math.sqrt(variance)
    return z, math.erfc(abs(z) / math.sqrt(2))


@router.get("/summary")
def summary(session: Annotated[Session, Depends(get_session)]) -> AbSummary:
    # Only appointments with a recorded outcome
    rows = session.execute(
        select(
            AbAssignment.group,
            func.count(),
            func.count().filter(Appointment.attended.is_(False)),
        )
        .join(Appointment, Appointment.id == AbAssignment.appointment_id)
        .where(Appointment.attended.is_not(None))
        .group_by(AbAssignment.group)
    ).all()
    counts = {group: (n, no_shows) for group, n, no_shows in rows}

    groups = []
    for group in Group:
        n, no_shows = counts.get(group, (0, 0))
        rate = no_shows / n if n else None
        groups.append(
            AbGroupSummary(group=group, appointments=n, no_shows=no_shows, no_show_rate=rate)
        )

    reminder, control = groups
    test = two_proportion_test(
        control.no_shows, control.appointments, reminder.no_shows, reminder.appointments
    )
    return AbSummary(
        groups=groups,
        difference=(
            control.no_show_rate - reminder.no_show_rate
            if control.no_show_rate is not None and reminder.no_show_rate is not None
            else None
        ),
        z=test[0] if test else None,
        p_value=test[1] if test else None,
    )
