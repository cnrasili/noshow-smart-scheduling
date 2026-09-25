from dataclasses import dataclass
from datetime import date


@dataclass(frozen=True)
class PatientRecord:
    patient_id: int
    age: int
    gender: str
    scholarship: bool
    hipertension: bool
    diabetes: bool
    alcoholism: bool
    handcap: int


@dataclass(frozen=True)
class PastAppointment:
    appointment_date: date
    attended: bool


def build_features(
    patient: PatientRecord,
    history: list[PastAppointment],
    appointment_date: date,
    booking_date: date,
) -> dict[str, float]:
    """Compute model features from data known at booking time."""
    if appointment_date < booking_date:
        raise ValueError("appointment_date must not be before booking_date")

    # Only appointments with a known outcome at booking time, to avoid leakage
    past = [a for a in history if a.appointment_date < booking_date]

    return {
        "lead_days": float((appointment_date - booking_date).days),
        "weekday": float(appointment_date.weekday()),
        "age": float(patient.age),
        "gender_male": 1.0 if patient.gender.upper() == "M" else 0.0,
        "scholarship": float(patient.scholarship),
        "hipertension": float(patient.hipertension),
        "diabetes": float(patient.diabetes),
        "alcoholism": float(patient.alcoholism),
        "handcap": float(patient.handcap),
        "prior_appt_count": float(len(past)),
        "prior_noshow_count": float(sum(not a.attended for a in past)),
    }
