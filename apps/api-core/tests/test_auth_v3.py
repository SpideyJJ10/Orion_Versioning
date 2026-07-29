"""Auth v3 — registro, login, refresh, /me, login-pin, plan suspendido."""
from fastapi.testclient import TestClient


REGISTER_PAYLOAD = {
    "email":              "negocio@test.com",
    "password":           "secret1234",
    "nombre_comercial":   "Asadero El Tizón",
    "nombre_propietario": "Juan Pérez",
    "telefono":           "3001234567",
    "nicho":              "restaurante",
}


def test_register_creates_full_tenant(client: TestClient):
    r = client.post("/api/v3/auth/register", json=REGISTER_PAYLOAD)
    assert r.status_code == 201, r.text
    body = r.json()
    assert body["token_type"] == "bearer"
    assert body["expires_in"] > 0
    assert body["access_token"]
    assert body["refresh_token"]
    assert body["usuario"]["email"] == "negocio@test.com"
    assert body["usuario"]["rol"] == "owner"
    assert body["usuario"]["sucursal_id"] is not None  # default "Principal"


def test_register_rejects_duplicate_email(client: TestClient):
    client.post("/api/v3/auth/register", json=REGISTER_PAYLOAD)
    r = client.post("/api/v3/auth/register", json=REGISTER_PAYLOAD)
    assert r.status_code == 409


def test_register_rejects_short_password(client: TestClient):
    payload = {**REGISTER_PAYLOAD, "password": "short"}
    r = client.post("/api/v3/auth/register", json=payload)
    assert r.status_code == 422


def test_login_succeeds_after_register(client: TestClient):
    client.post("/api/v3/auth/register", json=REGISTER_PAYLOAD)
    r = client.post("/api/v3/auth/login", json={
        "email":    REGISTER_PAYLOAD["email"],
        "password": REGISTER_PAYLOAD["password"],
    })
    assert r.status_code == 200, r.text
    assert r.json()["usuario"]["rol"] == "owner"


def test_login_rejects_wrong_password(client: TestClient):
    client.post("/api/v3/auth/register", json=REGISTER_PAYLOAD)
    r = client.post("/api/v3/auth/login", json={
        "email":    REGISTER_PAYLOAD["email"],
        "password": "wrong-password",
    })
    assert r.status_code == 401


def test_login_normalizes_email_to_lowercase(client: TestClient):
    client.post("/api/v3/auth/register", json=REGISTER_PAYLOAD)
    r = client.post("/api/v3/auth/login", json={
        "email":    REGISTER_PAYLOAD["email"].upper(),
        "password": REGISTER_PAYLOAD["password"],
    })
    assert r.status_code == 200


def test_me_returns_authenticated_user(client: TestClient):
    reg = client.post("/api/v3/auth/register", json=REGISTER_PAYLOAD).json()
    token = reg["access_token"]
    r = client.get("/api/v3/auth/me", headers={"Authorization": f"Bearer {token}"})
    assert r.status_code == 200
    assert r.json()["email"] == REGISTER_PAYLOAD["email"]


def test_me_rejects_missing_token(client: TestClient):
    r = client.get("/api/v3/auth/me")
    assert r.status_code == 401


def test_me_rejects_invalid_token(client: TestClient):
    r = client.get("/api/v3/auth/me", headers={"Authorization": "Bearer notajwt"})
    assert r.status_code == 401


def test_refresh_returns_new_pair(client: TestClient):
    reg = client.post("/api/v3/auth/register", json=REGISTER_PAYLOAD).json()
    refresh = reg["refresh_token"]

    r = client.post("/api/v3/auth/refresh", json={"refresh_token": refresh})
    assert r.status_code == 200, r.text
    body = r.json()
    assert body["access_token"]
    assert body["refresh_token"]


def test_refresh_rejects_reused_refresh_token(client: TestClient):
    reg = client.post("/api/v3/auth/register", json=REGISTER_PAYLOAD).json()
    refresh = reg["refresh_token"]

    first = client.post("/api/v3/auth/refresh", json={"refresh_token": refresh})
    assert first.status_code == 200, first.text

    reused = client.post("/api/v3/auth/refresh", json={"refresh_token": refresh})
    assert reused.status_code == 401


def test_refresh_rejects_access_token_passed_as_refresh(client: TestClient):
    reg = client.post("/api/v3/auth/register", json=REGISTER_PAYLOAD).json()
    r = client.post("/api/v3/auth/refresh", json={"refresh_token": reg["access_token"]})
    assert r.status_code == 401


def test_login_with_suspended_plan_returns_402(client: TestClient, db_session, tenant_factory):
    tenant_factory(email="suspendido@test.com", plan_activo=False)
    r = client.post("/api/v3/auth/login", json={
        "email": "suspendido@test.com",
        "password": "secret123",
    })
    assert r.status_code == 402


def test_login_pin_succeeds(client: TestClient, db_session, tenant_owner):
    # Add a cajero with PIN
    from backend.models.orm import Usuario
    cajero = Usuario(
        tenant_id     = tenant_owner["tenant"].id,
        email         = "caja@test.com",
        password_hash = "n/a",
        nombre        = "Cajero 1",
        rol           = "cajero",
        sucursal_id   = tenant_owner["sucursal"].id,
        pin           = "1234",
        activo        = True,
    )
    db_session.add(cajero)
    db_session.commit()

    r = client.post("/api/v3/auth/login-pin", json={
        "tenant_id": tenant_owner["tenant"].id,
        "pin":       "1234",
    })
    assert r.status_code == 200, r.text
    assert r.json()["usuario"]["rol"] == "cajero"


def test_login_pin_rejects_wrong_pin(client: TestClient, tenant_owner):
    r = client.post("/api/v3/auth/login-pin", json={
        "tenant_id": tenant_owner["tenant"].id,
        "pin":       "0000",
    })
    assert r.status_code == 401
