"""
backend.ml.train — Orquesta entrenamiento masivo (todos los productos de un tenant).

Función principal `train_tenant` itera los productos elegibles, entrena cada
uno, persiste forecasts y genera alertas. Devuelve un resumen útil para
mostrar en el panel admin o para el log del cron.

Pensado para ser llamado:
  - Desde un cron diario (`scripts/train_models.py`)
  - Desde el endpoint `POST /api/v3/ml/train` (admin only) para refresh manual
"""
from __future__ import annotations

import logging
import time
from dataclasses import dataclass
from typing import Optional

from sqlalchemy.orm import Session

from backend.ml.alerts import (
    generar_alertas_para_producto,
    generar_alertas_globales,
    limpiar_alertas_expiradas,
)
from backend.ml.data_extractor import listar_productos_entrenables
from backend.ml.forecasting import ForecastResult, train_producto

logger = logging.getLogger("tizon.ml")


@dataclass
class TrainSummary:
    tenant_id:           int
    productos_evaluados: int
    modelos_entrenados:  int
    modelos_omitidos:    int
    forecasts_generados: int
    alertas_creadas:     int
    duracion_segundos:   float
    modelo_tipo:         str
    errores:             list[str]


def train_tenant(
    db: Session,
    tenant_id: int,
    *,
    horizonte_dias: int = 14,
    historial_dias: int = 90,
    prefer_prophet: bool = False,
    sucursal_id: Optional[str] = None,
) -> TrainSummary:
    """Entrena modelos para todos los productos elegibles del tenant.

    Pasos:
      1. Listar productos con suficiente historial.
      2. Para cada uno, llamar `train_producto` (persiste forecasts + metadata).
      3. Generar alertas por producto.
      4. Generar alertas a nivel tenant (productos estrella).
      5. Limpiar alertas expiradas.
      6. Commit final.
    """
    t0 = time.time()
    productos = listar_productos_entrenables(
        db, tenant_id=tenant_id, sucursal_id=sucursal_id, min_dias_con_ventas=14,
    )

    productos_evaluados = len(productos)
    entrenados = 0
    omitidos = 0
    forecasts_generados = 0
    alertas_creadas = 0
    errores: list[str] = []
    modelo_tipo = "baseline"
    productos_por_id: dict[str, object] = {}
    resultados: list[ForecastResult] = []

    for p in productos:
        try:
            r = train_producto(
                db, p,
                horizonte_dias = horizonte_dias,
                historial_dias = historial_dias,
                prefer_prophet = prefer_prophet,
                persist        = True,
            )
            if r is None:
                omitidos += 1
                continue
            entrenados += 1
            forecasts_generados += len(r.puntos)
            modelo_tipo = r.modelo_tipo  # último visto
            resultados.append(r)
            productos_por_id[p.id] = p

            alertas = generar_alertas_para_producto(db, p, r, persist=True)
            alertas_creadas += len(alertas)
        except Exception as exc:
            errores.append(f"{p.id}: {exc}")
            logger.exception("Error entrenando producto %s", p.id)

    # Alertas cross-producto
    try:
        globales = generar_alertas_globales(
            db, tenant_id,
            forecasts=resultados,
            productos_por_id=productos_por_id,  # type: ignore[arg-type]
            persist=True,
        )
        alertas_creadas += len(globales)
    except Exception as exc:
        errores.append(f"alertas_globales: {exc}")
        logger.exception("Error generando alertas globales para tenant %d", tenant_id)

    # Limpiar expiradas
    try:
        eliminadas = limpiar_alertas_expiradas(db, tenant_id)
        if eliminadas > 0:
            logger.info("Tenant %d: %d alertas expiradas eliminadas", tenant_id, eliminadas)
    except Exception as exc:
        errores.append(f"limpiar_expiradas: {exc}")

    db.commit()

    return TrainSummary(
        tenant_id           = tenant_id,
        productos_evaluados = productos_evaluados,
        modelos_entrenados  = entrenados,
        modelos_omitidos    = omitidos,
        forecasts_generados = forecasts_generados,
        alertas_creadas     = alertas_creadas,
        duracion_segundos   = round(time.time() - t0, 2),
        modelo_tipo         = modelo_tipo,
        errores             = errores,
    )
