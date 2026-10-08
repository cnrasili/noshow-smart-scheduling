from datetime import time

from noshow_db.models.core import DoctorSchedule
from web_backend.seed import DOCTORS, PATIENTS, seed


def test_public_doctors_need_no_sign_in(db, client, make_doctor) -> None:
    doctor = make_doctor(email="doctor@example.com", name="Dr. Test")
    db.add_all(
        [
            DoctorSchedule(doctor_id=doctor.id, weekday=3, start_time=time(13), end_time=time(16)),
            DoctorSchedule(doctor_id=doctor.id, weekday=0, start_time=time(9), end_time=time(12)),
        ]
    )
    db.commit()

    response = client.get("/public/doctors")

    assert response.status_code == 200
    assert response.json() == [
        {
            "id": doctor.id,
            "full_name": "Dr. Test",
            "specialty": "General",
            "working_hours": [
                {"weekday": 0, "start_time": "09:00:00", "end_time": "12:00:00"},
                {"weekday": 3, "start_time": "13:00:00", "end_time": "16:00:00"},
            ],
        }
    ]


def test_public_doctors_return_no_account_data(db, client) -> None:
    seed(db)

    body = client.get("/public/doctors").text

    assert "@" not in body
    assert "demo1234" not in body
    assert "password" not in body
    assert "email" not in body
    for name, *_ in PATIENTS:
        assert name not in body


def test_public_doctors_list_the_seeded_hospital(db, client) -> None:
    seed(db)

    doctors = client.get("/public/doctors").json()

    assert len(doctors) == len(DOCTORS)
    assert all(doctor["working_hours"] for doctor in doctors)
    departments = [doctor["specialty"] for doctor in doctors]
    assert departments == sorted(departments)
    assert len(set(departments)) >= 8
