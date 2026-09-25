"""Add predictions table

Revision ID: 2f196bdd444f
Revises:
Create Date: 2026-09-26 01:39:31.863816

"""

from collections.abc import Sequence

import sqlalchemy as sa
from alembic import op

revision: str = "2f196bdd444f"
down_revision: str | Sequence[str] | None = None
branch_labels: str | Sequence[str] | None = None
depends_on: str | Sequence[str] | None = None


def upgrade() -> None:
    op.create_table(
        "predictions",
        sa.Column("id", sa.Integer(), nullable=False),
        sa.Column("patient_id", sa.Integer(), nullable=False),
        sa.Column("appointment_date", sa.Date(), nullable=False),
        sa.Column("booking_date", sa.Date(), nullable=False),
        sa.Column("features", sa.JSON(), nullable=False),
        sa.Column("p_noshow", sa.Double(), nullable=False),
        sa.Column("model_version", sa.String(length=64), nullable=False),
        sa.Column(
            "created_at",
            sa.DateTime(timezone=True),
            server_default=sa.text("now()"),
            nullable=False,
        ),
        sa.PrimaryKeyConstraint("id"),
    )
    op.create_index(op.f("ix_predictions_patient_id"), "predictions", ["patient_id"], unique=False)


def downgrade() -> None:
    op.drop_index(op.f("ix_predictions_patient_id"), table_name="predictions")
    op.drop_table("predictions")
