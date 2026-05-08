"""add document_chunks for RAG knowledge base

Revision ID: r1a2g3c4o5p6
Revises: g9b0c1d2e3f4
Create Date: 2026-05-08
"""

from __future__ import annotations

import sqlalchemy as sa
from alembic import op
from sqlalchemy import inspect

revision = "r1a2g3c4o5p6"
down_revision = "g9b0c1d2e3f4"
branch_labels = None
depends_on = None


def upgrade() -> None:
    bind = op.get_bind()
    inspector = inspect(bind)
    if "document_chunks" in inspector.get_table_names():
        return
    op.create_table(
        "document_chunks",
        sa.Column("id", sa.Integer(), autoincrement=True, nullable=False),
        sa.Column("question_id", sa.Integer(), nullable=False),
        sa.Column("source_type", sa.String(length=32), nullable=False),
        sa.Column("chunk_index", sa.Integer(), nullable=False, server_default="0"),
        sa.Column("text", sa.Text(), nullable=False),
        sa.Column("chunk_meta", sa.JSON(), nullable=True),
        sa.Column("created_at", sa.DateTime(), server_default=sa.text("CURRENT_TIMESTAMP"), nullable=False),
        sa.ForeignKeyConstraint(["question_id"], ["questions.id"], ondelete="CASCADE"),
        sa.PrimaryKeyConstraint("id"),
    )
    op.create_index(op.f("ix_document_chunks_question_id"), "document_chunks", ["question_id"], unique=False)
    if bind.dialect.name == "mysql":
        op.create_index(
            "ix_document_chunks_ft_text",
            "document_chunks",
            ["text"],
            unique=False,
            mysql_prefix="FULLTEXT",
        )


def downgrade() -> None:
    bind = op.get_bind()
    inspector = inspect(bind)
    if "document_chunks" not in inspector.get_table_names():
        return
    if bind.dialect.name == "mysql":
        op.drop_index("ix_document_chunks_ft_text", table_name="document_chunks")
    op.drop_index(op.f("ix_document_chunks_question_id"), table_name="document_chunks")
    op.drop_table("document_chunks")
