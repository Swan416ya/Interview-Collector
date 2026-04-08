"""add taxonomy and import relation tables

Revision ID: c2398a3093df
Revises: e736da847693
Create Date: 2026-04-08 18:32:03.369805
"""
from __future__ import annotations

from alembic import op
import sqlalchemy as sa



# revision identifiers, used by Alembic.
revision = 'c2398a3093df'
down_revision = 'e736da847693'
branch_labels = None
depends_on = None


def upgrade() -> None:
    op.create_table(
        "categories",
        sa.Column("id", sa.Integer(), nullable=False),
        sa.Column("name", sa.String(length=64), nullable=False),
        sa.PrimaryKeyConstraint("id"),
        sa.UniqueConstraint("name"),
    )
    op.create_index(op.f("ix_categories_id"), "categories", ["id"], unique=False)

    op.create_table(
        "roles",
        sa.Column("id", sa.Integer(), nullable=False),
        sa.Column("name", sa.String(length=64), nullable=False),
        sa.PrimaryKeyConstraint("id"),
        sa.UniqueConstraint("name"),
    )
    op.create_index(op.f("ix_roles_id"), "roles", ["id"], unique=False)

    op.create_table(
        "companies",
        sa.Column("id", sa.Integer(), nullable=False),
        sa.Column("name", sa.String(length=128), nullable=False),
        sa.PrimaryKeyConstraint("id"),
        sa.UniqueConstraint("name"),
    )
    op.create_index(op.f("ix_companies_id"), "companies", ["id"], unique=False)

    op.create_table(
        "question_roles",
        sa.Column("id", sa.Integer(), nullable=False),
        sa.Column("question_id", sa.Integer(), nullable=False),
        sa.Column("role_id", sa.Integer(), nullable=False),
        sa.ForeignKeyConstraint(["question_id"], ["questions.id"], ondelete="CASCADE"),
        sa.ForeignKeyConstraint(["role_id"], ["roles.id"], ondelete="CASCADE"),
        sa.PrimaryKeyConstraint("id"),
        sa.UniqueConstraint("question_id", "role_id", name="uq_question_role"),
    )
    op.create_index(op.f("ix_question_roles_id"), "question_roles", ["id"], unique=False)

    op.create_table(
        "question_companies",
        sa.Column("id", sa.Integer(), nullable=False),
        sa.Column("question_id", sa.Integer(), nullable=False),
        sa.Column("company_id", sa.Integer(), nullable=False),
        sa.ForeignKeyConstraint(["question_id"], ["questions.id"], ondelete="CASCADE"),
        sa.ForeignKeyConstraint(["company_id"], ["companies.id"], ondelete="CASCADE"),
        sa.PrimaryKeyConstraint("id"),
        sa.UniqueConstraint("question_id", "company_id", name="uq_question_company"),
    )
    op.create_index(op.f("ix_question_companies_id"), "question_companies", ["id"], unique=False)


def downgrade() -> None:
    op.drop_index(op.f("ix_question_companies_id"), table_name="question_companies")
    op.drop_table("question_companies")

    op.drop_index(op.f("ix_question_roles_id"), table_name="question_roles")
    op.drop_table("question_roles")

    op.drop_index(op.f("ix_companies_id"), table_name="companies")
    op.drop_table("companies")

    op.drop_index(op.f("ix_roles_id"), table_name="roles")
    op.drop_table("roles")

    op.drop_index(op.f("ix_categories_id"), table_name="categories")
    op.drop_table("categories")

