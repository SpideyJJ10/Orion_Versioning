"""Productos: CRUD + stock + ledger de movimientos + tenant isolation."""
from fastapi.testclient import TestClient


def _producto_payload(sucursal_id: str, **overrides) -> dict:
    base = {
        "nombre":        "Hamburguesa",
        "precio":        15000.0,
        "categoria":     "Platos fuertes",
        "sucursal_id":   sucursal_id,
        "stock":         50.0,
        "stock_minimo":  10.0,
        "unidad_medida": "unidad",
    }
    base.update(overrides)
    return base


def test_crear_producto_con_stock_inicial_genera_movimiento(
    client: TestClient, tenant_owner, auth_headers_owner, db_session
):
    sid = tenant_owner["sucursal"].id
    r = client.post("/api/productos", json=_producto_payload(sid), headers=auth_headers_owner)
    assert r.status_code == 201, r.text
    body = r.json()
    assert body["stock"] == 50.0
    assert body["stock_minimo"] == 10.0
    assert body["unidad_medida"] == "unidad"

    # Ledger: 1 movimiento de entrada con cantidad=50, stock_antes=0
    from backend.models.orm import MovimientoInventario
    mov = db_session.query(MovimientoInventario).filter_by(
        producto_id=body["id"]
    ).all()
    assert len(mov) == 1
    assert mov[0].tipo == "entrada"
    assert mov[0].cantidad == 50.0
    assert mov[0].stock_antes == 0.0
    assert mov[0].stock_despues == 50.0
    assert mov[0].motivo == "Stock inicial al crear producto"


def test_crear_producto_sin_stock_no_genera_movimiento(
    client: TestClient, tenant_owner, auth_headers_owner, db_session
):
    sid = tenant_owner["sucursal"].id
    r = client.post(
        "/api/productos",
        json=_producto_payload(sid, stock=0),
        headers=auth_headers_owner,
    )
    assert r.status_code == 201
    from backend.models.orm import MovimientoInventario
    assert db_session.query(MovimientoInventario).count() == 0


def test_crear_producto_rechaza_unidad_invalida(
    client: TestClient, tenant_owner, auth_headers_owner
):
    sid = tenant_owner["sucursal"].id
    r = client.post(
        "/api/productos",
        json=_producto_payload(sid, unidad_medida="parsec"),
        headers=auth_headers_owner,
    )
    assert r.status_code == 422


def test_listar_productos_filtra_por_sucursal(
    client: TestClient, tenant_owner, auth_headers_owner
):
    sid = tenant_owner["sucursal"].id
    client.post("/api/productos", json=_producto_payload(sid), headers=auth_headers_owner)

    r = client.get(f"/api/productos?sucursal_id={sid}", headers=auth_headers_owner)
    assert r.status_code == 200
    assert len(r.json()) == 1


def test_listar_productos_sin_sucursal_devuelve_vacio(
    client: TestClient, auth_headers_owner
):
    r = client.get("/api/productos", headers=auth_headers_owner)
    assert r.status_code == 200
    assert r.json() == []


def test_editar_producto_permite_stock_minimo_pero_no_stock(
    client: TestClient, tenant_owner, auth_headers_owner, db_session
):
    sid = tenant_owner["sucursal"].id
    created = client.post(
        "/api/productos", json=_producto_payload(sid), headers=auth_headers_owner
    ).json()

    # Cambiar stock_minimo via PUT debe funcionar
    r = client.put(
        f"/api/productos/{created['id']}",
        json={"stock_minimo": 25.0, "precio": 16000.0},
        headers=auth_headers_owner,
    )
    assert r.status_code == 200
    assert r.json()["stock_minimo"] == 25.0
    assert r.json()["precio"] == 16000.0
    # stock se mantiene (no se modifica vía PUT)
    assert r.json()["stock"] == 50.0


def test_ajuste_stock_entrada_aumenta_y_registra_ledger(
    client: TestClient, tenant_owner, auth_headers_owner
):
    sid = tenant_owner["sucursal"].id
    p = client.post(
        "/api/productos",
        json=_producto_payload(sid, stock=20),
        headers=auth_headers_owner,
    ).json()

    r = client.post(
        f"/api/productos/{p['id']}/ajuste-stock",
        json={"tipo": "entrada", "cantidad": 30, "motivo": "Compra a proveedor"},
        headers=auth_headers_owner,
    )
    assert r.status_code == 200
    assert r.json()["stock"] == 50.0

    movs = client.get(
        f"/api/productos/{p['id']}/movimientos", headers=auth_headers_owner
    ).json()
    # 2 movimientos: entrada inicial + entrada manual
    assert len(movs) == 2
    assert movs[0]["tipo"] == "entrada"  # ordenado por fecha desc
    assert movs[0]["cantidad"] == 30.0
    assert movs[0]["motivo"] == "Compra a proveedor"


def test_ajuste_stock_salida_disminuye(
    client: TestClient, tenant_owner, auth_headers_owner
):
    sid = tenant_owner["sucursal"].id
    p = client.post(
        "/api/productos",
        json=_producto_payload(sid, stock=10),
        headers=auth_headers_owner,
    ).json()

    r = client.post(
        f"/api/productos/{p['id']}/ajuste-stock",
        json={"tipo": "merma", "cantidad": 3},
        headers=auth_headers_owner,
    )
    assert r.status_code == 200
    assert r.json()["stock"] == 7.0


def test_ajuste_stock_no_permite_negativo(
    client: TestClient, tenant_owner, auth_headers_owner
):
    sid = tenant_owner["sucursal"].id
    p = client.post(
        "/api/productos",
        json=_producto_payload(sid, stock=5),
        headers=auth_headers_owner,
    ).json()
    r = client.post(
        f"/api/productos/{p['id']}/ajuste-stock",
        json={"tipo": "salida", "cantidad": 100},
        headers=auth_headers_owner,
    )
    assert r.status_code == 422


def test_ajuste_tipo_ajuste_fija_stock_final(
    client: TestClient, tenant_owner, auth_headers_owner
):
    sid = tenant_owner["sucursal"].id
    p = client.post(
        "/api/productos",
        json=_producto_payload(sid, stock=10),
        headers=auth_headers_owner,
    ).json()
    r = client.post(
        f"/api/productos/{p['id']}/ajuste-stock",
        json={"tipo": "ajuste", "cantidad": 1, "stock_final": 42, "motivo": "Conteo físico"},
        headers=auth_headers_owner,
    )
    assert r.status_code == 200
    assert r.json()["stock"] == 42.0


def test_eliminar_producto_es_soft_delete(
    client: TestClient, tenant_owner, auth_headers_owner
):
    sid = tenant_owner["sucursal"].id
    p = client.post(
        "/api/productos", json=_producto_payload(sid), headers=auth_headers_owner
    ).json()
    r = client.delete(f"/api/productos/{p['id']}", headers=auth_headers_owner)
    assert r.status_code == 204

    # Después de soft-delete no aparece en el listado
    listado = client.get(f"/api/productos?sucursal_id={sid}", headers=auth_headers_owner).json()
    assert all(prod["id"] != p["id"] for prod in listado)


def test_tenants_no_ven_productos_de_otros(
    client: TestClient, tenant_factory, make_auth_headers
):
    a = tenant_factory(email="a@test.com")
    b = tenant_factory(email="b@test.com")
    headers_a = make_auth_headers(a["owner"])
    headers_b = make_auth_headers(b["owner"])

    sid_a = a["sucursal"].id
    sid_b = b["sucursal"].id

    client.post("/api/productos", json=_producto_payload(sid_a, nombre="Solo A"), headers=headers_a)
    client.post("/api/productos", json=_producto_payload(sid_b, nombre="Solo B"), headers=headers_b)

    productos_a = client.get(f"/api/productos?sucursal_id={sid_a}", headers=headers_a).json()
    productos_b = client.get(f"/api/productos?sucursal_id={sid_b}", headers=headers_b).json()

    assert len(productos_a) == 1
    assert productos_a[0]["nombre"] == "Solo A"
    assert len(productos_b) == 1
    assert productos_b[0]["nombre"] == "Solo B"

    # Tenant A intentando leer la sucursal de B → 404 (sucursal no le pertenece)
    r = client.get(f"/api/productos?sucursal_id={sid_b}", headers=headers_a)
    assert r.status_code == 404
