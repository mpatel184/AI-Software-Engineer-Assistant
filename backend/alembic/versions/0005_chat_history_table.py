"""chat_history table

Revision ID: 0005_chat_history
Revises: 0004_documents
Create Date: 2026-06-21
"""
from __future__ import annotations

from collections.abc import Sequence

import sqlalchemy as sa
from alembic import op
from sqlalchemy.dialects import postgresql

revision: str = "0005_chat_history"
down_revision: str | None = "0004_documents"
branch_labels: str | Sequence[str] | None = None
depends_on: str | Sequence[str] | None = None

_CHAT_ROLES = ("user", "assistant")


def upgrade() -> None:
    chat_role = postgresql.ENUM(*_CHAT_ROLES, name="chat_role")
    chat_role.create(op.get_bind(), checkfirst=True)

    op.create_table(
        "chat_history",
        sa.Column("id", postgresql.UUID(as_uuid=True), primary_key=True),
        sa.Column("repository_id", postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column("user_id", postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column(
            "role",
            postgresql.ENUM(*_CHAT_ROLES, name="chat_role", create_type=False),
            nullable=False,
        ),
        sa.Column("content", sa.Text(), nullable=False),
        sa.Column("sources", postgresql.JSONB(), server_default="[]", nullable=False),
        sa.Column(
            "created_at",
            sa.DateTime(timezone=True),
            server_default=sa.text("now()"),
            nullable=False,
        ),
        sa.ForeignKeyConstraint(["repository_id"], ["repositories.id"], ondelete="CASCADE"),
        sa.ForeignKeyConstraint(["user_id"], ["users.id"], ondelete="CASCADE"),
    )
    op.create_index(
        "ix_chat_repo_user_created",
        "chat_history",
        ["repository_id", "user_id", "created_at"],
    )


def downgrade() -> None:
    op.drop_index("ix_chat_repo_user_created", table_name="chat_history")
    op.drop_table("chat_history")
    postgresql.ENUM(name="chat_role").drop(op.get_bind(), checkfirst=True)
