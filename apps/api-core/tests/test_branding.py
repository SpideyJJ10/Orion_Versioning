"""Branding: GET/PUT por tenant + endpoint público."""
from fastapi.testclient import TestClient


def test_get_branding_devuelve_default_si_no_existe(
    client: TestClient, tenant_owner, auth_headers_owner, db_session
):
    # Borramos el branding creado en la fixture
    from backend.models.orm import TenantBranding
    db_session.query(TenantBranding).filter_by(tenant_id=tenant_owner["tenant"].id).delete()
    db_session.commit()

    r = client.get("/api/v3/branding", headers=auth_headers_owner)
    assert r.status_code == 200
    body = r.json()
    assert body["color_primary"] == "#8b5cf6"
    assert body["tema"] == "dark"
    assert body["tenant_id"] == tenant_owner["tenant"].id


def test_put_branding_actualiza_solo_campos_enviados(
    client: TestClient, auth_headers_owner
):
    r = client.put(
        "/api/v3/branding",
        json={"color_primary": "#ff6b00", "tema": "warm"},
        headers=auth_headers_owner,
    )
    assert r.status_code == 200, r.text
    assert r.json()["color_primary"] == "#ff6b00"
    assert r.json()["tema"] == "warm"
    # color_secondary se mantiene por default
    assert r.json()["color_secondary"] == "#0f172a"


def test_put_branding_rechaza_color_invalido(
    client: TestClient, auth_headers_owner
):
    r = client.put(
        "/api/v3/branding",
        json={"color_primary": "naranja"},
        headers=auth_headers_owner,
    )
    assert r.status_code == 422


def test_put_branding_rechaza_tema_invalido(
    client: TestClient, auth_headers_owner
):
    r = client.put(
        "/api/v3/branding",
        json={"tema": "psicodelico"},
        headers=auth_headers_owner,
    )
    assert r.status_code == 422


def test_branding_publico_accesible_sin_auth(
    client: TestClient, tenant_owner
):
    tid = tenant_owner["tenant"].id
    r = client.get(f"/api/v3/branding/public/{tid}")
    assert r.status_code == 200
    assert r.json()["tenant_id"] == tid


def test_branding_publico_404_para_tenant_inexistente(client: TestClient):
    r = client.get("/api/v3/branding/public/99999")
    assert r.status_code == 404
