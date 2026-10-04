"""Add ab_assignments table

Revision ID: b3e8f1c2a7d4
Revises: 7c1e4b9a3f20
Create Date: 2026-10-04 18:00:00.000000

"""

from collections.abc import Sequence

import sqlalchemy as sa
from alembic import op

revision: str = "b3e8f1c2a7d4"
down_revision: str | Sequence[str] | None = "7c1e4b9a3f20"
branch_labels: str | Sequence[str] | None = None
depends_on: str | Sequence[str] | None = None


def upgrade() -> None:
    op.create_table(
        "ab_assignments",
        sa.Column("id", sa.Integer(), nullable=False),
        sa.Column("appointment_id", sa.Integer(), nullable=False),
        sa.Column("patient_id", sa.Integer(), nullable=False),
        sa.Column("group", sa.String(length=16), nullable=False),
        sa.Column(
            "created_at",
            sa.DateTime(timezone=True),
            server_default=sa.text("now()"),
            nullable=False,
        ),
        sa.PrimaryKeyConstraint("id"),
        sa.UniqueConstraint("appointment_id"),
    )
    op.create_index(
        op.f("ix_ab_assignments_patient_id"), "ab_assignments", ["patient_id"], unique=False
    )


def downgrade() -> None:
    op.drop_index(op.f("ix_ab_assignments_patient_id"), table_name="ab_assignments")
    op.drop_table("ab_assignments")
