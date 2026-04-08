"""add practice sessions and record session id

Revision ID: 34b37230d913
Revises: c6331ca1e535
Create Date: 2026-04-08 20:51:46.242853
"""
from __future__ import annotations

from alembic import op
import sqlalchemy as sa
from sqlalchemy import inspect



# revision identifiers, used by Alembic.
revision = '34b37230d913'
down_revision = 'c6331ca1e535'
branch_labels = None
depends_on = None


def upgrade() -> None:
    bind = op.get_bind()
    inspector = inspect(bind)
    tables = set(inspector.get_table_names())

    if "practice_sessions" not in tables:
        op.create_table(
            "practice_sessions",
            sa.Column("id", sa.Integer(), primary_key=True, nullable=False),
            sa.Column("total_score", sa.Integer(), nullable=False, server_default="0"),
            sa.Column("completed_at", sa.DateTime(), nullable=True),
            sa.Column("created_at", sa.DateTime(), nullable=False, server_default=sa.text("now()")),
        )
        op.create_index(op.f("ix_practice_sessions_id"), "practice_sessions", ["id"], unique=False)

    practice_cols = {col["name"] for col in inspector.get_columns("practice_records")}
    if "session_id" not in practice_cols:
        op.add_column("practice_records", sa.Column("session_id", sa.Integer(), nullable=True))
        op.create_index(op.f("ix_practice_records_session_id"), "practice_records", ["session_id"], unique=False)


def downgrade() -> None:
    bind = op.get_bind()
    inspector = inspect(bind)
    tables = set(inspector.get_table_names())
    if "practice_records" in tables:
        cols = {col["name"] for col in inspector.get_columns("practice_records")}
        if "session_id" in cols:
            op.drop_index(op.f("ix_practice_records_session_id"), table_name="practice_records")
            op.drop_column("practice_records", "session_id")

    if "practice_sessions" in tables:
        op.drop_index(op.f("ix_practice_sessions_id"), table_name="practice_sessions")
        op.drop_table("practice_sessions")

