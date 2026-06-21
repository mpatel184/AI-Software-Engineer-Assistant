"""Report endpoints: generate, list, get, and PDF export."""
from __future__ import annotations

import re
import uuid

from fastapi import APIRouter, Response, status

from app.infrastructure.reporting.pdf import markdown_to_pdf
from app.presentation.deps import CurrentUser, ReportServiceDep
from app.presentation.schemas.report import (
    GenerateReportRequest,
    ReportResponse,
    ReportSummary,
)

router = APIRouter(prefix="/repositories/{repo_id}/reports", tags=["reports"])


def _slug(value: str) -> str:
    return re.sub(r"[^a-z0-9]+", "-", value.lower()).strip("-") or "report"


@router.post("", response_model=ReportResponse, status_code=status.HTTP_201_CREATED)
async def generate_report(
    repo_id: uuid.UUID,
    payload: GenerateReportRequest,
    service: ReportServiceDep,
    user: CurrentUser,
) -> ReportResponse:
    report = await service.generate(user_id=user.id, repo_id=repo_id, type=payload.type)
    return ReportResponse.model_validate(report)


@router.get("", response_model=list[ReportSummary])
async def list_reports(
    repo_id: uuid.UUID,
    service: ReportServiceDep,
    user: CurrentUser,
) -> list[ReportSummary]:
    items = await service.list(user_id=user.id, repo_id=repo_id)
    return [ReportSummary.model_validate(r) for r in items]


@router.get("/{report_id}", response_model=ReportResponse)
async def get_report(
    repo_id: uuid.UUID,
    report_id: uuid.UUID,
    service: ReportServiceDep,
    user: CurrentUser,
) -> ReportResponse:
    report = await service.get(user_id=user.id, report_id=report_id)
    return ReportResponse.model_validate(report)


@router.get("/{report_id}/pdf")
async def download_report_pdf(
    repo_id: uuid.UUID,
    report_id: uuid.UUID,
    service: ReportServiceDep,
    user: CurrentUser,
) -> Response:
    report = await service.get(user_id=user.id, report_id=report_id)
    pdf = markdown_to_pdf(report.content)
    filename = f"{_slug(report.title)}.pdf"
    return Response(
        content=pdf,
        media_type="application/pdf",
        headers={"Content-Disposition": f'attachment; filename="{filename}"'},
    )
