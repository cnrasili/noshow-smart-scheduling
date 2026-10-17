from datetime import time

from noshow_db.models.core import DoctorSchedule


def test_public_doctors_list_only_the_department(db, client, make_department) -> None:
    department = make_department()
    db.add_all(
        [
            DoctorSchedule(
                doctor_id=department.id, weekday=1, start_time=time(8), end_time=time(12)
            ),
            DoctorSchedule(
                doctor_id=department.id, weekday=0, start_time=time(8), end_time=time(12)
            ),
        ]
    )
    db.commit()

    response = client.get("/public/doctors")

    assert response.status_code == 200
    assert response.json() == [
        {
            "id": department.id,
            "full_name": "General Practice",
            "specialty": "General Practice",
            "working_hours": [
                {"weekday": 0, "start_time": "08:00:00", "end_time": "12:00:00"},
                {"weekday": 1, "start_time": "08:00:00", "end_time": "12:00:00"},
            ],
        }
    ]


def test_public_doctors_return_no_account_data(client, make_department) -> None:
    make_department()

    body = client.get("/public/doctors").text

    assert "aile.hekimligi" not in body
    assert "password" not in body
    assert "email" not in body
