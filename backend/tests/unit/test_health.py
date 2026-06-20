"""Smoke tests for the application foundation."""
from __future__ import annotations

from fastapi.testclient import TestClient

from app.main import create_app


def test_health_endpoint_returns_ok() -> None:
    client = TestClient(create_app())
    resp = client.get("/api/v1/health")
    assert resp.status_code == 200
    assert resp.json() == {"status": "ok"}


def test_openapi_schema_is_served() -> None:
    client = TestClient(create_app())
    resp = client.get("/openapi.json")
    assert resp.status_code == 200
    assert resp.json()["info"]["title"]


def test_settings_load() -> None:
    from app.core.config import get_settings

    settings = get_settings()
    assert settings.jwt_algorithm == "HS256"
    assert settings.api_v1_prefix == "/api/v1"
