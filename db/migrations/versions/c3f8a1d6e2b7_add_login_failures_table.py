"""Add login failures table

Revision ID: c3f8a1d6e2b7
Revises: a4c7e2f91b36
Create Date: 2026-10-08 12:00:00.000000

Failed website logins of patients and doctors, used to limit password guessing.
"""

from collections.abc import Sequence

import sqlalchemy as sa
from alembic import op

revision: str = "c3f8a1d6e2b7"
down_revision: str | Sequence[str] | None = "a4c7e2f91b36"
branch_labels: str | Sequence[str] | None = None
depends_on: str | Sequence[str] | None = None


def upgrade() -> None:
    op.create_table(
        "login_failures",
        sa.Column("id", sa.Integer(), nullable=False),
        sa.Column("login_hash", sa.String(length=64), nullable=False),
        sa.Column("client_ip", sa.String(length=64), nullable=False),
        sa.Column("created_at", sa.DateTime(timezone=True), nullable=False),
        sa.PrimaryKeyConstraint("id"),
    )
    op.create_index(
        op.f("ix_login_failures_login_hash"), "login_failures", ["login_hash"], unique=False
    )
    op.create_index(
        op.f("ix_login_failures_client_ip"), "login_failures", ["client_ip"], unique=False
    )
    op.create_index(
        op.f("ix_login_failures_created_at"), "login_failures", ["created_at"], unique=False
    )


def downgrade() -> None:
    op.drop_index(op.f("ix_login_failures_created_at"), table_name="login_failures")
    op.drop_index(op.f("ix_login_failures_client_ip"), table_name="login_failures")
    op.drop_index(op.f("ix_login_failures_login_hash"), table_name="login_failures")
    op.drop_table("login_failures")
