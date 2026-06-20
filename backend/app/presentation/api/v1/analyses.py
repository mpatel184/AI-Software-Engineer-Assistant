"""Analysis endpoints: trigger, list, latest, get."""
from __future__ import annotations

import uuid

from fastapi import APIRouter, status

from app.domain.enums import AnalysisType
from app.domain.exceptions import NotFoundError
from app.presentation.deps import AnalysisServiceDep, CurrentUser
from app.presentation.schemas.analysis import AnalysisResponse, TriggerAnalysisRequest

router = APIRouter(prefix="/repositories/{repo_id}/analyses", tags=["analyses"])


@router.post("", response_model=AnalysisResponse, status_code=status.HTTP_202_ACCEPTED)
async def trigger_analysis(
    repo_id: uuid.UUID,
    payload: TriggerAnalysisRequest,
    service: AnalysisServiceDep,
    user: CurrentUser,
) -> AnalysisResponse:
    analysis = await service.trigger(user_id=user.id, repo_id=repo_id, type=payload.type)
    return AnalysisResponse.model_validate(analysis)


@router.get("", response_model=list[AnalysisResponse])
async def list_analyses(
    repo_id: uuid.UUID,
    service: AnalysisServiceDep,
    user: CurrentUser,
    type: AnalysisType | None = None,
) -> list[AnalysisResponse]:
    items = await service.list(user_id=user.id, repo_id=repo_id, type=type)
    return [AnalysisResponse.model_validate(a) for a in items]


@router.get("/latest", response_model=AnalysisResponse)
async def latest_analysis(
    repo_id: uuid.UUID,
    service: AnalysisServiceDep,
    user: CurrentUser,
    type: AnalysisType = AnalysisType.ARCHITECTURE,
) -> AnalysisResponse:
    analysis = await service.latest(user_id=user.id, repo_id=repo_id, type=type)
    if analysis is None:
        raise NotFoundError("No analysis found for this repository.")
    return AnalysisResponse.model_validate(analysis)


@router.get("/{analysis_id}", response_model=AnalysisResponse)
async def get_analysis(
    repo_id: uuid.UUID,
    analysis_id: uuid.UUID,
    service: AnalysisServiceDep,
    user: CurrentUser,
) -> AnalysisResponse:
    analysis = await service.get(user_id=user.id, analysis_id=analysis_id)
    return AnalysisResponse.model_validate(analysis)
