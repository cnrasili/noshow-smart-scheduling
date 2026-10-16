"""Add dataset patient number and appointment history

Revision ID: 665da867396e
Revises: c3f8a1d6e2b7
Create Date: 2026-10-15 20:00:00.000000

Patients get the PatientId of the public no-show dataset, and the national ID number becomes
optional because dataset patients have none. The dataset appointments get their own table:
they have a day but no slot or time. Downgrading removes the dataset patients.
"""

from collections.abc import Sequence

import sqlalchemy as sa
from alembic import op

revision: str = "665da867396e"
down_revision: str | Sequence[str] | None = "c3f8a1d6e2b7"
branch_labels: str | Sequence[str] | None = None
depends_on: str | Sequence[str] | None = None


def upgrade() -> None:
    op.add_column("patients", sa.Column("patient_number", sa.String(length=20), nullable=True))
    op.create_index(op.f("ix_patients_patient_number"), "patients", ["patient_number"], unique=True)
    op.alter_column("patients", "national_id", existing_type=sa.String(length=11), nullable=True)
    op.create_table(
        "dataset_appointments",
        sa.Column("id", sa.Integer(), nullable=False),
        sa.Column("appointment_number", sa.Integer(), nullable=False),
        sa.Column("patient_id", sa.Integer(), nullable=False),
        sa.Column("booked_at", sa.DateTime(timezone=True), nullable=False),
        sa.Column("appointment_date", sa.Date(), nullable=False),
        sa.Column("attended", sa.Boolean(), nullable=False),
        sa.Column("sms_received", sa.Boolean(), nullable=False),
        sa.ForeignKeyConstraint(["patient_id"], ["patients.id"]),
        sa.PrimaryKeyConstraint("id"),
        sa.UniqueConstraint("appointment_number"),
    )
    op.create_index(
        op.f("ix_dataset_appointments_patient_id"),
        "dataset_appointments",
        ["patient_id"],
        unique=False,
    )


def downgrade() -> None:
    op.drop_index(op.f("ix_dataset_appointments_patient_id"), table_name="dataset_appointments")
    op.drop_table("dataset_appointments")
    op.execute("DELETE FROM patients WHERE national_id IS NULL")
    op.alter_column("patients", "national_id", existing_type=sa.String(length=11), nullable=False)
    op.drop_index(op.f("ix_patients_patient_number"), table_name="patients")
    op.drop_column("patients", "patient_number")
