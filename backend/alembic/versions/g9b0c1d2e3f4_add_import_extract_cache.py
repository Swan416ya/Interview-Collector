"""add import_extract_cache for preview dedupe

Revision ID: g9b0c1d2e3f4
Revises: f8a1c2d3e4b5
Create Date: 2026-05-08
"""
from __future__ import annotations

from alembic import op
import sqlalchemy as sa
from sqlalchemy import inspect

revision = "g9b0c1d2e3f4"
down_revision = "f8a1c2d3e4b5"
branch_labels = None
depends_on = None


def upgrade() -> None:
    bind = op.get_bind()
    inspector = inspect(bind)
    if "import_extract_cache" in inspector.get_table_names():
        return
    op.create_table(
        "import_extract_cache",
        sa.Column("id", sa.Integer(), autoincrement=True, nullable=False),
        sa.Column("cache_key", sa.String(length=64), nullable=False),
        sa.Column("payload_json", sa.Text(), nullable=False),
        sa.Column("expires_at", sa.DateTime(), nullable=False),
        sa.Column("created_at", sa.DateTime(), server_default=sa.text("CURRENT_TIMESTAMP"), nullable=False),
        sa.PrimaryKeyConstraint("id"),
        sa.UniqueConstraint("cache_key"),
    )
    op.create_index(op.f("ix_import_extract_cache_expires_at"), "import_extract_cache", ["expires_at"], unique=False)


def downgrade() -> None:
    bind = op.get_bind()
    inspector = inspect(bind)
    if "import_extract_cache" not in inspector.get_table_names():
        return
    op.drop_index(op.f("ix_import_extract_cache_expires_at"), table_name="import_extract_cache")
    op.drop_table("import_extract_cache")
