"""analyses table

Revision ID: 0003_analyses
Revises: 0002_repos
Create Date: 2026-06-20
"""
from __future__ import annotations

from collections.abc import Sequence

import sqlalchemy as sa
from alembic import op
from sqlalchemy.dialects import postgresql

revision: str = "0003_analyses"
down_revision: str | None = "0002_repos"
branch_labels: str | Sequence[str] | None = None
depends_on: str | Sequence[str] | None = None

_ANALYSIS_TYPES = (
    "architecture", "dependencies", "complexity", "duplication",
    "dead_code", "bugs", "security",
)
_JOB_STATUSES = ("queued", "running", "completed", "failed")


def upgrade() -> None:
    analysis_type = postgresql.ENUM(*_ANALYSIS_TYPES, name="analysis_type")
    analysis_type.create(op.get_bind(), checkfirst=True)
    job_status = postgresql.ENUM(*_JOB_STATUSES, name="job_status")
    job_status.create(op.get_bind(), checkfirst=True)

    op.create_table(
        "analyses",
        sa.Column("id", postgresql.UUID(as_uuid=True), primary_key=True),
        sa.Column("repository_id", postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column(
            "type",
            postgresql.ENUM(*_ANALYSIS_TYPES, name="analysis_type", create_type=False),
            nullable=False,
        ),
        sa.Column(
            "status",
            postgresql.ENUM(*_JOB_STATUSES, name="job_status", create_type=False),
            server_default="queued",
            nullable=False,
        ),
        sa.Column("summary", postgresql.JSONB(), server_default=sa.text("'{}'"), nullable=False),
        sa.Column("metrics", postgresql.JSONB(), server_default=sa.text("'{}'"), nullable=False),
        sa.Column("score", sa.Integer(), nullable=True),
        sa.Column("error_message", sa.Text(), nullable=True),
        sa.Column("started_at", sa.DateTime(timezone=True), nullable=True),
        sa.Column("completed_at", sa.DateTime(timezone=True), nullable=True),
        sa.Column("created_at", sa.DateTime(timezone=True), server_default=sa.text("now()"), nullable=False),
        sa.ForeignKeyConstraint(["repository_id"], ["repositories.id"], ondelete="CASCADE"),
    )
    op.create_index("ix_analyses_repo_type", "analyses", ["repository_id", "type"])
    op.create_index("ix_analyses_repo_created", "analyses", ["repository_id", "created_at"])


def downgrade() -> None:
    op.drop_table("analyses")
    postgresql.ENUM(name="analysis_type").drop(op.get_bind(), checkfirst=True)
    postgresql.ENUM(name="job_status").drop(op.get_bind(), checkfirst=True)
