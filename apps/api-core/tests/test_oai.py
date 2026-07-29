"""
Tests para Orion IA (OIA) routes: templates, chat y provision.
"""
from fastapi.testclient import TestClient


def test_oai_templates_list(client: TestClient):
    r = client.get("/api/oai/templates")
    assert r.status_code == 200
    data = r.json()
    assert isinstance(data, list)
    assert len(data) >= 4
    keys = [item["key"] for item in data]
    assert "restaurante" in keys
    assert "barberia" in keys
    assert "farmacia" in keys
    assert "retail" in keys


def test_oai_chat_fallback(client: TestClient):
    r = client.post(
        "/api/oai/chat",
        json={
            "message": "Hola, tengo una hamburguesería llamada Burger Star",
            "history": [],
        },
    )
    assert r.status_code == 200
    data = r.json()
    assert "reply" in data
    assert "extracted" in data
    assert "session_id" in data
    assert isinstance(data["ready_to_provision"], bool)


def test_oai_provision_flow(client: TestClient):
    email = "oai_owner@burgerstar.com"
    r = client.post(
        "/api/oai/provision",
        json={
            "nombre_negocio": "Burger Star",
            "tipo_negocio": "restaurante",
            "email": email,
            "password": "Password123!",
            "num_mesas": 8,
            "num_empleados": 4,
        },
    )
    assert r.status_code == 201, r.text
    data = r.json()
    assert "access_token" in data
    assert "refresh_token" in data
    assert "tenant_id" in data
    assert "sucursal_id" in data
    assert data["app_url"] == "/dashboard"
    assert len(data["setup_checklist"]) > 0
    assert data["branding"]["nicho"] == "restaurante"

    # Intentar registrar el mismo email debe ser rechazado
    r_dup = client.post(
        "/api/oai/provision",
        json={
            "nombre_negocio": "Burger Star 2",
            "tipo_negocio": "restaurante",
            "email": email,
            "password": "Password123!",
        },
    )
    assert r_dup.status_code == 409
