"""Inventario: alertas de stock bajo + resumen + listado de movimientos."""
from fastapi.testclient import TestClient


def _producto(client, headers, sucursal_id, *, nombre, stock, stock_minimo=10, precio=1000):
    return client.post(
        "/api/productos",
        json={
            "nombre":        nombre,
            "precio":        precio,
            "categoria":     "General",
            "sucursal_id":   sucursal_id,
            "stock":         stock,
            "stock_minimo":  stock_minimo,
            "unidad_medida": "unidad",
        },
        headers=headers,
    ).json()


def test_alertas_stock_bajo_clasifica_severidad(
    client: TestClient, tenant_owner, auth_headers_owner
):
    sid = tenant_owner["sucursal"].id
    _producto(client, auth_headers_owner, sid, nombre="OK",        stock=100, stock_minimo=10)
    _producto(client, auth_headers_owner, sid, nombre="Warning",   stock=15,  stock_minimo=10)
    _producto(client, auth_headers_owner, sid, nombre="Critical",  stock=8,   stock_minimo=10)
    _producto(client, auth_headers_owner, sid, nombre="Agotado",   stock=0,   stock_minimo=10)

    r = client.get("/api/inventario/alertas/stock-bajo", headers=auth_headers_owner)
    assert r.status_code == 200
    alertas = r.json()
    nombres_severidad = {a["producto_nombre"]: a["severidad"] for a in alertas}

    assert "OK" not in nombres_severidad
    assert nombres_severidad["Warning"]  == "warning"
    assert nombres_severidad["Critical"] == "critical"
    assert nombres_severidad["Agotado"]  == "agotado"

    # Orden: agotado → critical → warning
    severidades_orden = [a["severidad"] for a in alertas]
    assert severidades_orden == ["agotado", "critical", "warning"]


def test_alertas_filtran_por_sucursal(
    client: TestClient, tenant_owner, auth_headers_owner, db_session
):
    sid_a = tenant_owner["sucursal"].id
    # Crear segunda sucursal
    from backend.models.orm import Sucursal
    suc_b = Sucursal(tenant_id=tenant_owner["tenant"].id, nombre="Norte")
    db_session.add(suc_b)
    db_session.commit()
    db_session.refresh(suc_b)

    _producto(client, auth_headers_owner, sid_a, nombre="Bajo A", stock=2,  stock_minimo=10)
    _producto(client, auth_headers_owner, suc_b.id, nombre="Bajo B", stock=2, stock_minimo=10)

    r_a = client.get(f"/api/inventario/alertas/stock-bajo?sucursal_id={sid_a}",
                     headers=auth_headers_owner).json()
    nombres_a = {a["producto_nombre"] for a in r_a}
    assert nombres_a == {"Bajo A"}


def test_resumen_inventario_calcula_kpis(
    client: TestClient, tenant_owner, auth_headers_owner
):
    sid = tenant_owner["sucursal"].id
    _producto(client, auth_headers_owner, sid, nombre="P1", stock=10, stock_minimo=5,  precio=1000)
    _producto(client, auth_headers_owner, sid, nombre="P2", stock=2,  stock_minimo=5,  precio=2000)
    _producto(client, auth_headers_owner, sid, nombre="P3", stock=0,  stock_minimo=5,  precio=500)

    r = client.get("/api/inventario/resumen", headers=auth_headers_owner)
    assert r.status_code == 200
    body = r.json()

    assert body["total_productos"]    == 3
    assert body["total_unidades"]     == 12.0
    assert body["valor_inventario"]   == 10*1000 + 2*2000 + 0*500
    assert body["productos_agotados"] == 1
    assert body["productos_criticos"] == 1   # P2 (2 <= 5)
    # P1: stock=10, minimo=5 → 10 > 5*2=10? no, 10 == 10, así que está en warning (10 <= 10)
    assert body["productos_warning"] == 1


def test_movimientos_filtran_por_tipo(
    client: TestClient, tenant_owner, auth_headers_owner
):
    sid = tenant_owner["sucursal"].id
    p = _producto(client, auth_headers_owner, sid, nombre="P", stock=20)
    # Genera movimiento de tipo="ajuste"
    client.post(
        f"/api/productos/{p['id']}/ajuste-stock",
        json={"tipo": "ajuste", "cantidad": 1, "stock_final": 30, "motivo": "Recuento"},
        headers=auth_headers_owner,
    )

    todos = client.get("/api/inventario/movimientos", headers=auth_headers_owner).json()
    assert len(todos) == 2  # entrada inicial + ajuste

    solo_ajuste = client.get(
        "/api/inventario/movimientos?tipo=ajuste", headers=auth_headers_owner
    ).json()
    assert len(solo_ajuste) == 1
    assert solo_ajuste[0]["tipo"] == "ajuste"
