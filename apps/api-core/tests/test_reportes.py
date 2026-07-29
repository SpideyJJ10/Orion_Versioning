"""Reportes diarios — agrega ventas legacy + órdenes."""
from fastapi.testclient import TestClient


def _crear_producto(client, headers, sucursal_id, *, nombre="P", stock=20, precio=1000):
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


def test_reporte_dia_sin_ordenes(
    client: TestClient, tenant_owner, auth_headers_owner
):
    sid = tenant_owner["sucursal"].id
    r = client.get(f"/api/reportes/dia?sucursal_id={sid}", headers=auth_headers_owner)
    assert r.status_code == 200
    body = r.json()
    assert body["productos"] == []
    assert body["resumen_caja"]["total_dia"] == 0


def test_reporte_dia_agrega_ordenes_efectivo_y_tarjeta(
    client: TestClient, tenant_owner, auth_headers_owner
):
    sid = tenant_owner["sucursal"].id
    p1 = _crear_producto(client, auth_headers_owner, sid, nombre="A", stock=20, precio=1000)
    p2 = _crear_producto(client, auth_headers_owner, sid, nombre="B", stock=20, precio=2500)

    # Orden 1: efectivo
    client.post(
        "/api/ordenes",
        json={
            "sucursal_id": sid,
            "metodo_pago": "Efectivo",
            "items": [{"producto_id": p1["id"], "cantidad": 3}],  # 3000
        },
        headers=auth_headers_owner,
    )
    # Orden 2: tarjeta
    client.post(
        "/api/ordenes",
        json={
            "sucursal_id": sid,
            "metodo_pago": "Tarjeta",
            "items": [{"producto_id": p2["id"], "cantidad": 2}],  # 5000
        },
        headers=auth_headers_owner,
    )

    r = client.get(f"/api/reportes/dia?sucursal_id={sid}", headers=auth_headers_owner)
    assert r.status_code == 200
    body = r.json()

    assert body["resumen_caja"]["efectivo"] == 3000.0
    assert body["resumen_caja"]["tarjeta"]  == 5000.0
    assert body["resumen_caja"]["total_dia"] == 8000.0

    # Productos ordenados por total descendente
    nombres = [p["producto_nombre"] for p in body["productos"]]
    assert nombres == ["B", "A"]
    assert body["productos"][0]["cantidad_total"] == 2
    assert body["productos"][0]["total_ingresos"] == 5000.0


def test_reporte_dia_excluye_ordenes_anuladas(
    client: TestClient, tenant_owner, auth_headers_owner
):
    import os
    pin = os.environ["ADMIN_PIN"]
    sid = tenant_owner["sucursal"].id
    p = _crear_producto(client, auth_headers_owner, sid, stock=10, precio=1000)

    orden = client.post(
        "/api/ordenes",
        json={
            "sucursal_id": sid,
            "metodo_pago": "Efectivo",
            "items": [{"producto_id": p["id"], "cantidad": 5}],
        },
        headers=auth_headers_owner,
    ).json()

    # Anular la orden
    client.delete(f"/api/ordenes/{orden['id']}?pin={pin}", headers=auth_headers_owner)

    r = client.get(f"/api/reportes/dia?sucursal_id={sid}", headers=auth_headers_owner)
    assert r.status_code == 200
    assert r.json()["resumen_caja"]["total_dia"] == 0
    assert r.json()["productos"] == []
