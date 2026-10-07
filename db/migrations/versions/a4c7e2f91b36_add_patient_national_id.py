"""Add patient national ID

Revision ID: a4c7e2f91b36
Revises: e4a7c9d2b1f6
Create Date: 2026-10-07 10:00:00.000000

Existing patients get a fictional number built from their id with the web backend's demo
pattern (prefix 99999, then the id in four digits, then the check digits). For a database
seeded by ``python -m web_backend.seed`` before this revision, the seeded patients come first,
so they get the numbers listed in the web backend README. Databases with patient ids above
9999 cannot be upgraded; recreate them and run the seed again.
"""

from collections.abc import Sequence

import sqlalchemy as sa
from alembic import op

revision: str = "a4c7e2f91b36"
down_revision: str | Sequence[str] | None = "e4a7c9d2b1f6"
branch_labels: str | Sequence[str] | None = None
depends_on: str | Sequence[str] | None = None

FICTIONAL_PREFIX = "99999"


def _fictional_national_id(number: int) -> str:
    # Same rule as web_backend.national_id.fictional_national_id; kept here so the
    # migration does not change if the application code changes
    first_nine = f"{FICTIONAL_PREFIX}{number:04d}"
    digits = [int(c) for c in first_nine]
    tenth = (sum(digits[0:9:2]) * 7 - sum(digits[1:8:2])) % 10
    eleventh = (sum(digits) + tenth) % 10
    return f"{first_nine}{tenth}{eleventh}"


def upgrade() -> None:
    op.add_column("patients", sa.Column("national_id", sa.String(length=11), nullable=True))

    conn = op.get_bind()
    patient_ids = conn.execute(sa.text("SELECT id FROM patients ORDER BY id")).scalars().all()
    if patient_ids and patient_ids[-1] > 9999:
        raise RuntimeError(
            "Patient ids above 9999 cannot get a fictional national ID; recreate the database"
        )
    for patient_id in patient_ids:
        conn.execute(
            sa.text("UPDATE patients SET national_id = :national_id WHERE id = :id"),
            {"national_id": _fictional_national_id(patient_id), "id": patient_id},
        )

    op.alter_column("patients", "national_id", nullable=False)
    op.create_index(op.f("ix_patients_national_id"), "patients", ["national_id"], unique=True)
    op.create_check_constraint(
        "ck_patients_national_id_eleven_digits", "patients", "length(national_id) = 11"
    )


def downgrade() -> None:
    op.drop_constraint("ck_patients_national_id_eleven_digits", "patients", type_="check")
    op.drop_index(op.f("ix_patients_national_id"), table_name="patients")
    op.drop_column("patients", "national_id")
