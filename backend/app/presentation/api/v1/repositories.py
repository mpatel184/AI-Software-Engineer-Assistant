"""Repository endpoints: create (GitHub), upload (zip), list, get, delete, reindex."""
from __future__ import annotations

import tempfile
import uuid
from pathlib import Path
from typing import Annotated

from fastapi import APIRouter, Depends, File, Form, UploadFile, status

from app.core.config import get_settings
from app.domain.enums import RepoStatus
from app.infrastructure.storage.archive import extract_zip_safely
from app.presentation.deps import CurrentUser, RepositoryServiceDep
from app.presentation.schemas.common import Page, PaginationParams
from app.presentation.schemas.repository import (
    CreateRepositoryFromGitHubRequest,
    RepositoryResponse,
)

router = APIRouter(prefix="/repositories", tags=["repositories"])

UPLOAD_CHUNK = 1024 * 1024  # 1 MB streaming read


@router.post("", response_model=RepositoryResponse, status_code=status.HTTP_201_CREATED)
async def create_from_github(
    payload: CreateRepositoryFromGitHubRequest,
    service: RepositoryServiceDep,
    user: CurrentUser,
) -> RepositoryResponse:
    repo = await service.create_from_github(
        user_id=user.id, github_url=payload.github_url, name=payload.name
    )
    return RepositoryResponse.model_validate(repo)


@router.post("/upload", response_model=RepositoryResponse, status_code=status.HTTP_201_CREATED)
async def upload_repository(
    service: RepositoryServiceDep,
    user: CurrentUser,
    name: Annotated[str, Form(max_length=200)],
    file: Annotated[UploadFile, File()],
) -> RepositoryResponse:
    from app.domain.exceptions import ValidationError

    if not (file.filename or "").lower().endswith(".zip"):
        raise ValidationError("Only .zip uploads are supported.")

    settings = get_settings()
    max_bytes = settings.max_repo_size_mb * 1024 * 1024
    repo_id = uuid.uuid4()
    dest_dir = str(Path(settings.repo_storage_path) / str(repo_id))

    # Stream the upload to a temp file with a hard size cap, then extract safely.
    written = 0
    with tempfile.NamedTemporaryFile(suffix=".zip", delete=False) as tmp:
        tmp_path = tmp.name
        while chunk := await file.read(UPLOAD_CHUNK):
            written += len(chunk)
            if written > max_bytes:
                Path(tmp_path).unlink(missing_ok=True)
                raise ValidationError("Uploaded file exceeds the maximum allowed size.")
            tmp.write(chunk)

    try:
        extract_zip_safely(zip_path=tmp_path, dest_dir=dest_dir, max_total_bytes=max_bytes)
    finally:
        Path(tmp_path).unlink(missing_ok=True)

    repo = await service.create_from_upload(
        user_id=user.id, name=name, clone_path=dest_dir
    )
    return RepositoryResponse.model_validate(repo)


@router.get("", response_model=Page[RepositoryResponse])
async def list_repositories(
    service: RepositoryServiceDep,
    user: CurrentUser,
    pagination: Annotated[PaginationParams, Depends()],
    status_filter: RepoStatus | None = None,
    search: str | None = None,
) -> Page[RepositoryResponse]:
    result = await service.list(
        user_id=user.id,
        status=status_filter,
        search=search,
        limit=pagination.limit,
        offset=pagination.offset,
    )
    return Page.create(
        items=[RepositoryResponse.model_validate(r) for r in result.items],
        total=result.total,
        page=pagination.page,
        page_size=pagination.page_size,
    )


@router.get("/{repo_id}", response_model=RepositoryResponse)
async def get_repository(
    repo_id: uuid.UUID, service: RepositoryServiceDep, user: CurrentUser
) -> RepositoryResponse:
    repo = await service.get(user_id=user.id, repo_id=repo_id)
    return RepositoryResponse.model_validate(repo)


@router.post("/{repo_id}/reindex", response_model=RepositoryResponse)
async def reindex_repository(
    repo_id: uuid.UUID, service: RepositoryServiceDep, user: CurrentUser
) -> RepositoryResponse:
    repo = await service.reindex(user_id=user.id, repo_id=repo_id)
    return RepositoryResponse.model_validate(repo)


@router.delete("/{repo_id}", status_code=status.HTTP_204_NO_CONTENT)
async def delete_repository(
    repo_id: uuid.UUID, service: RepositoryServiceDep, user: CurrentUser
) -> None:
    await service.delete(user_id=user.id, repo_id=repo_id)
