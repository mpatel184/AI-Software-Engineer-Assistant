"""symbols table (code symbol index)

Revision ID: 0007_symbols
Revises: 0006_reports
Create Date: 2026-06-21
"""
from __future__ import annotations

from collections.abc import Sequence

import sqlalchemy as sa
from alembic import op
from sqlalchemy.dialects import postgresql

revision: str = "0007_symbols"
down_revision: str | None = "0006_reports"
branch_labels: str | Sequence[str] | None = None
depends_on: str | Sequence[str] | None = None

_SYMBOL_KINDS = ("function", "method", "class", "route", "import", "variable")


def upgrade() -> None:
    symbol_kind = postgresql.ENUM(*_SYMBOL_KINDS, name="symbol_kind")
    symbol_kind.create(op.get_bind(), checkfirst=True)

    op.create_table(
        "symbols",
        sa.Column("id", postgresql.UUID(as_uuid=True), primary_key=True),
        sa.Column("repository_id", postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column("file_path", sa.String(length=1000), nullable=False),
        sa.Column(
            "kind",
            postgresql.ENUM(*_SYMBOL_KINDS, name="symbol_kind", create_type=False),
            nullable=False,
        ),
        sa.Column("name", sa.String(length=500), nullable=False),
        sa.Column("qualified_name", sa.String(length=1000), nullable=False),
        sa.Column("signature", sa.Text(), server_default="", nullable=False),
        sa.Column("start_line", sa.Integer(), server_default="0", nullable=False),
        sa.Column("end_line", sa.Integer(), server_default="0", nullable=False),
        sa.Column("language", sa.String(length=50), nullable=True),
        sa.Column("parent_name", sa.String(length=500), nullable=True),
        sa.Column("docstring", sa.Text(), nullable=True),
        sa.ForeignKeyConstraint(["repository_id"], ["repositories.id"], ondelete="CASCADE"),
    )
    op.create_index("ix_symbols_repo_name", "symbols", ["repository_id", "name"])
    op.create_index("ix_symbols_repo_kind", "symbols", ["repository_id", "kind"])


def downgrade() -> None:
    op.drop_index("ix_symbols_repo_kind", table_name="symbols")
    op.drop_index("ix_symbols_repo_name", table_name="symbols")
    op.drop_table("symbols")
    postgresql.ENUM(name="symbol_kind").drop(op.get_bind(), checkfirst=True)
