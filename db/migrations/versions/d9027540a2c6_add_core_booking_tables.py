"""Add core booking tables

Revision ID: d9027540a2c6
Revises: 49ff1f1a251f
Create Date: 2026-10-02 16:30:00.000000

"""

from collections.abc import Sequence

import sqlalchemy as sa
from alembic import op

revision: str = "d9027540a2c6"
down_revision: str | Sequence[str] | None = "49ff1f1a251f"
branch_labels: str | Sequence[str] | None = None
depends_on: str | Sequence[str] | None = None


def upgrade() -> None:
    op.create_table(
        "patients",
        sa.Column("id", sa.Integer(), nullable=False),
        sa.Column("full_name", sa.String(length=255), nullable=False),
        sa.Column("email", sa.String(length=255), nullable=False),
        sa.Column("age", sa.Integer(), nullable=False),
        sa.Column("gender", sa.String(length=1), nullable=False),
        sa.Column("scholarship", sa.Boolean(), nullable=False),
        sa.Column("hipertension", sa.Boolean(), nullable=False),
        sa.Column("diabetes", sa.Boolean(), nullable=False),
        sa.Column("alcoholism", sa.Boolean(), nullable=False),
        sa.Column("handcap", sa.Integer(), nullable=False),
        sa.Column(
            "created_at",
            sa.DateTime(timezone=True),
            server_default=sa.text("now()"),
            nullable=False,
        ),
        sa.PrimaryKeyConstraint("id"),
    )
    op.create_index(op.f("ix_patients_email"), "patients", ["email"], unique=True)

    op.create_table(
        "doctors",
        sa.Column("id", sa.Integer(), nullable=False),
        sa.Column("full_name", sa.String(length=255), nullable=False),
        sa.Column("specialty", sa.String(length=255), nullable=True),
        sa.PrimaryKeyConstraint("id"),
    )

    op.create_table(
        "doctor_schedules",
        sa.Column("id", sa.Integer(), nullable=False),
        sa.Column("doctor_id", sa.Integer(), nullable=False),
        sa.Column("weekday", sa.Integer(), nullable=False),
        sa.Column("start_time", sa.Time(), nullable=False),
        sa.Column("end_time", sa.Time(), nullable=False),
        sa.CheckConstraint("end_time > start_time"),
        sa.ForeignKeyConstraint(["doctor_id"], ["doctors.id"]),
        sa.PrimaryKeyConstraint("id"),
        sa.UniqueConstraint("doctor_id", "weekday"),
    )
    op.create_index(op.f("ix_doctor_schedules_doctor_id"), "doctor_schedules", ["doctor_id"])

    op.create_table(
        "slots",
        sa.Column("id", sa.Integer(), nullable=False),
        sa.Column("doctor_id", sa.Integer(), nullable=False),
        sa.Column("start_at", sa.DateTime(timezone=True), nullable=False),
        sa.Column("end_at", sa.DateTime(timezone=True), nullable=False),
        sa.Column("max_patients", sa.Integer(), nullable=False),
        sa.ForeignKeyConstraint(["doctor_id"], ["doctors.id"]),
        sa.PrimaryKeyConstraint("id"),
        sa.UniqueConstraint("doctor_id", "start_at"),
    )
    op.create_index(op.f("ix_slots_doctor_id"), "slots", ["doctor_id"])
    op.create_index(op.f("ix_slots_start_at"), "slots", ["start_at"])

    op.create_table(
        "appointments",
        sa.Column("id", sa.Integer(), nullable=False),
        sa.Column("patient_id", sa.Integer(), nullable=False),
        sa.Column("slot_id", sa.Integer(), nullable=False),
        sa.Column("appointment_date", sa.Date(), nullable=False),
        sa.Column("booking_date", sa.Date(), nullable=False),
        sa.Column("attended", sa.Boolean(), nullable=True),
        sa.Column(
            "created_at",
            sa.DateTime(timezone=True),
            server_default=sa.text("now()"),
            nullable=False,
        ),
        sa.ForeignKeyConstraint(["patient_id"], ["patients.id"]),
        sa.ForeignKeyConstraint(["slot_id"], ["slots.id"]),
        sa.PrimaryKeyConstraint("id"),
        sa.UniqueConstraint("patient_id", "slot_id"),
    )
    op.create_index(op.f("ix_appointments_patient_id"), "appointments", ["patient_id"])
    op.create_index(op.f("ix_appointments_slot_id"), "appointments", ["slot_id"])


def downgrade() -> None:
    op.drop_index(op.f("ix_appointments_slot_id"), table_name="appointments")
    op.drop_index(op.f("ix_appointments_patient_id"), table_name="appointments")
    op.drop_table("appointments")

    op.drop_index(op.f("ix_slots_start_at"), table_name="slots")
    op.drop_index(op.f("ix_slots_doctor_id"), table_name="slots")
    op.drop_table("slots")

    op.drop_index(op.f("ix_doctor_schedules_doctor_id"), table_name="doctor_schedules")
    op.drop_table("doctor_schedules")

    op.drop_table("doctors")

    op.drop_index(op.f("ix_patients_email"), table_name="patients")
    op.drop_table("patients")
