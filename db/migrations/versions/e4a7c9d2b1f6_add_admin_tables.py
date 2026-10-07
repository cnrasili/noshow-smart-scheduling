"""Add admin service tables

Revision ID: e4a7c9d2b1f6
Revises: d561909c92ca
Create Date: 2026-10-07 18:30:00.000000

"""

from collections.abc import Sequence

import sqlalchemy as sa
from alembic import op

revision: str = "e4a7c9d2b1f6"
down_revision: str | Sequence[str] | None = "d561909c92ca"
branch_labels: str | Sequence[str] | None = None
depends_on: str | Sequence[str] | None = None


def upgrade() -> None:
    op.create_table(
        "admin_users",
        sa.Column("id", sa.Integer(), nullable=False),
        sa.Column("email", sa.String(length=255), nullable=False),
        sa.Column("password_hash", sa.String(length=255), nullable=False),
        sa.Column(
            "created_at",
            sa.DateTime(timezone=True),
            server_default=sa.text("now()"),
            nullable=False,
        ),
        sa.Column("last_login_at", sa.DateTime(timezone=True), nullable=True),
        sa.PrimaryKeyConstraint("id"),
    )
    op.create_index(op.f("ix_admin_users_email"), "admin_users", ["email"], unique=True)

    op.create_table(
        "admin_sessions",
        sa.Column("id", sa.Integer(), nullable=False),
        sa.Column("admin_id", sa.Integer(), nullable=False),
        sa.Column("token_hash", sa.String(length=64), nullable=False),
        sa.Column("expires_at", sa.DateTime(timezone=True), nullable=False),
        sa.Column(
            "created_at",
            sa.DateTime(timezone=True),
            server_default=sa.text("now()"),
            nullable=False,
        ),
        sa.ForeignKeyConstraint(["admin_id"], ["admin_users.id"], ondelete="CASCADE"),
        sa.PrimaryKeyConstraint("id"),
        sa.UniqueConstraint("token_hash"),
    )
    op.create_index(
        op.f("ix_admin_sessions_admin_id"), "admin_sessions", ["admin_id"], unique=False
    )

    op.create_table(
        "admin_audit_log",
        sa.Column("id", sa.Integer(), nullable=False),
        sa.Column("admin_id", sa.Integer(), nullable=True),
        sa.Column("email", sa.String(length=255), nullable=False),
        sa.Column("action", sa.String(length=32), nullable=False),
        sa.Column("detail", sa.String(length=255), nullable=True),
        sa.Column("client_ip", sa.String(length=45), nullable=False),
        sa.Column(
            "created_at",
            sa.DateTime(timezone=True),
            server_default=sa.text("now()"),
            nullable=False,
        ),
        sa.ForeignKeyConstraint(["admin_id"], ["admin_users.id"], ondelete="SET NULL"),
        sa.PrimaryKeyConstraint("id"),
    )
    op.create_index(op.f("ix_admin_audit_log_action"), "admin_audit_log", ["action"], unique=False)
    op.create_index(
        op.f("ix_admin_audit_log_created_at"), "admin_audit_log", ["created_at"], unique=False
    )
    op.create_index(op.f("ix_admin_audit_log_email"), "admin_audit_log", ["email"], unique=False)


def downgrade() -> None:
    op.drop_index(op.f("ix_admin_audit_log_email"), table_name="admin_audit_log")
    op.drop_index(op.f("ix_admin_audit_log_created_at"), table_name="admin_audit_log")
    op.drop_index(op.f("ix_admin_audit_log_action"), table_name="admin_audit_log")
    op.drop_table("admin_audit_log")
    op.drop_index(op.f("ix_admin_sessions_admin_id"), table_name="admin_sessions")
    op.drop_table("admin_sessions")
    op.drop_index(op.f("ix_admin_users_email"), table_name="admin_users")
    op.drop_table("admin_users")
