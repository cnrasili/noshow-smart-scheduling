"""Add user account and session tables

Revision ID: d561909c92ca
Revises: b3e8f1c2a7d4
Create Date: 2026-10-04 18:14:36.814055

"""

from collections.abc import Sequence

import sqlalchemy as sa
from alembic import op

revision: str = "d561909c92ca"
down_revision: str | Sequence[str] | None = "b3e8f1c2a7d4"
branch_labels: str | Sequence[str] | None = None
depends_on: str | Sequence[str] | None = None


def upgrade() -> None:
    op.create_table(
        "user_accounts",
        sa.Column("id", sa.Integer(), nullable=False),
        sa.Column("email", sa.String(length=255), nullable=False),
        sa.Column("password_hash", sa.String(length=255), nullable=False),
        sa.Column("role", sa.String(length=16), nullable=False),
        sa.Column("patient_id", sa.Integer(), nullable=True),
        sa.Column("doctor_id", sa.Integer(), nullable=True),
        sa.Column(
            "created_at",
            sa.DateTime(timezone=True),
            server_default=sa.text("now()"),
            nullable=False,
        ),
        sa.CheckConstraint(
            "(role = 'patient' AND patient_id IS NOT NULL AND doctor_id IS NULL)"
            " OR (role = 'doctor' AND doctor_id IS NOT NULL AND patient_id IS NULL)",
            name="ck_user_accounts_role_matches_owner",
        ),
        sa.ForeignKeyConstraint(
            ["doctor_id"],
            ["doctors.id"],
        ),
        sa.ForeignKeyConstraint(
            ["patient_id"],
            ["patients.id"],
        ),
        sa.PrimaryKeyConstraint("id"),
        sa.UniqueConstraint("doctor_id"),
        sa.UniqueConstraint("patient_id"),
    )
    op.create_index(op.f("ix_user_accounts_email"), "user_accounts", ["email"], unique=True)
    op.create_table(
        "auth_sessions",
        sa.Column("id", sa.Integer(), nullable=False),
        sa.Column("account_id", sa.Integer(), nullable=False),
        sa.Column("token_hash", sa.String(length=64), nullable=False),
        sa.Column("expires_at", sa.DateTime(timezone=True), nullable=False),
        sa.Column(
            "created_at",
            sa.DateTime(timezone=True),
            server_default=sa.text("now()"),
            nullable=False,
        ),
        sa.ForeignKeyConstraint(["account_id"], ["user_accounts.id"], ondelete="CASCADE"),
        sa.PrimaryKeyConstraint("id"),
        sa.UniqueConstraint("token_hash"),
    )
    op.create_index(
        op.f("ix_auth_sessions_account_id"), "auth_sessions", ["account_id"], unique=False
    )


def downgrade() -> None:
    op.drop_index(op.f("ix_auth_sessions_account_id"), table_name="auth_sessions")
    op.drop_table("auth_sessions")
    op.drop_index(op.f("ix_user_accounts_email"), table_name="user_accounts")
    op.drop_table("user_accounts")
