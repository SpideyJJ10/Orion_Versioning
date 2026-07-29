"""
routes/ventas.py — Registro, listado y anulación de transacciones POS (legacy)
Nota: Nuevas ventas deben usar POST /api/ordenes para transacciones atómicas.
"""
from datetime import datetime, timedelta, timezone
from typing import Optional

from fastapi import APIRouter, HTTPException, Depends, Query
from sqlalchemy.orm import Session
from sqlalchemy import func

from backend.db.session import get_db
from backend.models.orm import Producto, Sucursal, Venta
from backend.schemas import VentaCreate, VentaOut, VentaListOut, VentaUpdate
from backend.auth_v3 import get_current_usuario as get_current_user
from backend.core.config import ADMIN_PIN

router = APIRouter(prefix="/api/ventas", tags=["Ventas"])


@router.get("", response_model=list[VentaListOut])
def listar_ventas(
    sucursal_id: str = Query(..., description="ID de la sucursal"),
    fecha: Optional[str] = Query(None, description="Fecha YYYY-MM-DD. Default: hoy"),
    tz_offset: int = Query(-5, description="UTC offset en horas (ej: -5 para Colombia)"),
    user: dict    = Depends(get_current_user),
    db:   Session = Depends(get_db),
):
    """Lista ventas del día para una sucursal (solo admin o tenant propio)."""
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

    ventas = (
        db.query(Venta)
        .filter(
            Venta.tenant_id   == user["tenant_id"],
            Venta.sucursal_id == sucursal_id,
            func.date(Venta.fecha) == fecha,
        )
        .order_by(Venta.fecha.desc())
        .all()
    )

    return [
        VentaListOut(
            id              = v.id,
            fecha           = v.fecha.strftime("%Y-%m-%d %H:%M:%S"),
            producto_nombre = v.producto_nombre,
            cantidad        = v.cantidad,
            precio_unitario = v.precio_unitario,
            total           = v.total,
            metodo_pago     = v.metodo_pago,
            anulada         = v.anulada,
        )
        for v in ventas
    ]


@router.post("", response_model=VentaOut, status_code=201)
def registrar_venta(
    data: VentaCreate,
    user: dict    = Depends(get_current_user),
    db:   Session = Depends(get_db),
):
    """
    Registra una venta en la sucursal indicada.
    Valida que el producto pertenezca a la misma sucursal.
    El precio se lee del producto en la BD (no del cliente).
    """
    # 1. Verificar sucursal
    sucursal = db.query(Sucursal).filter(
        Sucursal.id        == data.sucursal_id,
        Sucursal.tenant_id == user["tenant_id"],
        Sucursal.activo    == True,
    ).first()
    if not sucursal:
        raise HTTPException(status_code=404, detail="Sucursal no encontrada")

    # 2. Resolver producto: lookup en BD o entrada manual (domicilio, etc.)
    MANUAL_PREFIX = "__"
    if data.producto_id.startswith(MANUAL_PREFIX):
        # Entrada manual — no requiere producto en BD
        if not data.producto_nombre or not data.precio_unitario:
            raise HTTPException(
                status_code=422,
                detail="producto_nombre y precio_unitario son obligatorios para entradas manuales",
            )
        nombre_producto = data.producto_nombre
        precio_producto = data.precio_unitario
    else:
        producto = db.query(Producto).filter(
            Producto.id          == data.producto_id,
            Producto.tenant_id   == user["tenant_id"],
            Producto.sucursal_id == data.sucursal_id,
            Producto.activo      == True,
        ).first()

        if not producto:
            raise HTTPException(
                status_code=404,
                detail=f"Producto '{data.producto_id}' no encontrado en esta sucursal",
            )
        nombre_producto = producto.nombre
        precio_producto = producto.precio

    # 3. Calcular total server-side
    total = round(precio_producto * data.cantidad, 2)

    # 4. Persistir venta con snapshot
    venta = Venta(
        tenant_id       = user["tenant_id"],
        sucursal_id     = data.sucursal_id,
        fecha           = datetime.now(timezone.utc),
        producto_id     = data.producto_id,
        producto_nombre = nombre_producto,
        cantidad        = data.cantidad,
        precio_unitario = precio_producto,
        total           = total,
        metodo_pago     = data.metodo_pago.value,
        anulada         = False,
    )
    db.add(venta)
    db.commit()
    db.refresh(venta)

    return VentaOut(
        id              = venta.id,
        fecha           = venta.fecha.strftime("%Y-%m-%d %H:%M:%S"),
        producto_id     = venta.producto_id,
        producto_nombre = venta.producto_nombre,
        cantidad        = venta.cantidad,
        precio_unitario = venta.precio_unitario,
        total           = venta.total,
        metodo_pago     = venta.metodo_pago,
        anulada         = venta.anulada,
    )


@router.put("/{venta_id}", response_model=VentaOut)
def editar_venta(
    venta_id: str,
    data: VentaUpdate,
    pin: str      = Query(..., description="Código PIN de administrador"),
    user: dict    = Depends(get_current_user),
    db:   Session = Depends(get_db),
):
    """Edita cantidad y/o método de pago de una venta. Requiere PIN de admin."""
    if pin != ADMIN_PIN:
        raise HTTPException(status_code=403, detail="PIN incorrecto")

    venta = db.query(Venta).filter(
        Venta.id        == venta_id,
        Venta.tenant_id == user["tenant_id"],
    ).first()
    if not venta:
        raise HTTPException(status_code=404, detail="Venta no encontrada")
    if venta.anulada:
        raise HTTPException(status_code=400, detail="No se puede editar una venta anulada")

    if data.metodo_pago is not None:
        venta.metodo_pago = data.metodo_pago.value

    if data.cantidad is not None:
        venta.cantidad = data.cantidad
        venta.total    = round(venta.precio_unitario * data.cantidad, 2)

    db.commit()
    db.refresh(venta)

    return VentaOut(
        id              = venta.id,
        fecha           = venta.fecha.strftime("%Y-%m-%d %H:%M:%S"),
        producto_id     = venta.producto_id,
        producto_nombre = venta.producto_nombre,
        cantidad        = venta.cantidad,
        precio_unitario = venta.precio_unitario,
        total           = venta.total,
        metodo_pago     = venta.metodo_pago,
        anulada         = venta.anulada,
    )


@router.delete("/{venta_id}", status_code=204)
def anular_venta(
    venta_id: str,
    pin: str      = Query(..., description="Código PIN de administrador"),
    user: dict    = Depends(get_current_user),
    db:   Session = Depends(get_db),
):
    """Anula (soft delete) una venta. Requiere PIN de administrador."""
    if pin != ADMIN_PIN:
        raise HTTPException(status_code=403, detail="PIN incorrecto")

    venta = db.query(Venta).filter(
        Venta.id        == venta_id,
        Venta.tenant_id == user["tenant_id"],
    ).first()
    if not venta:
        raise HTTPException(status_code=404, detail="Venta no encontrada")

    venta.anulada = True
    db.commit()
