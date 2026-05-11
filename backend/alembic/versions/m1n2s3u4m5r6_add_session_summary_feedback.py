"""add session_feedback_json and summary_done on practice_sessions

Revision ID: m1n2s3u4m5r6
Revises: w7b8k9w0r1n2
Create Date: 2026-05-08
"""

from __future__ import annotations

import sqlalchemy as sa
from alembic import op
from sqlalchemy import inspect

revision = "m1n2s3u4m5r6"
down_revision = "w7b8k9w0r1n2"
branch_labels = None
depends_on = None


def upgrade() -> None:
    bind = op.get_bind()
    inspector = inspect(bind)
    cols = {c["name"] for c in inspector.get_columns("practice_sessions")}
    if "session_feedback_json" not in cols:
        op.add_column("practice_sessions", sa.Column("session_feedback_json", sa.Text(), nullable=True))
    if "summary_done" not in cols:
        op.add_column(
            "practice_sessions",
            sa.Column("summary_done", sa.Boolean(), nullable=False, server_default=sa.text("0")),
        )


def downgrade() -> None:
    bind = op.get_bind()
    inspector = inspect(bind)
    cols = {c["name"] for c in inspector.get_columns("practice_sessions")}
    if "summary_done" in cols:
        op.drop_column("practice_sessions", "summary_done")
    if "session_feedback_json" in cols:
        op.drop_column("practice_sessions", "session_feedback_json")
