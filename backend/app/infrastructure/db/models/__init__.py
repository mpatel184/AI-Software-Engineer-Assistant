"""ORM model registry.

All models are imported here so Alembic autogenerate and the metadata see them.
"""
from app.infrastructure.db.models.analysis import AnalysisModel
from app.infrastructure.db.models.chat import ChatMessageModel
from app.infrastructure.db.models.document import DocumentModel
from app.infrastructure.db.models.report import ReportModel
from app.infrastructure.db.models.repository import (
    EmbeddingsMetadataModel,
    RepositoryModel,
)
from app.infrastructure.db.models.user import RefreshTokenModel, UserModel

__all__ = [
    "UserModel",
    "RefreshTokenModel",
    "RepositoryModel",
    "EmbeddingsMetadataModel",
    "AnalysisModel",
    "DocumentModel",
    "ChatMessageModel",
    "ReportModel",
]
