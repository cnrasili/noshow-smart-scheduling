from sqlalchemy import func, select

from noshow_db.models.core import Appointment, Patient, Slot, UserAccount
from web_backend.seed import DEMO_PASSWORD, DOCTOR_EMAIL, PATIENTS, seed


def _count(db, model) -> int:
    return db.scalar(select(func.count()).select_from(model))


def test_seed_creates_a_usable_demo_clinic(db, client) -> None:
    seed(db)

    assert _count(db, Patient) == len(PATIENTS)
    assert _count(db, UserAccount) == len(PATIENTS) + 1
    assert _count(db, Slot) > 0
    assert _count(db, Appointment) > 0
    for email in (DOCTOR_EMAIL, PATIENTS[0][1]):
        response = client.post("/auth/login", json={"email": email, "password": DEMO_PASSWORD})
        assert response.status_code == 200


def test_seed_can_run_twice(db) -> None:
    seed(db)
    counts = [_count(db, model) for model in (Patient, UserAccount, Slot, Appointment)]

    seed(db)

    assert [_count(db, model) for model in (Patient, UserAccount, Slot, Appointment)] == counts
