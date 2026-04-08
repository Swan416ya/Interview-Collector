"""add mastery and practice records

Revision ID: c6331ca1e535
Revises: 997cec13b8b0
Create Date: 2026-04-08 20:42:58.122929
"""
from __future__ import annotations

from alembic import op
import sqlalchemy as sa
from sqlalchemy import inspect



# revision identifiers, used by Alembic.
revision = 'c6331ca1e535'
down_revision = '997cec13b8b0'
branch_labels = None
depends_on = None


def upgrade() -> None:
    bind = op.get_bind()
    inspector = inspect(bind)

    question_cols = {col["name"] for col in inspector.get_columns("questions")}
    if "mastery_score" not in question_cols:
        op.add_column("questions", sa.Column("mastery_score", sa.Integer(), nullable=False, server_default="0"))

    tables = set(inspector.get_table_names())
    if "practice_records" not in tables:
        op.create_table(
            "practice_records",
            sa.Column("id", sa.Integer(), primary_key=True, nullable=False),
            sa.Column("question_id", sa.Integer(), nullable=False),
            sa.Column("user_answer", sa.Text(), nullable=False, server_default=""),
            sa.Column("ai_answer", sa.Text(), nullable=False, server_default=""),
            sa.Column("ai_score", sa.Integer(), nullable=False, server_default="0"),
            sa.Column("created_at", sa.DateTime(), nullable=False, server_default=sa.text("now()")),
        )
        op.create_index(op.f("ix_practice_records_id"), "practice_records", ["id"], unique=False)
        op.create_index(op.f("ix_practice_records_question_id"), "practice_records", ["question_id"], unique=False)


def downgrade() -> None:
    bind = op.get_bind()
    inspector = inspect(bind)
    tables = set(inspector.get_table_names())

    if "practice_records" in tables:
        op.drop_index(op.f("ix_practice_records_question_id"), table_name="practice_records")
        op.drop_index(op.f("ix_practice_records_id"), table_name="practice_records")
        op.drop_table("practice_records")

    question_cols = {col["name"] for col in inspector.get_columns("questions")}
    if "mastery_score" in question_cols:
        op.drop_column("questions", "mastery_score")

