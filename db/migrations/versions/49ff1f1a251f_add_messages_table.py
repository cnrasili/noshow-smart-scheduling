"""Add messages table

Revision ID: 49ff1f1a251f
Revises: d5796cf55831
Create Date: 2026-10-01 20:20:52.303887

"""

from collections.abc import Sequence

import sqlalchemy as sa
from alembic import op

revision: str = "49ff1f1a251f"
down_revision: str | Sequence[str] | None = "d5796cf55831"
branch_labels: str | Sequence[str] | None = None
depends_on: str | Sequence[str] | None = None


def upgrade() -> None:
    op.create_table(
        "messages",
        sa.Column("id", sa.Integer(), nullable=False),
        sa.Column("appointment_id", sa.Integer(), nullable=False),
        sa.Column("patient_id", sa.Integer(), nullable=False),
        sa.Column("kind", sa.String(length=16), nullable=False),
        sa.Column("email", sa.String(length=255), nullable=False),
        sa.Column("subject", sa.String(length=255), nullable=False),
        sa.Column("body", sa.Text(), nullable=False),
        sa.Column("appointment_start", sa.DateTime(timezone=True), nullable=False),
        sa.Column("send_at", sa.DateTime(timezone=True), nullable=False),
        sa.Column("status", sa.String(length=16), nullable=False),
        sa.Column("attempts", sa.Integer(), nullable=False),
        sa.Column("error", sa.String(length=255), nullable=True),
        sa.Column("sent_at", sa.DateTime(timezone=True), nullable=True),
        sa.Column(
            "created_at",
            sa.DateTime(timezone=True),
            server_default=sa.text("now()"),
            nullable=False,
        ),
        sa.PrimaryKeyConstraint("id"),
        sa.UniqueConstraint("appointment_id", "kind"),
    )
    op.create_index(op.f("ix_messages_patient_id"), "messages", ["patient_id"], unique=False)
    op.create_index(op.f("ix_messages_send_at"), "messages", ["send_at"], unique=False)
    op.create_index(op.f("ix_messages_status"), "messages", ["status"], unique=False)


def downgrade() -> None:
    op.drop_index(op.f("ix_messages_status"), table_name="messages")
    op.drop_index(op.f("ix_messages_send_at"), table_name="messages")
    op.drop_index(op.f("ix_messages_patient_id"), table_name="messages")
    op.drop_table("messages")
