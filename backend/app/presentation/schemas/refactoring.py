"""Request/response schemas for the refactoring module."""
from __future__ import annotations

from pydantic import BaseModel, Field


class SuggestRefactorRequest(BaseModel):
    file_path: str = Field(min_length=1, max_length=500)


class RefactoringSuggestion(BaseModel):
    title: str
    category: str
    impact: str
    line: int
    rationale: str
    suggested_change: str


class RefactoringResponse(BaseModel):
    file_path: str
    summary: str
    suggestions: list[RefactoringSuggestion]
