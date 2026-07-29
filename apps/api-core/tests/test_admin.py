"""Admin: panel super-admin (login propio + gestión de tenants)."""
from fastapi.testclient import TestClient


def test_admin_login_succeeds(client: TestClient, tenant_admin):
    r = client.post(
        "/api/admin/login",
        json={"email": tenant_admin["tenant"].email, "password": "secret123"},
    )
    assert r.status_code == 200
    assert r.json()["access_token"]


def test_admin_login_rechaza_no_admin(client: TestClient, tenant_owner):
    r = client.post(
        "/api/admin/login",
        json={"email": tenant_owner["tenant"].email, "password": "secret123"},
    )
    assert r.status_code == 403


def test_admin_lista_todos_los_tenants(client: TestClient, admin_headers, tenant_factory):
    tenant_factory(email="cliente1@test.com")
    tenant_factory(email="cliente2@test.com")

    r = client.get("/api/admin/tenants", headers=admin_headers)
    assert r.status_code == 200
    emails = [t["email"] for t in r.json()]
    # admin + 2 tenants creados
    assert "cliente1@test.com" in emails
    assert "cliente2@test.com" in emails


def test_admin_puede_suspender_tenant(
    client: TestClient, admin_headers, tenant_factory
):
    cliente = tenant_factory(email="suspender@test.com")
    r = client.patch(
        f"/api/admin/tenants/{cliente['tenant'].id}",
        json={"plan_activo": False},
        headers=admin_headers,
    )
    assert r.status_code == 200
    assert r.json()["plan_activo"] is False

    # Login del cliente suspendido debe dar 402
    r2 = client.post(
        "/api/v3/auth/login",
        json={"email": "suspender@test.com", "password": "secret123"},
    )
    assert r2.status_code == 402


def test_admin_no_puede_eliminarse_a_si_mismo(
    client: TestClient, admin_headers, tenant_admin
):
    r = client.delete(
        f"/api/admin/tenants/{tenant_admin['tenant'].id}", headers=admin_headers
    )
    assert r.status_code == 403


def test_admin_puede_eliminar_tenant_normal(
    client: TestClient, admin_headers, tenant_factory
):
    cliente = tenant_factory(email="eliminar@test.com")
    r = client.delete(
        f"/api/admin/tenants/{cliente['tenant'].id}", headers=admin_headers
    )
    assert r.status_code == 200
    assert "eliminado" in r.json()["message"].lower()


def test_endpoints_admin_rechazan_no_admin(
    client: TestClient, auth_headers_owner
):
    r = client.get("/api/admin/tenants", headers=auth_headers_owner)
    assert r.status_code == 403
