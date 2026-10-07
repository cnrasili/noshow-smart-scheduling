"""Acceptance checks every delivered no-show model must pass; each returns the problems found."""

from datetime import date, timedelta

from overbooking_service.features import PastAppointment, PatientRecord, build_features
from overbooking_service.predictor import Predictor

BOOKING = date(2026, 11, 2)


def patient(age: int) -> PatientRecord:
    return PatientRecord(1, age, "F", False, False, False, False, 0)


def history(appointments: int, no_shows: int) -> list[PastAppointment]:
    return [
        PastAppointment(BOOKING - timedelta(days=30 * (i + 1)), attended=i >= no_shows)
        for i in range(appointments)
    ]


def feature_problems(predictor: Predictor) -> list[str]:
    """The schema must list exactly the features the service computes."""
    computed = set(build_features(patient(30), [], BOOKING, BOOKING))
    schema = set(predictor.feature_names)
    problems = []
    if missing := sorted(computed - schema):
        problems.append(f"Features computed by the service but missing in the schema: {missing}")
    if extra := sorted(schema - computed):
        problems.append(f"Schema features the service does not compute: {extra}")
    return problems


def probability_problems(predictor: Predictor) -> list[str]:
    """No-show probabilities must lie between 0 and 1."""
    problems = []
    for age in (5, 30, 70):
        for lead in (0, 7, 60):
            for no_shows in (0, 2):
                features = build_features(
                    patient(age), history(3, no_shows), BOOKING + timedelta(days=lead), BOOKING
                )
                p = predictor.predict(features)
                if not 0 <= p <= 1:
                    problems.append(
                        f"Probability {p} outside 0-1 for age {age}, lead time {lead} days"
                    )
    return problems


def ranking_problems(predictor: Predictor) -> list[str]:
    """Long lead times and past no-shows must score higher than reliable short-notice patients."""
    ages = (20, 40, 60)
    low = [
        predictor.predict(build_features(patient(a), history(5, 0), BOOKING, BOOKING)) for a in ages
    ]
    high = [
        predictor.predict(
            build_features(patient(a), history(3, 3), BOOKING + timedelta(days=60), BOOKING)
        )
        for a in ages
    ]
    low_mean, high_mean = sum(low) / len(low), sum(high) / len(high)
    if high_mean <= low_mean:
        return [
            f"High-risk profiles do not score higher than low-risk ones "
            f"(mean {high_mean:.3f} vs {low_mean:.3f})"
        ]
    return []


def acceptance_problems(predictor: Predictor) -> list[str]:
    problems = feature_problems(predictor)
    # Predictions need the right features
    if problems:
        return problems
    return probability_problems(predictor) + ranking_problems(predictor)
