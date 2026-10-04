from datetime import date
from typing import Annotated

from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.orm import Session

from noshow_db.models.service import BookingDecision
from overbooking_service.data_source import (
    DataSourceUnavailable,
    PatientDataSource,
    SlotDataSource,
    SlotState,
)
from overbooking_service.dependencies import (
    get_data_source,
    get_predictor,
    get_rule,
    get_session,
    get_slot_source,
)
from overbooking_service.predict import score_patient
from overbooking_service.predictor import Predictor
from overbooking_service.rules import Decision, OverbookingRule, decide
from overbooking_service.schemas import BookingDecisionRequest, BookingDecisionResponse

router = APIRouter()


def evaluate(
    patients: PatientDataSource,
    slots: SlotDataSource,
    predictor: Predictor,
    rule: OverbookingRule,
    patient_id: int,
    slot: SlotState,
    booking_date: date,
) -> tuple[Decision, float, list[float]] | None:
    """Decision, patient risk and booked patients' risks; None if the patient is unknown."""
    scored = score_patient(patients, predictor, patient_id, slot.slot_date, booking_date)
    if scored is None:
        return None
    p_noshow = scored[1]

    if any(b.patient_id == patient_id for b in slot.bookings):
        decision = Decision(
            allow=False, overbook=False, reason="Patient is already booked in this slot"
        )
        return decision, p_noshow, []

    booked_risks: list[float] = []
    for booking in slot.bookings:
        booked = score_patient(
            patients, predictor, booking.patient_id, slot.slot_date, booking.booking_date
        )
        if booked is None:
            raise DataSourceUnavailable(f"Booked patient {booking.patient_id} not found")
        booked_risks.append(booked[1])
    daily_overbooks = slots.count_overbooks(slot.doctor_id, slot.slot_date) if slot.bookings else 0
    return decide(booked_risks, slot.max_patients, daily_overbooks, rule), p_noshow, booked_risks


@router.post(
    "/booking-decision",
    responses={
        404: {"description": "Patient or slot not found"},
        503: {"description": "Patient or slot data source unavailable"},
    },
)
def booking_decision(
    body: BookingDecisionRequest,
    predictor: Annotated[Predictor, Depends(get_predictor)],
    patients: Annotated[PatientDataSource, Depends(get_data_source)],
    slots: Annotated[SlotDataSource, Depends(get_slot_source)],
    rule: Annotated[OverbookingRule, Depends(get_rule)],
    session: Annotated[Session, Depends(get_session)],
) -> BookingDecisionResponse:
    try:
        slot = slots.get_slot(body.slot_id)
        if slot is None:
            raise HTTPException(404, f"Slot {body.slot_id} not found")
        if body.booking_date > slot.slot_date:
            raise HTTPException(422, "booking_date must not be after the slot date")

        evaluated = evaluate(
            patients, slots, predictor, rule, body.patient_id, slot, body.booking_date
        )
        if evaluated is None:
            raise HTTPException(404, f"Patient {body.patient_id} not found")
        decision, p_noshow, booked_risks = evaluated
    except DataSourceUnavailable as exc:
        raise HTTPException(503, str(exc)) from exc

    # Decision log
    session.add(
        BookingDecision(
            patient_id=body.patient_id,
            slot_id=body.slot_id,
            booking_date=body.booking_date,
            p_noshow=p_noshow,
            booked_p_noshow=min(booked_risks) if booked_risks else None,
            allow=decision.allow,
            overbook=decision.overbook,
            reason=decision.reason,
            threshold=rule.threshold,
            model_version=predictor.version,
        )
    )
    session.commit()

    return BookingDecisionResponse(
        allow=decision.allow, overbook=decision.overbook, p_noshow=p_noshow, reason=decision.reason
    )
