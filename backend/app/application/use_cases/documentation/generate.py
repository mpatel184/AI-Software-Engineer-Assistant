"""Documentation generation pipeline (runs in the worker).

Builds a bounded source sample (wrapped as untrusted data) and asks Claude to
produce Markdown documentation tailored to the requested document type.
"""
from __future__ import annotations

import uuid

from app.application.interfaces.llm import LLMPort, wrap_untrusted
from app.application.interfaces.repositories import (
    DocumentRepository,
    RepositoryRepository,
)
from app.application.prompts.documentation import DOC_INSTRUCTIONS, DOC_SYSTEM
from app.application.services.repo_context import build_source_sample
from app.core.logging import get_logger
from app.domain.enums import JobStatus
from app.domain.exceptions import NotFoundError

logger = get_logger("documentation.generate")

_SYSTEM = DOC_SYSTEM
_INSTRUCTIONS = DOC_INSTRUCTIONS


class GenerateDocumentationService:
    def __init__(
        self,
        *,
        documents: DocumentRepository,
        repositories: RepositoryRepository,
        llm: LLMPort,
    ) -> None:
        self._docs = documents
        self._repos = repositories
        self._llm = llm

    async def run(self, document_id: uuid.UUID) -> None:
        document = await self._docs.get(document_id)
        if document is None:
            raise NotFoundError("Document not found.")
        repo = await self._repos.get(document.repository_id)
        if repo is None or not repo.clone_path:
            await self._docs.update_status(
                document_id, JobStatus.FAILED, error_message="Repository unavailable."
            )
            raise NotFoundError("Repository working tree unavailable.")

        try:
            await self._docs.update_status(document_id, JobStatus.RUNNING)

            sample = build_source_sample(repo.clone_path)
            if not sample.strip():
                raise ValueError("No source files available to document.")

            instruction = _INSTRUCTIONS[document.type]
            user = (
                f"{instruction}\n\nReturn only Markdown, no preamble.\n\n"
                + wrap_untrusted(sample, label="repository source")
            )
            content = await self._llm.complete(system=_SYSTEM, user=user, max_tokens=8000)

            document.content = content.strip()
            document.status = JobStatus.COMPLETED
            await self._docs.update(document)
            logger.info(
                "doc_generated",
                document_id=str(document_id),
                type=document.type.value,
                chars=len(content),
            )
        except Exception as exc:  # noqa: BLE001
            logger.exception("doc_generation_failed", document_id=str(document_id))
            await self._docs.update_status(
                document_id, JobStatus.FAILED, error_message=str(exc)[:500]
            )
            raise
