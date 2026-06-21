"""RAG chat endpoints: ask a question, fetch history, clear history."""
from __future__ import annotations

import uuid

from fastapi import APIRouter, status

from app.presentation.deps import ChatServiceDep, CurrentUser
from app.presentation.schemas.chat import AskRequest, ChatMessageResponse

router = APIRouter(prefix="/repositories/{repo_id}/chat", tags=["chat"])


@router.post("", response_model=ChatMessageResponse)
async def ask_question(
    repo_id: uuid.UUID,
    payload: AskRequest,
    service: ChatServiceDep,
    user: CurrentUser,
) -> ChatMessageResponse:
    answer = await service.ask(user_id=user.id, repo_id=repo_id, question=payload.question)
    return ChatMessageResponse.model_validate(answer)


@router.get("", response_model=list[ChatMessageResponse])
async def get_history(
    repo_id: uuid.UUID,
    service: ChatServiceDep,
    user: CurrentUser,
) -> list[ChatMessageResponse]:
    messages = await service.history(user_id=user.id, repo_id=repo_id)
    return [ChatMessageResponse.model_validate(m) for m in messages]


@router.delete("", status_code=status.HTTP_204_NO_CONTENT)
async def clear_history(
    repo_id: uuid.UUID,
    service: ChatServiceDep,
    user: CurrentUser,
) -> None:
    await service.clear(user_id=user.id, repo_id=repo_id)
