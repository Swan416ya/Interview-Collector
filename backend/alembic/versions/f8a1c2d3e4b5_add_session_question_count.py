"""add practice_sessions.question_count

Revision ID: f8a1c2d3e4b5
Revises: e8412cd6183e
Create Date: 2026-04-11
"""
from __future__ import annotations

from alembic import op
import sqlalchemy as sa
from sqlalchemy import inspect

revision = "f8a1c2d3e4b5"
down_revision = "e8412cd6183e"
branch_labels = None
depends_on = None


def upgrade() -> None:
    bind = op.get_bind()
    inspector = inspect(bind)
    cols = {c["name"] for c in inspector.get_columns("practice_sessions")}
    if "question_count" not in cols:
        op.add_column(
            "practice_sessions",
            sa.Column("question_count", sa.Integer(), nullable=False, server_default="10"),
        )


def downgrade() -> None:
    bind = op.get_bind()
    inspector = inspect(bind)
    cols = {c["name"] for c in inspector.get_columns("practice_sessions")}
    if "question_count" in cols:
        op.drop_column("practice_sessions", "question_count")
