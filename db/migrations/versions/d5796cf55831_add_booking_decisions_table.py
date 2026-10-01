"""Add booking decisions table

Revision ID: d5796cf55831
Revises: 2f196bdd444f
Create Date: 2026-10-01 19:34:45.634613

"""

from collections.abc import Sequence

import sqlalchemy as sa
from alembic import op

revision: str = "d5796cf55831"
down_revision: str | Sequence[str] | None = "2f196bdd444f"
branch_labels: str | Sequence[str] | None = None
depends_on: str | Sequence[str] | None = None


def upgrade() -> None:
    op.create_table(
        "booking_decisions",
        sa.Column("id", sa.Integer(), nullable=False),
        sa.Column("patient_id", sa.Integer(), nullable=False),
        sa.Column("slot_id", sa.Integer(), nullable=False),
        sa.Column("booking_date", sa.Date(), nullable=False),
        sa.Column("p_noshow", sa.Double(), nullable=False),
        sa.Column("booked_p_noshow", sa.Double(), nullable=True),
        sa.Column("allow", sa.Boolean(), nullable=False),
        sa.Column("overbook", sa.Boolean(), nullable=False),
        sa.Column("reason", sa.String(length=255), nullable=False),
        sa.Column("threshold", sa.Double(), nullable=False),
        sa.Column("model_version", sa.String(length=64), nullable=False),
        sa.Column(
            "created_at",
            sa.DateTime(timezone=True),
            server_default=sa.text("now()"),
            nullable=False,
        ),
        sa.PrimaryKeyConstraint("id"),
    )
    op.create_index(
        op.f("ix_booking_decisions_patient_id"), "booking_decisions", ["patient_id"], unique=False
    )
    op.create_index(
        op.f("ix_booking_decisions_slot_id"), "booking_decisions", ["slot_id"], unique=False
    )


def downgrade() -> None:
    op.drop_index(op.f("ix_booking_decisions_slot_id"), table_name="booking_decisions")
    op.drop_index(op.f("ix_booking_decisions_patient_id"), table_name="booking_decisions")
    op.drop_table("booking_decisions")
