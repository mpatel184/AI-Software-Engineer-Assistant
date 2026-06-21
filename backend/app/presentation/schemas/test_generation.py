"""Request/response schemas for the test-generation module."""
from __future__ import annotations

from pydantic import BaseModel, Field


class GenerateTestRequest(BaseModel):
    file_path: str = Field(min_length=1, max_length=500)


class RepoFilesResponse(BaseModel):
    files: list[str]


class GeneratedTestResponse(BaseModel):
    file_path: str
    framework: str
    test_file_path: str
    test_code: str
    notes: str
