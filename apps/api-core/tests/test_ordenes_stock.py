"""Órdenes: creación atómica + descuento de stock + anulación restaura stock."""
from fastapi.testclient import TestClient


def _crear_producto(client, headers, sucursal_id, *, nombre="Hamburguesa", stock=20, precio=10000):
    return client.post(
        "/api/productos",
        json={
            "nombre":        nombre,
            "precio":        precio,
            "categoria":     "General",
            "sucursal_id":   sucursal_id,
            "stock":         stock,
            "stock_minimo":  5,
            "unidad_medida": "unidad",
        },
        headers=headers,
    ).json()


def test_crear_orden_descuenta_stock_y_genera_movimiento(
    client: TestClient, tenant_owner, auth_headers_owner, db_session
):
    sid = tenant_owner["sucursal"].id
    p = _crear_producto(client, auth_headers_owner, sid, stock=10)

    r = client.post(
        "/api/ordenes",
        json={
            "sucursal_id": sid,
            "metodo_pago": "Efectivo",
            "domicilio":   0,
            "items":       [{"producto_id": p["id"], "cantidad": 3}],
        },
        headers=auth_headers_owner,
    )
    assert r.status_code == 201, r.text
    body = r.json()
    assert body["subtotal"] == 30000.0
    assert body["total"] == 30000.0

    # Stock descontado
    db_session.expire_all()
    listado = client.get(f"/api/productos?sucursal_id={sid}", headers=auth_headers_owner).json()
    assert listado[0]["stock"] == 7.0

    # Movimiento tipo='venta' creado
    from backend.models.orm import MovimientoInventario
    movs = db_session.query(MovimientoInventario).filter_by(
        producto_id=p["id"], tipo="venta"
    ).all()
    assert len(movs) == 1
    assert movs[0].cantidad == -3.0
    assert movs[0].stock_antes == 10.0
    assert movs[0].stock_despues == 7.0
    assert movs[0].referencia_id == body["id"]


def test_crear_orden_rechaza_si_stock_insuficiente(
    client: TestClient, tenant_owner, auth_headers_owner
):
    sid = tenant_owner["sucursal"].id
    p = _crear_producto(client, auth_headers_owner, sid, stock=2)

    r = client.post(
        "/api/ordenes",
        json={
            "sucursal_id": sid,
            "metodo_pago": "Efectivo",
            "items":       [{"producto_id": p["id"], "cantidad": 5}],
        },
        headers=auth_headers_owner,
    )
    assert r.status_code == 409
    assert "Stock insuficiente" in r.json()["detail"]


def test_crear_orden_es_atomica_si_un_item_falla(
    client: TestClient, tenant_owner, auth_headers_owner, db_session
):
    sid = tenant_owner["sucursal"].id
    p1 = _crear_producto(client, auth_headers_owner, sid, nombre="A", stock=10)
    p2 = _crear_producto(client, auth_headers_owner, sid, nombre="B", stock=1)

    # Esta orden debe fallar por p2: ningún item debe descontar stock
    r = client.post(
        "/api/ordenes",
        json={
            "sucursal_id": sid,
            "metodo_pago": "Efectivo",
            "items": [
                {"producto_id": p1["id"], "cantidad": 3},
                {"producto_id": p2["id"], "cantidad": 5},  # falla aquí
            ],
        },
        headers=auth_headers_owner,
    )
    assert r.status_code == 409

    # Stock de p1 NO se debe haber tocado
    db_session.expire_all()
    productos = client.get(
        f"/api/productos?sucursal_id={sid}", headers=auth_headers_owner
    ).json()
    p1_after = next(p for p in productos if p["id"] == p1["id"])
    p2_after = next(p for p in productos if p["id"] == p2["id"])
    assert p1_after["stock"] == 10
    assert p2_after["stock"] == 1


def test_orden_con_item_manual_no_afecta_stock(
    client: TestClient, tenant_owner, auth_headers_owner
):
    sid = tenant_owner["sucursal"].id
    r = client.post(
        "/api/ordenes",
        json={
            "sucursal_id": sid,
            "metodo_pago": "Efectivo",
            "domicilio":   2000,
            "items":       [{
                "producto_id":     "__manual_domicilio",
                "producto_nombre": "Domicilio extra",
                "precio_unitario": 5000,
                "cantidad":        1,
            }],
        },
        headers=auth_headers_owner,
    )
    assert r.status_code == 201
    body = r.json()
    assert body["domicilio"] == 2000.0
    assert body["total"] == 7000.0


def test_anular_orden_restaura_stock(
    client: TestClient, tenant_owner, auth_headers_owner, db_session
):
    import os
    pin = os.environ["ADMIN_PIN"]
    sid = tenant_owner["sucursal"].id
    p = _crear_producto(client, auth_headers_owner, sid, stock=10)

    orden = client.post(
        "/api/ordenes",
        json={
            "sucursal_id": sid,
            "metodo_pago": "Efectivo",
            "items":       [{"producto_id": p["id"], "cantidad": 4}],
        },
        headers=auth_headers_owner,
    ).json()

    # Stock = 6 después de la venta
    r = client.delete(
        f"/api/ordenes/{orden['id']}?pin={pin}", headers=auth_headers_owner
    )
    assert r.status_code == 204

    db_session.expire_all()
    productos = client.get(
        f"/api/productos?sucursal_id={sid}", headers=auth_headers_owner
    ).json()
    assert productos[0]["stock"] == 10.0  # restaurado

    # Movimiento de devolución
    from backend.models.orm import MovimientoInventario
    devs = db_session.query(MovimientoInventario).filter_by(
        producto_id=p["id"], tipo="devolucion"
    ).all()
    assert len(devs) == 1
    assert devs[0].motivo == "Anulación de orden"
    assert devs[0].referencia_id == orden["id"]


def test_anular_orden_es_idempotente(
    client: TestClient, tenant_owner, auth_headers_owner, db_session
):
    import os
    pin = os.environ["ADMIN_PIN"]
    sid = tenant_owner["sucursal"].id
    p = _crear_producto(client, auth_headers_owner, sid, stock=10)

    orden = client.post(
        "/api/ordenes",
        json={
            "sucursal_id": sid,
            "metodo_pago": "Efectivo",
            "items":       [{"producto_id": p["id"], "cantidad": 4}],
        },
        headers=auth_headers_owner,
    ).json()

    # Anular dos veces
    client.delete(f"/api/ordenes/{orden['id']}?pin={pin}", headers=auth_headers_owner)
    client.delete(f"/api/ordenes/{orden['id']}?pin={pin}", headers=auth_headers_owner)

    # Solo debe haber UN movimiento de devolución
    from backend.models.orm import MovimientoInventario
    devs = db_session.query(MovimientoInventario).filter_by(
        producto_id=p["id"], tipo="devolucion"
    ).count()
    assert devs == 1
    db_session.expire_all()
    productos = client.get(
        f"/api/productos?sucursal_id={sid}", headers=auth_headers_owner
    ).json()
    assert productos[0]["stock"] == 10.0


def test_anular_orden_rechaza_pin_invalido(
    client: TestClient, tenant_owner, auth_headers_owner
):
    sid = tenant_owner["sucursal"].id
    p = _crear_producto(client, auth_headers_owner, sid, stock=10)
    orden = client.post(
        "/api/ordenes",
        json={
            "sucursal_id": sid,
            "metodo_pago": "Efectivo",
            "items":       [{"producto_id": p["id"], "cantidad": 1}],
        },
        headers=auth_headers_owner,
    ).json()

    r = client.delete(
        f"/api/ordenes/{orden['id']}?pin=000000", headers=auth_headers_owner
    )
    assert r.status_code == 403


def test_listar_ordenes_solo_devuelve_del_dia(
    client: TestClient, tenant_owner, auth_headers_owner
):
    sid = tenant_owner["sucursal"].id
    p = _crear_producto(client, auth_headers_owner, sid, stock=20)
    client.post(
        "/api/ordenes",
        json={
            "sucursal_id": sid,
            "metodo_pago": "Efectivo",
            "items":       [{"producto_id": p["id"], "cantidad": 1}],
        },
        headers=auth_headers_owner,
    )

    r = client.get(f"/api/ordenes?sucursal_id={sid}", headers=auth_headers_owner)
    assert r.status_code == 200
    assert len(r.json()) == 1
