"""
backend.ml.data_extractor — Construye series temporales para entrenamiento.

Las funciones aquí leen `MovimientoInventario` y `Orden`+`OrdenItem` para producir
una serie diaria por (producto_id, sucursal_id) que el forecaster pueda consumir.

Decisión clave:
  Usamos `MovimientoInventario.tipo == 'venta'` como fuente de verdad. Es más
  fiable que `OrdenItem` porque ya está agregada a nivel de producto y filtra
  ventas anuladas (las anulaciones generan 'devolucion' que NO entra como venta).
"""
from __future__ import annotations

from dataclasses import dataclass
from datetime import date, datetime, timedelta, timezone
from typing import Iterable

from sqlalchemy import func
from sqlalchemy.orm import Session

from backend.models.orm import MovimientoInventario, Producto


@dataclass
class SerieDiaria:
    """Serie temporal de demanda diaria para un producto.

    `valores[i]` = unidades vendidas el día `fechas[i]` (puede ser 0).
    Las series están **densificadas**: no faltan días intermedios.
    """
    producto_id: str
    sucursal_id: str
    fechas:      list[date]   # ordenadas asc
    valores:     list[float]

    @property
    def n(self) -> int:
        return len(self.fechas)

    @property
    def media(self) -> float:
        return sum(self.valores) / self.n if self.n else 0.0

    @property
    def total(self) -> float:
        return float(sum(self.valores))


def extraer_serie_diaria(
    db: Session,
    *,
    producto_id: str,
    sucursal_id: str,
    desde: date,
    hasta: date,
) -> SerieDiaria:
    """Demanda diaria de un producto entre [desde, hasta] (inclusive).

    Retorna una serie densa: si no hubo ventas un día, ese día está con 0.0.
    """
    # Sumamos solo movimientos de venta (cantidad es negativa → tomamos abs)
    rows = (
        db.query(
            func.date(MovimientoInventario.fecha).label("d"),
            func.sum(MovimientoInventario.cantidad).label("cant"),
        )
        .filter(
            MovimientoInventario.producto_id == producto_id,
            MovimientoInventario.sucursal_id == sucursal_id,
            MovimientoInventario.tipo == "venta",
            MovimientoInventario.fecha >= datetime.combine(desde, datetime.min.time(), tzinfo=timezone.utc),
            MovimientoInventario.fecha <= datetime.combine(hasta, datetime.max.time(), tzinfo=timezone.utc),
        )
        .group_by(func.date(MovimientoInventario.fecha))
        .all()
    )

    # Map: date_str -> cantidad (positivo)
    por_dia: dict[str, float] = {}
    for d, cant in rows:
        # `d` puede venir como str o date dependiendo del backend (sqlite=str)
        clave = d if isinstance(d, str) else d.isoformat()
        por_dia[clave] = -float(cant or 0.0)  # ventas son negativas, las invertimos

    fechas: list[date] = []
    valores: list[float] = []
    cursor = desde
    while cursor <= hasta:
        fechas.append(cursor)
        valores.append(por_dia.get(cursor.isoformat(), 0.0))
        cursor += timedelta(days=1)

    return SerieDiaria(
        producto_id = producto_id,
        sucursal_id = sucursal_id,
        fechas      = fechas,
        valores     = valores,
    )


def listar_productos_entrenables(
    db: Session,
    *,
    tenant_id: int,
    sucursal_id: str | None = None,
    min_dias_con_ventas: int = 14,
) -> list[Producto]:
    """Productos con suficientes ventas históricas para entrenar.

    Filtra productos del tenant con al menos `min_dias_con_ventas` días con
    al menos una venta registrada. Esto descarta productos nuevos sin
    historial significativo.
    """
    query = (
        db.query(Producto.id, Producto)
          .join(
              MovimientoInventario,
              (MovimientoInventario.producto_id == Producto.id) &
              (MovimientoInventario.tipo == "venta"),
          )
          .filter(Producto.tenant_id == tenant_id, Producto.activo == True)
    )
    if sucursal_id:
        query = query.filter(Producto.sucursal_id == sucursal_id)

    rows = (
        query.add_columns(
            func.count(func.distinct(func.date(MovimientoInventario.fecha))).label("dias_venta")
        )
        .group_by(Producto.id)
        .having(func.count(func.distinct(func.date(MovimientoInventario.fecha))) >= min_dias_con_ventas)
        .all()
    )

    # rows = [(producto_id, Producto, dias_venta), ...]
    return [r[1] for r in rows]


def iter_productos_a_entrenar(
    db: Session, *, tenant_id: int, sucursal_id: str | None = None,
    min_dias_con_ventas: int = 14,
) -> Iterable[Producto]:
    """Generator-friendly version (idéntico a `listar_productos_entrenables`)."""
    yield from listar_productos_entrenables(
        db,
        tenant_id=tenant_id,
        sucursal_id=sucursal_id,
        min_dias_con_ventas=min_dias_con_ventas,
    )
