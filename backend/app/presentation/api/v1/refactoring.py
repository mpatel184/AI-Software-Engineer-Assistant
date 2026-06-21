"""Refactoring endpoints: list candidate files, suggest refactorings for a file."""
from __future__ import annotations

import uuid

from fastapi import APIRouter

from app.presentation.deps import CurrentUser, RefactoringServiceDep
from app.presentation.schemas.refactoring import (
    RefactoringResponse,
    SuggestRefactorRequest,
)
from app.presentation.schemas.test_generation import RepoFilesResponse

router = APIRouter(prefix="/repositories/{repo_id}/refactoring", tags=["refactoring"])


@router.get("/files", response_model=RepoFilesResponse)
async def list_repo_files(
    repo_id: uuid.UUID,
    service: RefactoringServiceDep,
    user: CurrentUser,
) -> RepoFilesResponse:
    files = await service.list_files(user_id=user.id, repo_id=repo_id)
    return RepoFilesResponse(files=files)


@router.post("", response_model=RefactoringResponse)
async def suggest_refactorings(
    repo_id: uuid.UUID,
    payload: SuggestRefactorRequest,
    service: RefactoringServiceDep,
    user: CurrentUser,
) -> RefactoringResponse:
    result = await service.suggest(
        user_id=user.id, repo_id=repo_id, file_path=payload.file_path
    )
    return RefactoringResponse(
        file_path=result.file_path,
        summary=result.summary,
        suggestions=result.suggestions,
    )
