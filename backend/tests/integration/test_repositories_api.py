"""API-level tests for the repositories module (no database required).

Verifies routing, auth enforcement, and OpenAPI exposure. Full lifecycle
(create → index → ready) is exercised by the docker-compose stack.
"""
from __future__ import annotations

import logging

import pytest
from fastapi.testclient import TestClient

from app.main import create_app


@pytest.fixture(scope="module")
def client() -> TestClient:
    logging.disable(logging.CRITICAL)
    return TestClient(create_app(), raise_server_exceptions=False)


def test_list_requires_auth(client: TestClient) -> None:
    assert client.get("/api/v1/repositories").status_code == 401


def test_create_requires_auth(client: TestClient) -> None:
    resp = client.post(
        "/api/v1/repositories", json={"github_url": "https://github.com/psf/requests"}
    )
    assert resp.status_code == 401


def test_delete_requires_auth(client: TestClient) -> None:
    assert (
        client.delete("/api/v1/repositories/00000000-0000-0000-0000-000000000000").status_code
        == 401
    )


def test_openapi_exposes_repository_routes(client: TestClient) -> None:
    paths = client.get("/openapi.json").json()["paths"]
    assert "/api/v1/repositories" in paths
    assert "/api/v1/repositories/upload" in paths
    assert "/api/v1/repositories/{repo_id}" in paths
    assert "/api/v1/repositories/{repo_id}/reindex" in paths
