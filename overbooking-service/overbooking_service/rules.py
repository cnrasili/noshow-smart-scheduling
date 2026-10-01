from collections.abc import Sequence
from dataclasses import dataclass

from pydantic import BaseModel, Field


class OverbookingRule(BaseModel):
    """Slot-level overbooking parameters."""

    threshold: float = Field(ge=0, le=1)
    max_patients_per_slot: int = Field(ge=1)
    daily_overbook_limit: int = Field(ge=0)


@dataclass(frozen=True)
class Decision:
    allow: bool
    overbook: bool
    reason: str


def decide(booked_risks: Sequence[float], daily_overbooks: int, rule: OverbookingRule) -> Decision:
    """Decide whether a patient may be booked into a slot."""
    if not booked_risks:
        return Decision(allow=True, overbook=False, reason="Slot is empty")

    patients = len(booked_risks)
    if patients >= rule.max_patients_per_slot:
        return Decision(
            allow=False,
            overbook=False,
            reason=f"Slot is full ({patients}/{rule.max_patients_per_slot} patients)",
        )

    # Every booked patient must be likely to miss the appointment
    risk = min(booked_risks)
    if risk < rule.threshold:
        return Decision(
            allow=False,
            overbook=False,
            reason=f"Slot is booked; booked patient risk {risk:.2f} < {rule.threshold:.2f}",
        )

    risk_text = f"Slot is booked; booked patient risk {risk:.2f} >= {rule.threshold:.2f}"
    if daily_overbooks >= rule.daily_overbook_limit:
        return Decision(
            allow=False,
            overbook=False,
            reason=(
                f"{risk_text}; daily overbook limit reached "
                f"({daily_overbooks}/{rule.daily_overbook_limit})"
            ),
        )

    return Decision(
        allow=True,
        overbook=True,
        reason=f"{risk_text}; daily overbooks {daily_overbooks}/{rule.daily_overbook_limit}",
    )
