"""API-level tests for auth that do not require a database.

Covers routing, validation, auth-error handling, and the RFC7807 response shape.
Full register/login/me persistence is exercised by the docker-compose stack and
DB-backed integration tests.
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


def test_me_without_token_is_unauthorized(client: TestClient) -> None:
    resp = client.get("/api/v1/auth/me")
    assert resp.status_code == 401
    body = resp.json()
    assert body["title"] == "authentication_error"
    assert "request_id" in body


def test_register_rejects_invalid_email_and_weak_password(client: TestClient) -> None:
    resp = client.post("/api/v1/auth/register", json={"email": "bad", "password": "short"})
    assert resp.status_code == 422
    assert resp.json()["title"] == "validation_error"


def test_register_rejects_password_without_number(client: TestClient) -> None:
    resp = client.post(
        "/api/v1/auth/register",
        json={"email": "user@example.com", "password": "onlyletters"},
    )
    assert resp.status_code == 422


def test_refresh_without_cookie_is_unauthorized(client: TestClient) -> None:
    resp = client.post("/api/v1/auth/refresh")
    assert resp.status_code == 401
    assert resp.json()["title"] == "authentication_error"


def test_login_validation_requires_fields(client: TestClient) -> None:
    resp = client.post("/api/v1/auth/login", json={"email": "user@example.com"})
    assert resp.status_code == 422


def test_openapi_exposes_all_auth_routes(client: TestClient) -> None:
    paths = client.get("/openapi.json").json()["paths"]
    for route in ("register", "login", "refresh", "logout", "me"):
        assert f"/api/v1/auth/{route}" in paths
