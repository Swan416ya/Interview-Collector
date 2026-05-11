"""add wrongbook fields on questions

Revision ID: w7b8k9w0r1n2
Revises: r1a2g3c4o5p6
Create Date: 2026-05-08
"""

from __future__ import annotations

import sqlalchemy as sa
from alembic import op
from sqlalchemy import inspect

revision = "w7b8k9w0r1n2"
down_revision = "r1a2g3c4o5p6"
branch_labels = None
depends_on = None


def upgrade() -> None:
    bind = op.get_bind()
    inspector = inspect(bind)
    cols = {c["name"] for c in inspector.get_columns("questions")}
    if "wrongbook_active" not in cols:
        op.add_column(
            "questions",
            sa.Column("wrongbook_active", sa.Boolean(), nullable=False, server_default=sa.text("0")),
        )
    if "wrongbook_entered_at" not in cols:
        op.add_column("questions", sa.Column("wrongbook_entered_at", sa.DateTime(), nullable=True))
    if "wrongbook_last_wrong_at" not in cols:
        op.add_column("questions", sa.Column("wrongbook_last_wrong_at", sa.DateTime(), nullable=True))
    if "wrongbook_cleared_at" not in cols:
        op.add_column("questions", sa.Column("wrongbook_cleared_at", sa.DateTime(), nullable=True))


def downgrade() -> None:
    bind = op.get_bind()
    inspector = inspect(bind)
    cols = {c["name"] for c in inspector.get_columns("questions")}
    if "wrongbook_cleared_at" in cols:
        op.drop_column("questions", "wrongbook_cleared_at")
    if "wrongbook_last_wrong_at" in cols:
        op.drop_column("questions", "wrongbook_last_wrong_at")
    if "wrongbook_entered_at" in cols:
        op.drop_column("questions", "wrongbook_entered_at")
    if "wrongbook_active" in cols:
        op.drop_column("questions", "wrongbook_active")
