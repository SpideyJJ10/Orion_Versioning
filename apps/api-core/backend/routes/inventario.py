"""
routes/inventario.py — Vista agregada de inventario y alertas de stock bajo.

Estos endpoints sirven datos al UI de inventario y al motor de ML.
La predicción de demanda más sofisticada vive en backend/ml/.
"""
from typing import List, Optional

from fastapi import APIRouter, Depends, HTTPException, Query
from sqlalchemy.orm import Session

from backend.auth_v3 import get_current_usuario as get_current_user
from backend.db.session import get_db
from backend.models.orm import MovimientoInventario, Producto, Sucursal
from backend.schemas import AlertaStockBajo, MovimientoInventarioOut

router = APIRouter(prefix="/api/inventario", tags=["Inventario"])


def _severidad_stock(stock: float, stock_minimo: float) -> Optional[str]:
    """Devuelve la severidad de la alerta de stock o None si está OK.

    Reglas (heurística base; el módulo ML refinará con predicción de demanda):
      - stock <= 0                 → 'agotado'
      - stock <= stock_minimo      → 'critical'
      - stock <= stock_minimo * 2  → 'warning'
      - en otro caso               → None (sin alerta)
    """
    if stock_minimo is None or stock_minimo <= 0:
        # Si el tenant no configuró stock_minimo, solo alertamos cuando se agota.
        return "agotado" if stock <= 0 else None
    if stock <= 0:
        return "agotado"
    if stock <= stock_minimo:
        return "critical"
    if stock <= stock_minimo * 2:
        return "warning"
    return None


@router.get("/alertas/stock-bajo", response_model=List[AlertaStockBajo])
def alertas_stock_bajo(
    sucursal_id: Optional[str] = Query(None, description="Filtrar por sucursal (opcional)"),
    user: dict    = Depends(get_current_user),
    db:   Session = Depends(get_db),
):
    """Devuelve productos del tenant con stock bajo o agotado.

    Usa una heurística pura (stock vs stock_minimo). El motor ML genera
    alertas más ricas en `/api/v3/ml/alerts` (Fase 2).
    """
    query = db.query(Producto, Sucursal).join(
        Sucursal, Producto.sucursal_id == Sucursal.id, isouter=True
    ).filter(
        Producto.tenant_id == user["tenant_id"],
        Producto.activo    == True,
    )
    if sucursal_id:
        query = query.filter(Producto.sucursal_id == sucursal_id)

    alertas: list[AlertaStockBajo] = []
    for producto, sucursal in query.all():
        stock        = float(producto.stock or 0.0)
        stock_minimo = float(producto.stock_minimo or 0.0)
        severidad    = _severidad_stock(stock, stock_minimo)
        if severidad is None:
            continue
        alertas.append(AlertaStockBajo(
            producto_id     = producto.id,
            producto_nombre = producto.nombre,
            sucursal_id     = producto.sucursal_id,
            sucursal_nombre = sucursal.nombre if sucursal else None,
            stock           = stock,
            stock_minimo    = stock_minimo,
            unidad_medida   = producto.unidad_medida or "unidad",
            severidad       = severidad,
        ))

    # Orden: agotados → criticos → warnings, dentro de cada grupo más bajo primero
    orden_severidad = {"agotado": 0, "critical": 1, "warning": 2}
    alertas.sort(key=lambda a: (orden_severidad.get(a.severidad, 99), a.stock))
    return alertas


@router.get("/movimientos", response_model=List[MovimientoInventarioOut])
def listar_movimientos_tenant(
    sucursal_id: Optional[str] = Query(None),
    tipo:        Optional[str] = Query(None, pattern="^(entrada|salida|ajuste|venta|merma|devolucion)$"),
    limit:       int           = Query(100, ge=1, le=500),
    user: dict    = Depends(get_current_user),
    db:   Session = Depends(get_db),
):
    """Histórico de movimientos del tenant, con filtros opcionales por sucursal/tipo."""
    query = db.query(MovimientoInventario).filter(
        MovimientoInventario.tenant_id == user["tenant_id"],
    )
    if sucursal_id:
        query = query.filter(MovimientoInventario.sucursal_id == sucursal_id)
    if tipo:
        query = query.filter(MovimientoInventario.tipo == tipo)

    movimientos = query.order_by(MovimientoInventario.fecha.desc()).limit(limit).all()
    return [
        MovimientoInventarioOut(
            id            = m.id,
            producto_id   = m.producto_id,
            sucursal_id   = m.sucursal_id,
            tipo          = m.tipo,
            cantidad      = m.cantidad,
            stock_antes   = m.stock_antes,
            stock_despues = m.stock_despues,
            motivo        = m.motivo,
            referencia_id = m.referencia_id,
            usuario_id    = m.usuario_id,
            fecha         = m.fecha.strftime("%Y-%m-%d %H:%M:%S") if m.fecha else "",
        )
        for m in movimientos
    ]


@router.get("/resumen")
def resumen_inventario(
    sucursal_id: Optional[str] = Query(None),
    user: dict    = Depends(get_current_user),
    db:   Session = Depends(get_db),
):
    """KPIs rápidos para el dashboard de inventario.

    Returns:
      total_productos:       cantidad de productos activos
      total_unidades:        suma de stock (en unidades, mezclando unidades de medida)
      valor_inventario:      suma de (stock * precio)
      productos_agotados:    cuántos tienen stock <= 0
      productos_criticos:    cuántos están en o por debajo del stock_minimo
      productos_warning:     cuántos están entre stock_minimo y 2x stock_minimo
    """
    query = db.query(Producto).filter(
        Producto.tenant_id == user["tenant_id"],
        Producto.activo    == True,
    )
    if sucursal_id:
        query = query.filter(Producto.sucursal_id == sucursal_id)

    productos = query.all()

    total_productos    = len(productos)
    total_unidades     = sum(float(p.stock or 0) for p in productos)
    valor_inventario   = sum(float(p.stock or 0) * float(p.precio or 0) for p in productos)
    productos_agotados = sum(1 for p in productos if (p.stock or 0) <= 0)
    productos_criticos = sum(
        1 for p in productos
        if (p.stock or 0) > 0 and (p.stock_minimo or 0) > 0 and (p.stock or 0) <= (p.stock_minimo or 0)
    )
    productos_warning = sum(
        1 for p in productos
        if (p.stock_minimo or 0) > 0
        and (p.stock or 0) > (p.stock_minimo or 0)
        and (p.stock or 0) <= (p.stock_minimo or 0) * 2
    )

    return {
        "total_productos":    total_productos,
        "total_unidades":     round(total_unidades, 2),
        "valor_inventario":   round(valor_inventario, 2),
        "productos_agotados": productos_agotados,
        "productos_criticos": productos_criticos,
        "productos_warning":  productos_warning,
    }
