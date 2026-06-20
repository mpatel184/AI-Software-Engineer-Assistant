"""repository and embeddings_metadata tables

Revision ID: 0002_repos
Revises: 0001_auth
Create Date: 2026-06-20
"""
from __future__ import annotations

from collections.abc import Sequence

import sqlalchemy as sa
from alembic import op
from sqlalchemy.dialects import postgresql

revision: str = "0002_repos"
down_revision: str | None = "0001_auth"
branch_labels: str | Sequence[str] | None = None
depends_on: str | Sequence[str] | None = None


def upgrade() -> None:
    repo_source = postgresql.ENUM("github", "upload", name="repo_source")
    repo_source.create(op.get_bind(), checkfirst=True)
    repo_status = postgresql.ENUM(
        "pending", "cloning", "indexing", "ready", "failed", name="repo_status"
    )
    repo_status.create(op.get_bind(), checkfirst=True)

    op.create_table(
        "repositories",
        sa.Column("id", postgresql.UUID(as_uuid=True), primary_key=True),
        sa.Column("user_id", postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column("name", sa.String(length=200), nullable=False),
        sa.Column(
            "source",
            postgresql.ENUM("github", "upload", name="repo_source", create_type=False),
            nullable=False,
        ),
        sa.Column("github_url", sa.String(length=500), nullable=True),
        sa.Column("default_branch", sa.String(length=200), nullable=True),
        sa.Column("clone_path", sa.String(length=500), nullable=True),
        sa.Column(
            "status",
            postgresql.ENUM(
                "pending", "cloning", "indexing", "ready", "failed",
                name="repo_status", create_type=False,
            ),
            server_default="pending",
            nullable=False,
        ),
        sa.Column("primary_language", sa.String(length=50), nullable=True),
        sa.Column("languages", postgresql.JSONB(), server_default=sa.text("'{}'"), nullable=False),
        sa.Column("file_count", sa.Integer(), server_default=sa.text("0"), nullable=False),
        sa.Column("total_lines", sa.Integer(), server_default=sa.text("0"), nullable=False),
        sa.Column("size_bytes", sa.BigInteger(), server_default=sa.text("0"), nullable=False),
        sa.Column("commit_sha", sa.String(length=40), nullable=True),
        sa.Column("error_message", sa.Text(), nullable=True),
        sa.Column("indexed_at", sa.DateTime(timezone=True), nullable=True),
        sa.Column("created_at", sa.DateTime(timezone=True), server_default=sa.text("now()"), nullable=False),
        sa.Column("updated_at", sa.DateTime(timezone=True), server_default=sa.text("now()"), nullable=False),
        sa.ForeignKeyConstraint(["user_id"], ["users.id"], ondelete="CASCADE"),
    )
    op.create_index("ix_repositories_user_id", "repositories", ["user_id"])
    op.create_index("ix_repositories_user_status", "repositories", ["user_id", "status"])

    op.create_table(
        "embeddings_metadata",
        sa.Column("id", postgresql.UUID(as_uuid=True), primary_key=True),
        sa.Column("repository_id", postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column("chroma_id", sa.String(length=100), nullable=False),
        sa.Column("file_path", sa.String(length=1000), nullable=False),
        sa.Column("language", sa.String(length=50), nullable=True),
        sa.Column("chunk_index", sa.Integer(), nullable=False),
        sa.Column("start_line", sa.Integer(), nullable=False),
        sa.Column("end_line", sa.Integer(), nullable=False),
        sa.Column("token_count", sa.Integer(), server_default=sa.text("0"), nullable=False),
        sa.Column("content_hash", sa.String(length=64), nullable=False),
        sa.Column("created_at", sa.DateTime(timezone=True), server_default=sa.text("now()"), nullable=False),
        sa.ForeignKeyConstraint(["repository_id"], ["repositories.id"], ondelete="CASCADE"),
    )
    op.create_index("ix_embeddings_repo_id", "embeddings_metadata", ["repository_id"])
    op.create_index("ix_embeddings_repo_file", "embeddings_metadata", ["repository_id", "file_path"])
    op.create_index(
        "uq_embeddings_repo_chroma",
        "embeddings_metadata",
        ["repository_id", "chroma_id"],
        unique=True,
    )


def downgrade() -> None:
    op.drop_table("embeddings_metadata")
    op.drop_table("repositories")
    postgresql.ENUM(name="repo_status").drop(op.get_bind(), checkfirst=True)
    postgresql.ENUM(name="repo_source").drop(op.get_bind(), checkfirst=True)
