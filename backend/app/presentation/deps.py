"""Dependency-injection providers wiring HTTP requests to use cases.

Keeps the composition root in one place: repositories, security adapters, and
services are assembled here and injected into routers.
"""
from __future__ import annotations

from typing import Annotated

from fastapi import Depends
from fastapi.security import HTTPAuthorizationCredentials, HTTPBearer
from sqlalchemy.ext.asyncio import AsyncSession

from app.application.interfaces.security import PasswordHasher, TokenService
from app.application.use_cases.analysis.service import AnalysisService
from app.application.use_cases.auth.service import AuthService
from app.application.use_cases.chat.service import ChatService
from app.application.use_cases.documentation.service import DocumentationService
from app.application.use_cases.reports.service import ReportService
from app.application.use_cases.repositories.service import RepositoryService
from app.application.use_cases.tests.service import TestGenerationService
from app.core.config import Settings, get_settings
from app.domain.entities.user import User
from app.domain.enums import TokenType
from app.domain.exceptions import AuthenticationError
from app.infrastructure.auth.jwt_service import JwtTokenService
from app.infrastructure.auth.password import Argon2PasswordHasher
from app.infrastructure.db.repositories.refresh_token_repository import (
    SqlAlchemyRefreshTokenRepository,
)
from app.infrastructure.db.repositories.analysis_repository import (
    SqlAlchemyAnalysisRepository,
)
from app.infrastructure.db.repositories.document_repository import (
    SqlAlchemyDocumentRepository,
)
from app.infrastructure.db.repositories.report_repository import (
    SqlAlchemyReportRepository,
)
from app.infrastructure.db.repositories.repository_repository import (
    SqlAlchemyRepositoryRepository,
)
from app.infrastructure.db.repositories.user_repository import SqlAlchemyUserRepository
from app.infrastructure.db.repositories.chat_repository import (
    SqlAlchemyChatMessageRepository,
)
from app.infrastructure.db.session import get_session
from app.infrastructure.llm.factory import get_llm_provider
from app.infrastructure.vector.chroma_store import ChromaVectorStore
from app.infrastructure.vector.embedder import FastEmbedEmbedder
from app.workers.dispatcher import (
    CeleryAnalysisDispatcher,
    CeleryDocumentationDispatcher,
    CeleryIndexDispatcher,
)

SettingsDep = Annotated[Settings, Depends(get_settings)]
SessionDep = Annotated[AsyncSession, Depends(get_session)]

# Stateless singletons. Settings is itself a cached singleton (get_settings),
# so the token service can be built once lazily and reused.
_password_hasher = Argon2PasswordHasher()
_token_service_singleton: JwtTokenService | None = None


def get_password_hasher() -> PasswordHasher:
    return _password_hasher


def get_token_service(settings: SettingsDep) -> TokenService:
    global _token_service_singleton
    if _token_service_singleton is None:
        _token_service_singleton = JwtTokenService(settings)
    return _token_service_singleton


def get_auth_service(
    session: SessionDep,
    hasher: Annotated[PasswordHasher, Depends(get_password_hasher)],
    tokens: Annotated[TokenService, Depends(get_token_service)],
) -> AuthService:
    return AuthService(
        users=SqlAlchemyUserRepository(session),
        refresh_tokens=SqlAlchemyRefreshTokenRepository(session),
        hasher=hasher,
        tokens=tokens,
    )


AuthServiceDep = Annotated[AuthService, Depends(get_auth_service)]

_index_dispatcher = CeleryIndexDispatcher()


def get_repository_service(session: SessionDep) -> RepositoryService:
    return RepositoryService(
        repositories=SqlAlchemyRepositoryRepository(session),
        dispatcher=_index_dispatcher,
    )


RepositoryServiceDep = Annotated[RepositoryService, Depends(get_repository_service)]

_analysis_dispatcher = CeleryAnalysisDispatcher()


def get_analysis_service(session: SessionDep) -> AnalysisService:
    return AnalysisService(
        repositories=SqlAlchemyRepositoryRepository(session),
        analyses=SqlAlchemyAnalysisRepository(session),
        dispatcher=_analysis_dispatcher,
    )


AnalysisServiceDep = Annotated[AnalysisService, Depends(get_analysis_service)]

_documentation_dispatcher = CeleryDocumentationDispatcher()


def get_documentation_service(session: SessionDep) -> DocumentationService:
    return DocumentationService(
        repositories=SqlAlchemyRepositoryRepository(session),
        documents=SqlAlchemyDocumentRepository(session),
        dispatcher=_documentation_dispatcher,
    )


DocumentationServiceDep = Annotated[
    DocumentationService, Depends(get_documentation_service)
]


def get_test_generation_service(
    session: SessionDep, settings: SettingsDep
) -> TestGenerationService:
    return TestGenerationService(
        repositories=SqlAlchemyRepositoryRepository(session),
        llm=get_llm_provider(settings),
    )


TestGenerationServiceDep = Annotated[
    TestGenerationService, Depends(get_test_generation_service)
]


def get_chat_service(session: SessionDep, settings: SettingsDep) -> ChatService:
    return ChatService(
        repositories=SqlAlchemyRepositoryRepository(session),
        messages=SqlAlchemyChatMessageRepository(session),
        embedder=FastEmbedEmbedder(settings.embedding_model),
        vectors=ChromaVectorStore(host=settings.chroma_host, port=settings.chroma_port),
        llm=get_llm_provider(settings),
    )


ChatServiceDep = Annotated[ChatService, Depends(get_chat_service)]


def get_report_service(session: SessionDep) -> ReportService:
    return ReportService(
        repositories=SqlAlchemyRepositoryRepository(session),
        analyses=SqlAlchemyAnalysisRepository(session),
        reports=SqlAlchemyReportRepository(session),
    )


ReportServiceDep = Annotated[ReportService, Depends(get_report_service)]

_bearer = HTTPBearer(auto_error=False)


async def get_current_user(
    session: SessionDep,
    tokens: Annotated[TokenService, Depends(get_token_service)],
    credentials: Annotated[HTTPAuthorizationCredentials | None, Depends(_bearer)],
) -> User:
    if credentials is None:
        raise AuthenticationError("Authentication credentials were not provided.")

    claims = tokens.decode(credentials.credentials, expected_type=TokenType.ACCESS)
    user = await SqlAlchemyUserRepository(session).get_by_id(claims.subject)
    if user is None or not user.is_active:
        raise AuthenticationError("User account is invalid or disabled.")
    return user


CurrentUser = Annotated[User, Depends(get_current_user)]
