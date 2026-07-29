"""Smoke tests for the API."""
from fastapi.testclient import TestClient


def test_health_endpoint(client: TestClient):
    r = client.get("/api/health")
    assert r.status_code == 200
    body = r.json()
    assert body["status"] == "ok"
    assert body["service"] == "orion"


def test_openapi_schema_exposes_routers(client: TestClient):
    r = client.get("/openapi.json")
    assert r.status_code == 200
    paths = r.json()["paths"]
    expected_prefixes = [
        "/api/v3/auth",
        "/api/productos",
        "/api/categorias",
        "/api/ordenes",
        "/api/reportes",
        "/api/inventario",
        "/api/admin",
        "/api/sucursales",
        "/api/v3/usuarios",
        "/api/v3/branding",
        "/api/v3/onboarding",
    ]
    for prefix in expected_prefixes:
        assert any(
            p.startswith(prefix) for p in paths
        ), f"No path starts with {prefix} (got: {sorted(paths)[:8]}...)"
