"""reports table

Revision ID: 0006_reports
Revises: 0005_chat_history
Create Date: 2026-06-21
"""
from __future__ import annotations

from collections.abc import Sequence

import sqlalchemy as sa
from alembic import op
from sqlalchemy.dialects import postgresql

revision: str = "0006_reports"
down_revision: str | None = "0005_chat_history"
branch_labels: str | Sequence[str] | None = None
depends_on: str | Sequence[str] | None = None

_REPORT_TYPES = ("full", "analysis", "security", "bugs")


def upgrade() -> None:
    report_type = postgresql.ENUM(*_REPORT_TYPES, name="report_type")
    report_type.create(op.get_bind(), checkfirst=True)

    op.create_table(
        "reports",
        sa.Column("id", postgresql.UUID(as_uuid=True), primary_key=True),
        sa.Column("repository_id", postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column("user_id", postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column(
            "type",
            postgresql.ENUM(*_REPORT_TYPES, name="report_type", create_type=False),
            nullable=False,
        ),
        sa.Column("title", sa.String(length=200), nullable=False),
        sa.Column("content", sa.Text(), server_default="", nullable=False),
        sa.Column(
            "status",
            postgresql.ENUM(
                "queued", "running", "completed", "failed",
                name="job_status", create_type=False,
            ),
            server_default="completed",
            nullable=False,
        ),
        sa.Column("created_at", sa.DateTime(timezone=True), server_default=sa.text("now()"), nullable=False),
        sa.Column("updated_at", sa.DateTime(timezone=True), server_default=sa.text("now()"), nullable=False),
        sa.ForeignKeyConstraint(["repository_id"], ["repositories.id"], ondelete="CASCADE"),
        sa.ForeignKeyConstraint(["user_id"], ["users.id"], ondelete="CASCADE"),
    )
    op.create_index("ix_reports_repo_created", "reports", ["repository_id", "created_at"])


def downgrade() -> None:
    op.drop_index("ix_reports_repo_created", table_name="reports")
    op.drop_table("reports")
    postgresql.ENUM(name="report_type").drop(op.get_bind(), checkfirst=True)
