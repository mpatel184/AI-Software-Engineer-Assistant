"""documents table

Revision ID: 0004_documents
Revises: 0003_analyses
Create Date: 2026-06-20
"""
from __future__ import annotations

from collections.abc import Sequence

import sqlalchemy as sa
from alembic import op
from sqlalchemy.dialects import postgresql

revision: str = "0004_documents"
down_revision: str | None = "0003_analyses"
branch_labels: str | Sequence[str] | None = None
depends_on: str | Sequence[str] | None = None

_DOC_TYPES = ("readme", "api_docs", "function_docs", "class_docs")
_DOC_FORMATS = ("markdown", "html")


def upgrade() -> None:
    doc_type = postgresql.ENUM(*_DOC_TYPES, name="document_type")
    doc_type.create(op.get_bind(), checkfirst=True)
    doc_format = postgresql.ENUM(*_DOC_FORMATS, name="document_format")
    doc_format.create(op.get_bind(), checkfirst=True)

    op.create_table(
        "documents",
        sa.Column("id", postgresql.UUID(as_uuid=True), primary_key=True),
        sa.Column("repository_id", postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column(
            "type",
            postgresql.ENUM(*_DOC_TYPES, name="document_type", create_type=False),
            nullable=False,
        ),
        sa.Column("title", sa.String(length=200), nullable=False),
        sa.Column("content", sa.Text(), server_default="", nullable=False),
        sa.Column(
            "format",
            postgresql.ENUM(*_DOC_FORMATS, name="document_format", create_type=False),
            server_default="markdown",
            nullable=False,
        ),
        # job_status enum already created by migration 0003 — reference it.
        sa.Column(
            "status",
            postgresql.ENUM(
                "queued", "running", "completed", "failed",
                name="job_status", create_type=False,
            ),
            server_default="queued",
            nullable=False,
        ),
        sa.Column("error_message", sa.Text(), nullable=True),
        sa.Column("created_at", sa.DateTime(timezone=True), server_default=sa.text("now()"), nullable=False),
        sa.Column("updated_at", sa.DateTime(timezone=True), server_default=sa.text("now()"), nullable=False),
        sa.ForeignKeyConstraint(["repository_id"], ["repositories.id"], ondelete="CASCADE"),
    )
    op.create_index("uq_documents_repo_type", "documents", ["repository_id", "type"], unique=True)


def downgrade() -> None:
    op.drop_table("documents")
    postgresql.ENUM(name="document_format").drop(op.get_bind(), checkfirst=True)
    postgresql.ENUM(name="document_type").drop(op.get_bind(), checkfirst=True)
