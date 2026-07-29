"""
routes/ordenes.py — Registro atómico de órdenes completas
Una orden = una transacción POS completa con todos sus items.
"""
import json
from datetime import datetime, timedelta, timezone
from typing import Optional

from fastapi import APIRouter, HTTPException, Depends, Query, BackgroundTasks
from sqlalchemy.orm import Session
from sqlalchemy import func

from backend.db.session import get_db
from backend.models.orm import (
    MovimientoInventario,
    Orden,
    OrdenItem,
    Producto,
    Sucursal,
    Tenant,
    TenantBranding,
)
from backend.schemas import OrdenCreate, OrdenOut, OrdenItemOut, OrdenListOut
from backend.auth_v3 import get_current_usuario as get_current_user
from backend.core.config import ADMIN_PIN
from backend.services.dian import emitir_factura_electronica_dian

router = APIRouter(prefix="/api/ordenes", tags=["Órdenes"])


def _verificar_sucursal(sucursal_id: str, tenant_id: int, db: Session) -> Sucursal:
    s = db.query(Sucursal).filter(
        Sucursal.id        == sucursal_id,
        Sucursal.tenant_id == tenant_id,
        Sucursal.activo    == True,
    ).first()
    if not s:
        raise HTTPException(status_code=404, detail="Sucursal no encontrada")
    return s


def _serialize_orden(orden: Orden) -> OrdenOut:
    cambio = None
    if orden.metodo_pago == "Efectivo" and orden.efectivo_recibido is not None:
        cambio = round(float(orden.efectivo_recibido) - float(orden.total), 2)
    return OrdenOut(
        id                = orden.id,
        fecha             = orden.fecha.strftime("%Y-%m-%d %H:%M:%S"),
        sucursal_id       = orden.sucursal_id,
        metodo_pago       = orden.metodo_pago,
        subtotal          = orden.subtotal,
        descuento         = float(orden.descuento or 0.0),
        domicilio         = orden.domicilio,
        total             = orden.total,
        efectivo_recibido = orden.efectivo_recibido,
        cambio            = cambio,
        cliente_nombre    = orden.cliente_nombre,
        notas             = orden.notas,
        metodo_pago_extra = orden.metodo_pago_extra,
        anulada           = orden.anulada,
        dian_status       = orden.dian_status,
        dian_cufe         = orden.dian_cufe,
        dian_pdf_url      = orden.dian_pdf_url,
        dian_xml_url      = orden.dian_xml_url,
        items             = [
            OrdenItemOut(
                id              = item.id,
                producto_id     = item.producto_id,
                producto_nombre = item.producto_nombre,
                cantidad        = item.cantidad,
                precio_unitario = item.precio_unitario,
                total           = item.total,
            )
            for item in orden.items
        ],
    )


@router.post("", response_model=OrdenOut, status_code=201)
def crear_orden(
    data: OrdenCreate,
    background_tasks: BackgroundTasks,
    user: dict    = Depends(get_current_user),
    db:   Session = Depends(get_db),
):
    """
    Registra una orden completa atómicamente.
    Todos los items se validan, persisten Y descuentan stock en una sola
    transacción DB. Cada ítem genera un MovimientoInventario tipo='venta'.

    Ítems manuales (`producto_id` empieza con '__') no afectan stock.
    Si algún producto tiene stock insuficiente, la orden se rechaza completa.
    """
    _verificar_sucursal(data.sucursal_id, user["tenant_id"], db)

    subtotal = 0.0
    items_db: list[OrdenItem] = []
    stock_changes: list[tuple[Producto, int]] = []  # (producto, cantidad)

    MANUAL_PREFIX = "__"

    for item in data.items:
        if item.producto_id.startswith(MANUAL_PREFIX):
            # Entrada manual (domicilio, custom, etc.) — sin stock
            if not item.producto_nombre or not item.precio_unitario:
                raise HTTPException(
                    status_code=422,
                    detail="producto_nombre y precio_unitario son obligatorios para entradas manuales",
                )
            nombre = item.producto_nombre
            precio = item.precio_unitario
        else:
            producto = db.query(Producto).filter(
                Producto.id          == item.producto_id,
                Producto.tenant_id   == user["tenant_id"],
                Producto.sucursal_id == data.sucursal_id,
                Producto.activo      == True,
            ).first()
            if not producto:
                raise HTTPException(
                    status_code=404,
                    detail=f"Producto '{item.producto_id}' no encontrado en esta sucursal",
                )
            # Validación de stock (si stock se rastrea, es decir, > 0 alguna vez)
            if (producto.stock or 0) < item.cantidad:
                raise HTTPException(
                    status_code=409,
                    detail=(
                        f"Stock insuficiente para '{producto.nombre}': "
                        f"disponible={producto.stock}, solicitado={item.cantidad}"
                    ),
                )
            nombre = producto.nombre
            precio = producto.precio
            stock_changes.append((producto, item.cantidad))

        item_total = round(precio * item.cantidad, 2)
        subtotal += item_total
        items_db.append(OrdenItem(
            producto_id     = item.producto_id,
            producto_nombre = nombre,
            cantidad        = item.cantidad,
            precio_unitario = precio,
            total           = item_total,
        ))

    subtotal  = round(subtotal, 2)
    descuento = round(float(data.descuento or 0.0), 2)
    domicilio = round(data.domicilio, 2)

    if descuento > subtotal:
        raise HTTPException(
            status_code=422,
            detail=f"El descuento ({descuento}) no puede exceder el subtotal ({subtotal})",
        )

    total = round(subtotal - descuento + domicilio, 2)

    # Validación de pago en efectivo
    efectivo_recibido = None
    if data.efectivo_recibido is not None:
        if data.metodo_pago.value != "Efectivo":
            raise HTTPException(
                status_code=422,
                detail="efectivo_recibido solo aplica para metodo_pago='Efectivo'",
            )
        if data.efectivo_recibido < total:
            raise HTTPException(
                status_code=422,
                detail=f"Efectivo recibido ({data.efectivo_recibido}) menor al total ({total})",
            )
        efectivo_recibido = round(float(data.efectivo_recibido), 2)

    # Validación de pago mixto
    metodo_pago_extra: Optional[str] = None
    if data.metodo_pago.value == "Mixto":
        if not data.pagos_mixtos or len(data.pagos_mixtos) < 2:
            raise HTTPException(
                status_code=422,
                detail="metodo_pago='Mixto' requiere al menos 2 pagos en pagos_mixtos",
            )
        suma = round(sum(p.monto for p in data.pagos_mixtos), 2)
        if abs(suma - total) > 0.01:
            raise HTTPException(
                status_code=422,
                detail=f"La suma de pagos mixtos ({suma}) no coincide con el total ({total})",
            )
        metodo_pago_extra = json.dumps(
            [{"metodo": p.metodo.value, "monto": round(p.monto, 2)} for p in data.pagos_mixtos]
        )

    orden = Orden(
        tenant_id         = user["tenant_id"],
        sucursal_id       = data.sucursal_id,
        metodo_pago       = data.metodo_pago.value,
        subtotal          = subtotal,
        descuento         = descuento,
        domicilio         = domicilio,
        total             = total,
        efectivo_recibido = efectivo_recibido,
        metodo_pago_extra = metodo_pago_extra,
        cliente_nombre    = (data.cliente_nombre or None),
        notas             = (data.notas or None),
        usuario_id        = user.get("usuario_id"),
        items             = items_db,
    )
    db.add(orden)
    db.flush()  # obtiene orden.id para referencia en movimientos

    # ── Descontar stock + registrar ledger ──────────────────────────────
    for producto, cantidad_vendida in stock_changes:
        stock_antes   = float(producto.stock or 0.0)
        stock_despues = round(stock_antes - cantidad_vendida, 4)
        producto.stock = stock_despues
        db.add(MovimientoInventario(
            tenant_id     = user["tenant_id"],
            sucursal_id   = data.sucursal_id,
            producto_id   = producto.id,
            tipo          = "venta",
            cantidad      = -float(cantidad_vendida),
            stock_antes   = stock_antes,
            stock_despues = stock_despues,
            motivo        = None,
            referencia_id = orden.id,
            usuario_id    = user.get("usuario_id"),
        ))

    db.commit()
    db.refresh(orden)
    
    # Lanzar emisión de factura DIAN en background
    background_tasks.add_task(emitir_factura_electronica_dian, orden.id)
    
    return _serialize_orden(orden)


@router.get("", response_model=list[OrdenOut])
def listar_ordenes(
    sucursal_id: str = Query(..., description="ID de la sucursal"),
    fecha: Optional[str] = Query(None, description="Fecha YYYY-MM-DD. Default: hoy"),
    tz_offset: int = Query(-5, description="UTC offset en horas (ej: -5 para Colombia)"),
    user: dict    = Depends(get_current_user),
    db:   Session = Depends(get_db),
):
    """Lista órdenes del día para una sucursal."""
    _verificar_sucursal(sucursal_id, user["tenant_id"], db)

    if fecha is None:
        now_local = datetime.now(timezone.utc) + timedelta(hours=tz_offset)
        fecha = now_local.date().isoformat()

    # Convertir "fecha local" + tz_offset a un rango UTC [inicio, fin].
    # Esto evita errores de zona horaria cuando la medianoche local cae en
    # otro día UTC (p. ej. 00:00 Colombia = 05:00 UTC del mismo día).
    fecha_local = datetime.fromisoformat(fecha)
    start_utc = (fecha_local - timedelta(hours=tz_offset)).replace(tzinfo=timezone.utc)
    end_utc   = start_utc + timedelta(days=1)

    ordenes = (
        db.query(Orden)
        .filter(
            Orden.tenant_id   == user["tenant_id"],
            Orden.sucursal_id == sucursal_id,
            Orden.fecha       >= start_utc,
            Orden.fecha       <  end_utc,
        )
        .order_by(Orden.fecha.desc())
        .all()
    )

    return [_serialize_orden(o) for o in ordenes]


@router.get("/{orden_id}", response_model=OrdenOut)
def obtener_orden(
    orden_id: str,
    user: dict    = Depends(get_current_user),
    db:   Session = Depends(get_db),
):
    """Detalle de una orden por id (útil para reimpresión de recibo)."""
    orden = db.query(Orden).filter(
        Orden.id        == orden_id,
        Orden.tenant_id == user["tenant_id"],
    ).first()
    if not orden:
        raise HTTPException(status_code=404, detail="Orden no encontrada")
    return _serialize_orden(orden)


@router.get("/{orden_id}/recibo")
def recibo_orden(
    orden_id: str,
    user: dict    = Depends(get_current_user),
    db:   Session = Depends(get_db),
):
    """Devuelve los datos necesarios para imprimir el recibo en el cliente.

    Combina datos de la orden con identidad del tenant (nombre comercial, logo,
    color primario) para que el frontend renderice un ticket completo sin
    necesidad de múltiples llamadas.
    """
    orden = db.query(Orden).filter(
        Orden.id        == orden_id,
        Orden.tenant_id == user["tenant_id"],
    ).first()
    if not orden:
        raise HTTPException(status_code=404, detail="Orden no encontrada")

    tenant   = db.query(Tenant).filter(Tenant.id == user["tenant_id"]).first()
    branding = db.query(TenantBranding).filter(
        TenantBranding.tenant_id == user["tenant_id"]
    ).first()
    sucursal = db.query(Sucursal).filter(Sucursal.id == orden.sucursal_id).first()

    pagos_mixtos: list[dict] = []
    if orden.metodo_pago_extra:
        try:
            pagos_mixtos = json.loads(orden.metodo_pago_extra)
        except json.JSONDecodeError:
            pagos_mixtos = []

    cambio = None
    if orden.metodo_pago == "Efectivo" and orden.efectivo_recibido is not None:
        cambio = round(float(orden.efectivo_recibido) - float(orden.total), 2)

    return {
        "orden": _serialize_orden(orden).model_dump(),
        "negocio": {
            "nombre_comercial": (branding.nombre_comercial if branding else (tenant.nombre if tenant else "Negocio")),
            "logo_url":         (branding.logo_url if branding else None),
            "color_primary":    (branding.color_primary if branding else "#8b5cf6"),
            "sucursal":         (sucursal.nombre if sucursal else None),
            "telefono":         (tenant.telefono if tenant else None),
        },
        "pago": {
            "metodo":            orden.metodo_pago,
            "efectivo_recibido": orden.efectivo_recibido,
            "cambio":            cambio,
            "pagos_mixtos":      pagos_mixtos,
        },
    }


@router.delete("/{orden_id}", status_code=204)
def anular_orden(
    orden_id: str,
    pin: str      = Query(..., description="PIN de administrador"),
    user: dict    = Depends(get_current_user),
    db:   Session = Depends(get_db),
):
    """Anula (soft delete) una orden completa y RESTAURA el stock vendido.

    Cada ítem de producto real (no manual) genera un MovimientoInventario
    tipo='devolucion' con motivo='Anulación de orden'. Idempotente: si ya
    está anulada no hace nada.
    """
    if pin != ADMIN_PIN:
        raise HTTPException(status_code=403, detail="PIN incorrecto")

    orden = db.query(Orden).filter(
        Orden.id        == orden_id,
        Orden.tenant_id == user["tenant_id"],
    ).first()
    if not orden:
        raise HTTPException(status_code=404, detail="Orden no encontrada")

    if orden.anulada:
        return  # idempotente

    MANUAL_PREFIX = "__"
    for item in orden.items:
        if item.producto_id.startswith(MANUAL_PREFIX):
            continue
        producto = db.query(Producto).filter(
            Producto.id        == item.producto_id,
            Producto.tenant_id == user["tenant_id"],
        ).first()
        if not producto:
            continue  # producto fue eliminado; no podemos restaurar pero permitimos anular
        stock_antes   = float(producto.stock or 0.0)
        stock_despues = round(stock_antes + item.cantidad, 4)
        producto.stock = stock_despues
        db.add(MovimientoInventario(
            tenant_id     = user["tenant_id"],
            sucursal_id   = orden.sucursal_id,
            producto_id   = producto.id,
            tipo          = "devolucion",
            cantidad      = float(item.cantidad),
            stock_antes   = stock_antes,
            stock_despues = stock_despues,
            motivo        = "Anulación de orden",
            referencia_id = orden.id,
            usuario_id    = user.get("usuario_id"),
        ))

    orden.anulada = True
    db.commit()
