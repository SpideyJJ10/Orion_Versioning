"""Usuarios: jerarquía de roles y aislamiento por tenant."""
from fastapi.testclient import TestClient


def test_owner_puede_crear_manager(client: TestClient, tenant_owner, auth_headers_owner):
    sid = tenant_owner["sucursal"].id
    r = client.post(
        "/api/v3/usuarios",
        json={
            "email":       "manager@test.com",
            "password":    "secret123",
            "nombre":      "Gerente",
            "rol":         "manager",
            "sucursal_id": sid,
        },
        headers=auth_headers_owner,
    )
    assert r.status_code == 201, r.text
    assert r.json()["rol"] == "manager"


def test_manager_no_puede_crear_otro_manager(
    client: TestClient, tenant_owner, db_session, make_auth_headers
):
    sid = tenant_owner["sucursal"].id
    # Creamos un manager en BD directamente
    from backend.auth_v3.passwords import hash_password
    from backend.models.orm import Usuario
    manager = Usuario(
        tenant_id=tenant_owner["tenant"].id,
        email="manager1@test.com",
        password_hash=hash_password("xx"),
        nombre="M1",
        rol="manager",
        sucursal_id=sid,
        activo=True,
    )
    db_session.add(manager)
    db_session.commit()
    db_session.refresh(manager)

    headers = make_auth_headers(manager)
    r = client.post(
        "/api/v3/usuarios",
        json={
            "email":       "manager2@test.com",
            "password":    "secret123",
            "nombre":      "M2",
            "rol":         "manager",
            "sucursal_id": sid,
        },
        headers=headers,
    )
    assert r.status_code == 403


def test_manager_puede_crear_cajero_con_pin(
    client: TestClient, tenant_owner, db_session, make_auth_headers
):
    sid = tenant_owner["sucursal"].id
    from backend.auth_v3.passwords import hash_password
    from backend.models.orm import Usuario
    manager = Usuario(
        tenant_id=tenant_owner["tenant"].id,
        email="m@test.com",
        password_hash=hash_password("xx"),
        nombre="M",
        rol="manager",
        sucursal_id=sid,
        activo=True,
    )
    db_session.add(manager)
    db_session.commit()
    db_session.refresh(manager)

    headers = make_auth_headers(manager)
    r = client.post(
        "/api/v3/usuarios",
        json={
            "email":       "cajero@test.com",
            "password":    "secret123",
            "nombre":      "Cajero",
            "rol":         "cajero",
            "sucursal_id": sid,
            "pin":         "1234",
        },
        headers=headers,
    )
    assert r.status_code == 201
    assert r.json()["rol"] == "cajero"


def test_cajero_no_puede_listar_usuarios(
    client: TestClient, tenant_owner, db_session, make_auth_headers
):
    from backend.auth_v3.passwords import hash_password
    from backend.models.orm import Usuario
    cajero = Usuario(
        tenant_id=tenant_owner["tenant"].id,
        email="c@test.com",
        password_hash=hash_password("xx"),
        nombre="C",
        rol="cajero",
        sucursal_id=tenant_owner["sucursal"].id,
        activo=True,
    )
    db_session.add(cajero)
    db_session.commit()
    db_session.refresh(cajero)

    r = client.get("/api/v3/usuarios", headers=make_auth_headers(cajero))
    assert r.status_code == 403


def test_pin_duplicado_es_rechazado(
    client: TestClient, tenant_owner, auth_headers_owner
):
    sid = tenant_owner["sucursal"].id
    payload = {
        "email":       "c1@test.com",
        "password":    "secret123",
        "nombre":      "C1",
        "rol":         "cajero",
        "sucursal_id": sid,
        "pin":         "9876",
    }
    r1 = client.post("/api/v3/usuarios", json=payload, headers=auth_headers_owner)
    assert r1.status_code == 201

    payload["email"] = "c2@test.com"
    payload["nombre"] = "C2"
    r2 = client.post("/api/v3/usuarios", json=payload, headers=auth_headers_owner)
    assert r2.status_code == 409


def test_owner_no_puede_desactivarse_a_si_mismo(
    client: TestClient, tenant_owner, auth_headers_owner
):
    owner_id = tenant_owner["owner"].id
    r = client.delete(f"/api/v3/usuarios/{owner_id}", headers=auth_headers_owner)
    assert r.status_code == 400
