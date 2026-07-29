"""Onboarding: GET, PATCH, POST /skip."""
from fastapi.testclient import TestClient


def test_get_onboarding_devuelve_progreso_inicial(
    client: TestClient, auth_headers_owner
):
    r = client.get("/api/v3/onboarding", headers=auth_headers_owner)
    assert r.status_code == 200
    body = r.json()
    assert body["perfil_configurado"] is False
    assert body["primer_producto"] is False
    assert body["primera_venta"] is False
    assert body["porcentaje"] == 0
    assert body["completado"] is False


def test_patch_onboarding_marca_paso(
    client: TestClient, auth_headers_owner
):
    r = client.patch("/api/v3/onboarding/perfil", headers=auth_headers_owner)
    assert r.status_code == 200
    body = r.json()
    assert body["perfil_configurado"] is True
    assert body["porcentaje"] == 33  # 1/3 redondeado


def test_patch_onboarding_completar_todo_genera_completado(
    client: TestClient, auth_headers_owner
):
    for paso in ("perfil", "producto", "venta"):
        client.patch(f"/api/v3/onboarding/{paso}", headers=auth_headers_owner)
    r = client.get("/api/v3/onboarding", headers=auth_headers_owner)
    assert r.json()["porcentaje"] == 100
    assert r.json()["completado"] is True


def test_patch_onboarding_paso_invalido(
    client: TestClient, auth_headers_owner
):
    r = client.patch("/api/v3/onboarding/inventarios", headers=auth_headers_owner)
    assert r.status_code == 400


def test_skip_onboarding(client: TestClient, auth_headers_owner):
    r = client.post("/api/v3/onboarding/skip", headers=auth_headers_owner)
    assert r.status_code == 200
    assert r.json()["saltado"] is True
