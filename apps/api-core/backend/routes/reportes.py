"""
routes/reportes.py — Reportes y cierre de caja
Agrega datos de ventas legacy Y órdenes nuevas en un set unificado de KPIs.

Endpoints:
  GET /api/reportes/dia      → ReporteDia (legacy: caja por método + lista productos)
  GET /api/reportes/diario   → ReporteDiarioOut (consumido por el dashboard)
  GET /api/reportes/rango    → ReporteRangoOut (con serie diaria para gráficas)
"""
from datetime import datetime, timedelta, timezone
from typing import Optional

from fastapi import APIRouter, Depends, HTTPException, Query
from sqlalchemy import func
from sqlalchemy.orm import Session

from backend.auth_v3 import get_current_usuario as get_current_user
from backend.db.session import get_db
from backend.models.orm import Orden, OrdenItem, Sucursal, Venta
from backend.schemas import (
    ReporteDia,
    ReporteDiarioOut,
    ReporteProducto,
    ReporteRangoOut,
    ResumenCaja,
    TopProducto,
)

router = APIRouter(prefix="/api/reportes", tags=["Reportes"])


# ====================================================================
# Helpers
# ====================================================================
def _verificar_sucursal(sucursal_id: str, tenant_id: int, db: Session) -> Sucursal:
    s = db.query(Sucursal).filter(
        Sucursal.id        == sucursal_id,
        Sucursal.tenant_id == tenant_id,
        Sucursal.activo    == True,
    ).first()
    if not s:
        raise HTTPException(status_code=404, detail="Sucursal no encontrada")
    return s


def _rango_utc(fecha_iso: str, tz_offset: int) -> tuple[datetime, datetime]:
    fecha_local = datetime.fromisoformat(fecha_iso)
    start_utc = (fecha_local - timedelta(hours=tz_offset)).replace(tzinfo=timezone.utc)
    end_utc   = start_utc + timedelta(days=1)
    return start_utc, end_utc


@router.get("/dia", response_model=ReporteDia)
def reporte_dia(
    sucursal_id: str = Query(..., description="ID de la sucursal"),
    fecha: Optional[str] = Query(None, description="Fecha YYYY-MM-DD. Default: hoy"),
    tz_offset: int = Query(-5, description="UTC offset en horas (ej: -5 para Colombia)"),
    user: dict    = Depends(get_current_user),
    db:   Session = Depends(get_db),
):
    """Retorna resumen de caja + detalle por producto del día (ventas + órdenes)."""

    sucursal = db.query(Sucursal).filter(
        Sucursal.id        == sucursal_id,
        Sucursal.tenant_id == user["tenant_id"],
        Sucursal.activo    == True,
    ).first()
    if not sucursal:
        raise HTTPException(status_code=404, detail="Sucursal no encontrada")

    if fecha is None:
        now_local = datetime.now(timezone.utc) + timedelta(hours=tz_offset)
        fecha = now_local.date().isoformat()

    # Construye rango UTC equivalente al día local solicitado, evitando
    # comparaciones `func.date(...)` que rompen cuando la fecha local cae
    # entre dos días UTC.
    fecha_local = datetime.fromisoformat(fecha)
    start_utc = (fecha_local - timedelta(hours=tz_offset)).replace(tzinfo=timezone.utc)
    end_utc   = start_utc + timedelta(days=1)

    # ── Ventas legacy (activas, no anuladas) ─────────────────────────
    ventas = (
        db.query(Venta)
        .filter(
            Venta.tenant_id   == user["tenant_id"],
            Venta.sucursal_id == sucursal_id,
            Venta.anulada     == False,
            Venta.fecha       >= start_utc,
            Venta.fecha       <  end_utc,
        )
        .all()
    )

    # ── Órdenes atómicas (activas, no anuladas) ─────────────────────
    ordenes = (
        db.query(Orden)
        .filter(
            Orden.tenant_id   == user["tenant_id"],
            Orden.sucursal_id == sucursal_id,
            Orden.anulada     == False,
            Orden.fecha       >= start_utc,
            Orden.fecha       <  end_utc,
        )
        .all()
    )

    # ── Agregar productos vendidos ───────────────────────────────────
    producto_map = {}  # {nombre: {cantidad, total}}

    # Legacy ventas
    for v in ventas:
        key = v.producto_nombre
        if key not in producto_map:
            producto_map[key] = {"cantidad": 0, "total": 0.0}
        producto_map[key]["cantidad"] += v.cantidad
        producto_map[key]["total"]    += v.total

    # Orden items
    for orden in ordenes:
        for item in orden.items:
            key = item.producto_nombre
            if key not in producto_map:
                producto_map[key] = {"cantidad": 0, "total": 0.0}
            producto_map[key]["cantidad"] += item.cantidad
            producto_map[key]["total"]    += item.total

    productos = [
        ReporteProducto(
            producto_nombre = nombre,
            cantidad_total  = data["cantidad"],
            total_ingresos  = round(data["total"], 2),
        )
        for nombre, data in sorted(producto_map.items(), key=lambda x: x[1]["total"], reverse=True)
    ]

    # ── Resumen de caja por método de pago ────────────────────────────
    metodo_map = {"Efectivo": 0.0, "Nequi": 0.0, "Daviplata": 0.0, "Tarjeta": 0.0}

    for v in ventas:
        if v.metodo_pago in metodo_map:
            metodo_map[v.metodo_pago] += v.total

    for orden in ordenes:
        if orden.metodo_pago in metodo_map:
            metodo_map[orden.metodo_pago] += orden.total

    total_dia = sum(metodo_map.values())

    resumen_caja = ResumenCaja(
        total_dia = round(total_dia, 2),
        efectivo  = round(metodo_map["Efectivo"], 2),
        nequi     = round(metodo_map["Nequi"], 2),
        daviplata = round(metodo_map["Daviplata"], 2),
        tarjeta   = round(metodo_map["Tarjeta"], 2),
    )

    return ReporteDia(
        fecha        = fecha,
        sucursal_id  = sucursal_id,
        productos    = productos,
        resumen_caja = resumen_caja,
    )


# ====================================================================
# /diario (consumido por el Dashboard)
# ====================================================================
@router.get("/diario", response_model=ReporteDiarioOut)
def reporte_diario(
    sucursal_id: Optional[str] = Query(None, description="ID de la sucursal (opcional)"),
    fecha:       Optional[str] = Query(None, description="Fecha YYYY-MM-DD. Default: hoy"),
    tz_offset:   int           = Query(-5, description="UTC offset en horas (Colombia=-5)"),
    user: dict    = Depends(get_current_user),
    db:   Session = Depends(get_db),
):
    """KPIs unificados del día para el dashboard.

    Combina ventas legacy + órdenes activas. Si no se envía `sucursal_id`,
    agrega TODO el tenant.
    """
    if sucursal_id:
        _verificar_sucursal(sucursal_id, user["tenant_id"], db)

    if fecha is None:
        now_local = datetime.now(timezone.utc) + timedelta(hours=tz_offset)
        fecha = now_local.date().isoformat()
    start_utc, end_utc = _rango_utc(fecha, tz_offset)

    # ── Filtros base ──────────────────────────────────────
    ventas_q = db.query(Venta).filter(
        Venta.tenant_id == user["tenant_id"],
        Venta.anulada   == False,
        Venta.fecha     >= start_utc,
        Venta.fecha     <  end_utc,
    )
    ordenes_q = db.query(Orden).filter(
        Orden.tenant_id == user["tenant_id"],
        Orden.anulada   == False,
        Orden.fecha     >= start_utc,
        Orden.fecha     <  end_utc,
    )
    if sucursal_id:
        ventas_q  = ventas_q.filter(Venta.sucursal_id == sucursal_id)
        ordenes_q = ordenes_q.filter(Orden.sucursal_id == sucursal_id)

    ventas  = ventas_q.all()
    ordenes = ordenes_q.all()

    # ── KPIs ───────────────────────────────────────────────
    total_ventas_legacy = sum(float(v.total) for v in ventas)
    total_ordenes_money = sum(float(o.total) for o in ordenes)
    total_ventas        = round(total_ventas_legacy + total_ordenes_money, 2)
    total_ordenes_count = len(ventas) + len(ordenes)
    ticket_promedio     = round(total_ventas / total_ordenes_count, 2) if total_ordenes_count else 0.0

    total_items = 0.0
    for v in ventas:
        total_items += float(v.cantidad)
    for o in ordenes:
        for it in o.items:
            total_items += float(it.cantidad)

    # ── Por método de pago ────────────────────────────────────
    por_metodo: dict[str, float] = {}
    for v in ventas:
        por_metodo[v.metodo_pago] = por_metodo.get(v.metodo_pago, 0.0) + float(v.total)
    for o in ordenes:
        por_metodo[o.metodo_pago] = por_metodo.get(o.metodo_pago, 0.0) + float(o.total)
    por_metodo = {k: round(val, 2) for k, val in por_metodo.items()}

    # ── Top productos ────────────────────────────────────────
    top_map: dict[str, dict] = {}
    for v in ventas:
        key = v.producto_id
        bucket = top_map.setdefault(key, {
            "producto_id": v.producto_id,
            "nombre":      v.producto_nombre,
            "cantidad":    0.0,
            "total":       0.0,
        })
        bucket["cantidad"] += float(v.cantidad)
        bucket["total"]    += float(v.total)
    for o in ordenes:
        for it in o.items:
            key = it.producto_id
            bucket = top_map.setdefault(key, {
                "producto_id": it.producto_id,
                "nombre":      it.producto_nombre,
                "cantidad":    0.0,
                "total":       0.0,
            })
            bucket["cantidad"] += float(it.cantidad)
            bucket["total"]    += float(it.total)

    top_productos = [
        TopProducto(
            producto_id = b["producto_id"],
            nombre      = b["nombre"],
            cantidad    = round(b["cantidad"], 3),
            total       = round(b["total"], 2),
        )
        for b in sorted(top_map.values(), key=lambda x: x["total"], reverse=True)[:10]
    ]

    return ReporteDiarioOut(
        fecha           = fecha,
        sucursal_id     = sucursal_id,
        total_ventas    = total_ventas,
        total_ordenes   = total_ordenes_count,
        ticket_promedio = ticket_promedio,
        total_items     = round(total_items, 3),
        por_metodo_pago = por_metodo,
        top_productos   = top_productos,
    )


# ====================================================================
# /rango (para la pantalla de Reportes con gráficas)
# ====================================================================
@router.get("/rango", response_model=ReporteRangoOut)
def reporte_rango(
    desde:       str           = Query(..., description="YYYY-MM-DD"),
    hasta:       str           = Query(..., description="YYYY-MM-DD (inclusive)"),
    sucursal_id: Optional[str] = Query(None),
    tz_offset:   int           = Query(-5),
    user: dict    = Depends(get_current_user),
    db:   Session = Depends(get_db),
):
    """Reporte agregado para un rango de fechas con serie diaria para gráficas."""
    if sucursal_id:
        _verificar_sucursal(sucursal_id, user["tenant_id"], db)

    fecha_inicio = datetime.fromisoformat(desde).date()
    fecha_fin    = datetime.fromisoformat(hasta).date()
    if fecha_fin < fecha_inicio:
        raise HTTPException(status_code=422, detail="`hasta` no puede ser anterior a `desde`")
    if (fecha_fin - fecha_inicio).days > 366:
        raise HTTPException(status_code=422, detail="Rango máximo de 366 días")

    start_utc, _ = _rango_utc(desde, tz_offset)
    _, end_utc   = _rango_utc(hasta, tz_offset)

    ordenes_q = db.query(Orden).filter(
        Orden.tenant_id == user["tenant_id"],
        Orden.anulada   == False,
        Orden.fecha     >= start_utc,
        Orden.fecha     <  end_utc,
    )
    ventas_q = db.query(Venta).filter(
        Venta.tenant_id == user["tenant_id"],
        Venta.anulada   == False,
        Venta.fecha     >= start_utc,
        Venta.fecha     <  end_utc,
    )
    if sucursal_id:
        ordenes_q = ordenes_q.filter(Orden.sucursal_id == sucursal_id)
        ventas_q  = ventas_q.filter(Venta.sucursal_id == sucursal_id)

    ordenes = ordenes_q.all()
    ventas  = ventas_q.all()

    # Acumuladores
    total_ventas        = 0.0
    total_items         = 0.0
    por_metodo: dict[str, float] = {}
    top_map: dict[str, dict]     = {}
    serie: dict[str, dict]       = {}   # {fecha_iso: {total, count}}

    def _bucket_dia(fecha: datetime) -> str:
        local = fecha.astimezone(timezone.utc) + timedelta(hours=tz_offset)
        return local.date().isoformat()

    for v in ventas:
        total_ventas += float(v.total)
        total_items  += float(v.cantidad)
        por_metodo[v.metodo_pago] = por_metodo.get(v.metodo_pago, 0.0) + float(v.total)
        d = _bucket_dia(v.fecha)
        serie.setdefault(d, {"total_ventas": 0.0, "total_ordenes": 0})
        serie[d]["total_ventas"]  += float(v.total)
        serie[d]["total_ordenes"] += 1
        b = top_map.setdefault(v.producto_id, {
            "producto_id": v.producto_id, "nombre": v.producto_nombre,
            "cantidad": 0.0, "total": 0.0,
        })
        b["cantidad"] += float(v.cantidad)
        b["total"]    += float(v.total)

    for o in ordenes:
        total_ventas += float(o.total)
        por_metodo[o.metodo_pago] = por_metodo.get(o.metodo_pago, 0.0) + float(o.total)
        d = _bucket_dia(o.fecha)
        serie.setdefault(d, {"total_ventas": 0.0, "total_ordenes": 0})
        serie[d]["total_ventas"]  += float(o.total)
        serie[d]["total_ordenes"] += 1
        for it in o.items:
            total_items += float(it.cantidad)
            b = top_map.setdefault(it.producto_id, {
                "producto_id": it.producto_id, "nombre": it.producto_nombre,
                "cantidad": 0.0, "total": 0.0,
            })
            b["cantidad"] += float(it.cantidad)
            b["total"]    += float(it.total)

    total_ordenes_count = len(ordenes) + len(ventas)
    ticket_promedio     = round(total_ventas / total_ordenes_count, 2) if total_ordenes_count else 0.0

    # Rellenar fechas faltantes con ceros
    serie_diaria: list[dict] = []
    actual = fecha_inicio
    while actual <= fecha_fin:
        key = actual.isoformat()
        bucket = serie.get(key, {"total_ventas": 0.0, "total_ordenes": 0})
        serie_diaria.append({
            "fecha":         key,
            "total_ventas":  round(bucket["total_ventas"], 2),
            "total_ordenes": int(bucket["total_ordenes"]),
        })
        actual += timedelta(days=1)

    top_productos = [
        TopProducto(
            producto_id=b["producto_id"], nombre=b["nombre"],
            cantidad=round(b["cantidad"], 3), total=round(b["total"], 2),
        )
        for b in sorted(top_map.values(), key=lambda x: x["total"], reverse=True)[:10]
    ]

    return ReporteRangoOut(
        desde           = desde,
        hasta           = hasta,
        sucursal_id     = sucursal_id,
        total_ventas    = round(total_ventas, 2),
        total_ordenes   = total_ordenes_count,
        ticket_promedio = ticket_promedio,
        total_items     = round(total_items, 3),
        por_metodo_pago = {k: round(v, 2) for k, v in por_metodo.items()},
        top_productos   = top_productos,
        serie_diaria    = serie_diaria,
    )
