"""Documentation endpoints: generate, list, get."""
from __future__ import annotations

import uuid

from fastapi import APIRouter, status

from app.presentation.deps import CurrentUser, DocumentationServiceDep
from app.presentation.schemas.document import (
    DocumentResponse,
    DocumentSummary,
    GenerateDocumentRequest,
)

router = APIRouter(prefix="/repositories/{repo_id}/documents", tags=["documentation"])


@router.post("", response_model=DocumentResponse, status_code=status.HTTP_202_ACCEPTED)
async def generate_document(
    repo_id: uuid.UUID,
    payload: GenerateDocumentRequest,
    service: DocumentationServiceDep,
    user: CurrentUser,
) -> DocumentResponse:
    document = await service.generate(user_id=user.id, repo_id=repo_id, type=payload.type)
    return DocumentResponse.model_validate(document)


@router.get("", response_model=list[DocumentSummary])
async def list_documents(
    repo_id: uuid.UUID,
    service: DocumentationServiceDep,
    user: CurrentUser,
) -> list[DocumentSummary]:
    items = await service.list(user_id=user.id, repo_id=repo_id)
    return [DocumentSummary.model_validate(d) for d in items]


@router.get("/{document_id}", response_model=DocumentResponse)
async def get_document(
    repo_id: uuid.UUID,
    document_id: uuid.UUID,
    service: DocumentationServiceDep,
    user: CurrentUser,
) -> DocumentResponse:
    document = await service.get(user_id=user.id, document_id=document_id)
    return DocumentResponse.model_validate(document)
