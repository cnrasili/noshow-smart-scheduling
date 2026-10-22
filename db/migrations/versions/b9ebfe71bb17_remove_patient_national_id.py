"""Remove patient national ID

Revision ID: b9ebfe71bb17
Revises: a4d098683a3c
Create Date: 2026-10-22 16:54:00.000000

Patients are the dataset's patients and log in with their patient number; national ID numbers
are not used, not even fictional ones. Downgrading restores the column empty and optional.
"""

from collections.abc import Sequence

import sqlalchemy as sa
from alembic import op

revision: str = "b9ebfe71bb17"
down_revision: str | Sequence[str] | None = "a4d098683a3c"
branch_labels: str | Sequence[str] | None = None
depends_on: str | Sequence[str] | None = None


def upgrade() -> None:
    op.drop_constraint("ck_patients_national_id_eleven_digits", "patients", type_="check")
    op.drop_index(op.f("ix_patients_national_id"), table_name="patients")
    op.drop_column("patients", "national_id")


def downgrade() -> None:
    op.add_column("patients", sa.Column("national_id", sa.String(length=11), nullable=True))
    op.create_index(op.f("ix_patients_national_id"), "patients", ["national_id"], unique=True)
    op.create_check_constraint(
        "ck_patients_national_id_eleven_digits", "patients", "length(national_id) = 11"
    )
