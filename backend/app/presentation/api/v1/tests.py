"""Test-generation endpoints: list candidate files, generate tests for a file."""
from __future__ import annotations

import uuid

from fastapi import APIRouter

from app.presentation.deps import CurrentUser, TestGenerationServiceDep
from app.presentation.schemas.test_generation import (
    GeneratedTestResponse,
    GenerateTestRequest,
    RepoFilesResponse,
)

router = APIRouter(prefix="/repositories/{repo_id}/tests", tags=["tests"])


@router.get("/files", response_model=RepoFilesResponse)
async def list_repo_files(
    repo_id: uuid.UUID,
    service: TestGenerationServiceDep,
    user: CurrentUser,
) -> RepoFilesResponse:
    files = await service.list_files(user_id=user.id, repo_id=repo_id)
    return RepoFilesResponse(files=files)


@router.post("", response_model=GeneratedTestResponse)
async def generate_tests(
    repo_id: uuid.UUID,
    payload: GenerateTestRequest,
    service: TestGenerationServiceDep,
    user: CurrentUser,
) -> GeneratedTestResponse:
    result = await service.generate(
        user_id=user.id, repo_id=repo_id, file_path=payload.file_path
    )
    return GeneratedTestResponse(
        file_path=result.file_path,
        framework=result.framework,
        test_file_path=result.test_file_path,
        test_code=result.test_code,
        notes=result.notes,
    )
