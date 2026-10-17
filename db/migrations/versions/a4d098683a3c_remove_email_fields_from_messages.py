"""Remove email fields from messages

Revision ID: a4d098683a3c
Revises: 665da867396e
Create Date: 2026-10-17 21:00:00.000000

Patient messages are demo SMS addressed by the dataset patient number, so they keep no email
address and no subject. Downgrading restores the columns with empty values.
"""

from collections.abc import Sequence

import sqlalchemy as sa
from alembic import op

revision: str = "a4d098683a3c"
down_revision: str | Sequence[str] | None = "665da867396e"
branch_labels: str | Sequence[str] | None = None
depends_on: str | Sequence[str] | None = None


def upgrade() -> None:
    op.drop_column("messages", "subject")
    op.drop_column("messages", "email")


def downgrade() -> None:
    for name in ["email", "subject"]:
        op.add_column(
            "messages",
            sa.Column(name, sa.String(length=255), nullable=False, server_default=""),
        )
        op.alter_column("messages", name, server_default=None)
