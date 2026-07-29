"""
routes/productos.py — CRUD de productos por sucursal
Todos los queries filtran por tenant_id + sucursal_id.
"""
from typing import Optional

from fastapi import APIRouter, HTTPException, Depends, Query
from sqlalchemy.orm import Session

from backend.db.session import get_db
from backend.models.orm import Categoria, MovimientoInventario, Producto, Sucursal
from backend.schemas import (
    AjusteStockRequest,
    MovimientoInventarioOut,
    ProductoCreate,
    ProductoOut,
    ProductoUpdate,
)
from backend.auth_v3 import get_current_usuario as get_current_user

router = APIRouter(prefix="/api/productos", tags=["Productos"])


def _verificar_sucursal(sucursal_id: str, tenant_id: int, db: Session) -> Sucursal:
    """Valida que la sucursal exista y pertenezca al tenant."""
    s = db.query(Sucursal).filter(
        Sucursal.id        == sucursal_id,
        Sucursal.tenant_id == tenant_id,
        Sucursal.activo    == True,
    ).first()
    if not s:
        raise HTTPException(status_code=404, detail="Sucursal no encontrada")
    return s


def _resolver_categoria_id(tenant_id: int, sucursal_id: str, categoria_nombre: str, db: Session) -> Optional[str]:
    """Resuelve el ID de una categoría a partir del nombre."""
    if not categoria_nombre:
        return None
    cat = db.query(Categoria).filter(
        Categoria.tenant_id   == tenant_id,
        Categoria.sucursal_id == sucursal_id,
        Categoria.nombre      == categoria_nombre,
        Categoria.activo      == True,
    ).first()
    return cat.id if cat else None


@router.get("", response_model=list[ProductoOut])
def listar_productos(
    sucursal_id: Optional[str] = Query(None, description="ID de la sucursal"),
    incluir_inactivos: bool = Query(False, description="Incluir productos desactivados"),
    search: Optional[str] = Query(None, description="Buscar por nombre o SKU (case-insensitive)"),
    user: dict    = Depends(get_current_user),
    db:   Session = Depends(get_db),
):
    """Retorna productos de la sucursal indicada.

    - `incluir_inactivos=true` permite recuperar también los desactivados (admin/manager).
    - `search` filtra por nombre **o** SKU.
    """
    if not sucursal_id:
        return []

    _verificar_sucursal(sucursal_id, user["tenant_id"], db)

    q = db.query(Producto).filter(
        Producto.tenant_id   == user["tenant_id"],
        Producto.sucursal_id == sucursal_id,
    )
    if not incluir_inactivos:
        q = q.filter(Producto.activo == True)
    if search:
        like = f"%{search.strip()}%"
        q = q.filter(
            (Producto.nombre.ilike(like)) | (Producto.sku.ilike(like))
        )
    return q.order_by(Producto.nombre).all()


@router.get("/{producto_id}", response_model=ProductoOut)
def obtener_producto(
    producto_id: str,
    user: dict    = Depends(get_current_user),
    db:   Session = Depends(get_db),
):
    """Retorna un producto por id. Útil para vista de detalle."""
    p = db.query(Producto).filter(
        Producto.id        == producto_id,
        Producto.tenant_id == user["tenant_id"],
    ).first()
    if not p:
        raise HTTPException(status_code=404, detail="Producto no encontrado")
    return p


@router.post("", response_model=ProductoOut, status_code=201)
def crear_producto(
    data: ProductoCreate,
    user: dict    = Depends(get_current_user),
    db:   Session = Depends(get_db),
):
    """Crea un nuevo producto en la sucursal indicada.

    Si se provee `stock` > 0, registra automáticamente un MovimientoInventario
    de tipo 'entrada' con motivo 'Stock inicial al crear producto'.
    """
    _verificar_sucursal(data.sucursal_id, user["tenant_id"], db)

    stock_inicial = float(data.stock or 0.0)

    producto = Producto(
        tenant_id     = user["tenant_id"],
        sucursal_id   = data.sucursal_id,
        nombre        = data.nombre,
        precio        = data.precio,
        costo         = float(data.costo or 0.0),
        insumos       = data.insumos or "",
        descripcion   = data.descripcion,
        sku           = data.sku,
        imagen_url    = data.imagen_url,
        categoria     = data.categoria,
        categoria_id  = _resolver_categoria_id(user["tenant_id"], data.sucursal_id, data.categoria, db),
        stock         = stock_inicial,
        stock_minimo  = float(data.stock_minimo or 0.0),
        unidad_medida = data.unidad_medida or "unidad",
    )
    db.add(producto)
    db.flush()

    # Ledger: stock inicial > 0 ⇒ registrar entrada inicial.
    if stock_inicial > 0:
        db.add(MovimientoInventario(
            tenant_id     = user["tenant_id"],
            sucursal_id   = data.sucursal_id,
            producto_id   = producto.id,
            tipo          = "entrada",
            cantidad      = stock_inicial,
            stock_antes   = 0.0,
            stock_despues = stock_inicial,
            motivo        = "Stock inicial al crear producto",
            referencia_id = None,
            usuario_id    = user.get("usuario_id"),
        ))

    db.commit()
    db.refresh(producto)
    return producto


@router.put("/{producto_id}", response_model=ProductoOut)
def editar_producto(
    producto_id: str,
    data: ProductoUpdate,
    user: dict    = Depends(get_current_user),
    db:   Session = Depends(get_db),
):
    """Edita campos del producto. Acepta cambios parciales.

    El campo `stock` NO se edita aquí — usar `POST /{producto_id}/ajuste-stock`
    para mantener el ledger de movimientos consistente.
    """
    producto = db.query(Producto).filter(
        Producto.id        == producto_id,
        Producto.tenant_id == user["tenant_id"],
    ).first()

    if not producto:
        raise HTTPException(status_code=404, detail="Producto no encontrado")

    if data.nombre is not None:
        producto.nombre = data.nombre
    if data.precio is not None:
        producto.precio = data.precio
    if data.costo is not None:
        producto.costo = float(data.costo)
    if data.insumos is not None:
        producto.insumos = data.insumos
    if data.descripcion is not None:
        producto.descripcion = data.descripcion
    if data.sku is not None:
        producto.sku = data.sku.strip() or None
    if data.imagen_url is not None:
        producto.imagen_url = data.imagen_url or None
    if data.categoria is not None:
        producto.categoria = data.categoria
        producto.categoria_id = _resolver_categoria_id(
            user["tenant_id"], producto.sucursal_id, data.categoria, db
        )
    if data.stock_minimo is not None:
        producto.stock_minimo = float(data.stock_minimo)
    if data.unidad_medida is not None:
        producto.unidad_medida = data.unidad_medida
    if data.activo is not None:
        producto.activo = bool(data.activo)

    db.commit()
    db.refresh(producto)
    return producto


# ── Inventario: ajuste manual de stock + historial ─────────────────────
@router.post("/{producto_id}/ajuste-stock", response_model=ProductoOut)
def ajustar_stock(
    producto_id: str,
    data: AjusteStockRequest,
    user: dict    = Depends(get_current_user),
    db:   Session = Depends(get_db),
):
    """Ajusta el stock de un producto y registra el movimiento en el ledger.

    Tipos:
      - 'entrada' / 'devolucion': suma al stock.
      - 'salida' / 'merma':       resta del stock.
      - 'ajuste':                 fija el stock al valor `stock_final` provisto
                                   (la diferencia se calcula automáticamente).
    """
    producto = db.query(Producto).filter(
        Producto.id        == producto_id,
        Producto.tenant_id == user["tenant_id"],
    ).first()

    if not producto:
        raise HTTPException(status_code=404, detail="Producto no encontrado")

    stock_antes = float(producto.stock or 0.0)

    # Calcular delta firmado según tipo
    if data.tipo in ("entrada", "devolucion"):
        delta = abs(data.cantidad)
    elif data.tipo in ("salida", "merma"):
        delta = -abs(data.cantidad)
    elif data.tipo == "ajuste":
        if data.stock_final is None:
            raise HTTPException(
                status_code=422,
                detail="Para tipo='ajuste' debes enviar `stock_final`.",
            )
        if data.stock_final < 0:
            raise HTTPException(status_code=422, detail="stock_final no puede ser negativo")
        delta = float(data.stock_final) - stock_antes
    else:
        raise HTTPException(status_code=422, detail=f"tipo '{data.tipo}' no soportado")

    stock_despues = round(stock_antes + delta, 4)
    if stock_despues < 0:
        raise HTTPException(
            status_code=422,
            detail=f"El movimiento dejaría stock negativo ({stock_despues}). Operación bloqueada.",
        )

    producto.stock = stock_despues

    db.add(MovimientoInventario(
        tenant_id     = user["tenant_id"],
        sucursal_id   = producto.sucursal_id,
        producto_id   = producto.id,
        tipo          = data.tipo,
        cantidad      = delta,
        stock_antes   = stock_antes,
        stock_despues = stock_despues,
        motivo        = data.motivo,
        referencia_id = None,
        usuario_id    = user.get("usuario_id"),
    ))
    db.commit()
    db.refresh(producto)
    return producto


@router.get("/{producto_id}/movimientos", response_model=list[MovimientoInventarioOut])
def listar_movimientos(
    producto_id: str,
    limit: int = Query(100, ge=1, le=500),
    user: dict    = Depends(get_current_user),
    db:   Session = Depends(get_db),
):
    """Devuelve el historial de movimientos de stock de un producto (más recientes primero)."""
    producto = db.query(Producto).filter(
        Producto.id        == producto_id,
        Producto.tenant_id == user["tenant_id"],
    ).first()
    if not producto:
        raise HTTPException(status_code=404, detail="Producto no encontrado")

    movimientos = (
        db.query(MovimientoInventario)
        .filter(
            MovimientoInventario.producto_id == producto_id,
            MovimientoInventario.tenant_id   == user["tenant_id"],
        )
        .order_by(MovimientoInventario.fecha.desc())
        .limit(limit)
        .all()
    )

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


@router.delete("/{producto_id}", status_code=204)
def eliminar_producto(
    producto_id: str,
    user: dict    = Depends(get_current_user),
    db:   Session = Depends(get_db),
):
    """Soft-delete: marca activo=False."""
    producto = db.query(Producto).filter(
        Producto.id        == producto_id,
        Producto.tenant_id == user["tenant_id"],
    ).first()

    if not producto:
        raise HTTPException(status_code=404, detail="Producto no encontrado")

    producto.activo = False
    db.commit()
