"""
backend.ml.forecasting — Fachada principal del módulo.

Expone `train_producto()` que entrena un modelo para un (producto, sucursal)
dado, persiste las predicciones en `forecast_series` + metadata en
`ml_model_metadata`, y devuelve un `ForecastResult`.

Decisión de modelo:
  - Si Prophet está disponible Y `prefer_prophet=True` Y la serie tiene
    >= 60 días con datos → usa Prophet.
  - En cualquier otro caso → baseline.

Prophet se importa lazy para no romper si no está instalado en el runtime.
"""
from __future__ import annotations

import logging
from dataclasses import dataclass, field
from datetime import date, datetime, timedelta, timezone
from typing import Optional

from sqlalchemy.orm import Session

from backend.models.orm import (
    ForecastSerie,
    MlModelMetadata,
    Producto,
)
from backend.ml.baseline import (
    BaselineModel,
    entrenar_baseline,
    predecir_horizonte,
)
from backend.ml.data_extractor import extraer_serie_diaria

logger = logging.getLogger("tizon.ml")

# ─────────────────────────────────────────────────────────────────────────
#  PROPHET DETECTION (lazy)
# ─────────────────────────────────────────────────────────────────────────
def _check_prophet() -> bool:
    try:
        import prophet  # noqa: F401
        return True
    except Exception:
        return False


PROPHET_AVAILABLE = _check_prophet()


# ─────────────────────────────────────────────────────────────────────────
#  RESULT TYPES
# ─────────────────────────────────────────────────────────────────────────
@dataclass
class ForecastResult:
    """Resultado del entrenamiento + predicción de un producto."""
    producto_id:    str
    sucursal_id:    str
    modelo_tipo:    str
    samples:        int
    horizonte_dias: int
    rmse:           float
    mae:            float
    mape:           Optional[float]
    demanda_media:  float
    puntos:         list[tuple[date, float, float, float]] = field(default_factory=list)
    # ↑ (fecha, demanda, intervalo_inf, intervalo_sup)


# ─────────────────────────────────────────────────────────────────────────
#  TRAIN
# ─────────────────────────────────────────────────────────────────────────
def train_producto(
    db: Session,
    producto: Producto,
    *,
    horizonte_dias: int = 14,
    historial_dias: int = 90,
    prefer_prophet: bool = False,
    persist: bool = True,
    hoy: Optional[date] = None,
) -> Optional[ForecastResult]:
    """Entrena un modelo para `producto` y persiste predicciones.

    Args:
        db: sesión SQLAlchemy
        producto: ORM `Producto` a entrenar
        horizonte_dias: cuántos días futuros predecir
        historial_dias: cuántos días de historia usar para entrenar
        prefer_prophet: si True y prophet está disponible, lo usa
        persist: si True, escribe a `forecast_series` + `ml_model_metadata`
        hoy: fecha de referencia (default: today UTC). Útil para testing.

    Returns:
        `ForecastResult` con las predicciones, o None si no hay datos suficientes.
    """
    hoy = hoy or datetime.now(timezone.utc).date()
    desde = hoy - timedelta(days=historial_dias)
    hasta = hoy - timedelta(days=1)  # ayer (excluimos hoy porque está incompleto)

    serie = extraer_serie_diaria(
        db,
        producto_id=producto.id,
        sucursal_id=producto.sucursal_id,
        desde=desde,
        hasta=hasta,
    )

    # Cuántos días tienen al menos 1 venta
    dias_con_venta = sum(1 for v in serie.valores if v > 0)
    if dias_con_venta < 7:
        logger.info(
            "Producto %s saltado: solo %d días con ventas (mínimo 7)",
            producto.id, dias_con_venta,
        )
        return None

    use_prophet = prefer_prophet and PROPHET_AVAILABLE and dias_con_venta >= 60
    modelo_tipo = "prophet" if use_prophet else "baseline"

    if use_prophet:
        try:
            from backend.ml.prophet_model import entrenar_prophet, predecir_prophet  # type: ignore
            model = entrenar_prophet(serie.fechas, serie.valores)
            puntos = predecir_prophet(model, desde=hoy, horizonte=horizonte_dias)
            rmse, mae, mape = model.rmse, model.mae, model.mape
            demanda_media = serie.media
        except Exception as e:
            logger.warning("Prophet falló para %s, fallback a baseline: %s", producto.id, e)
            modelo_tipo = "baseline"
            base_m = entrenar_baseline(serie.fechas, serie.valores)
            puntos = predecir_horizonte(base_m, desde=hoy, horizonte=horizonte_dias)
            rmse, mae, mape = base_m.rmse, base_m.mae, base_m.mape
            demanda_media = serie.media
    else:
        base_m: BaselineModel = entrenar_baseline(serie.fechas, serie.valores)
        puntos = predecir_horizonte(base_m, desde=hoy, horizonte=horizonte_dias)
        rmse, mae, mape = base_m.rmse, base_m.mae, base_m.mape
        demanda_media = serie.media

    result = ForecastResult(
        producto_id    = producto.id,
        sucursal_id    = producto.sucursal_id,
        modelo_tipo    = modelo_tipo,
        samples        = serie.n,
        horizonte_dias = horizonte_dias,
        rmse           = rmse,
        mae            = mae,
        mape           = mape,
        demanda_media  = demanda_media,
        puntos         = puntos,
    )

    if persist:
        _persistir_forecast(db, producto, result)

    return result


def _persistir_forecast(db: Session, producto: Producto, result: ForecastResult) -> None:
    """Guarda metadata + reemplaza forecast_series del producto."""
    # 1) Borrar forecasts viejos del producto
    db.query(ForecastSerie).filter_by(producto_id=producto.id).delete()

    # 2) Insertar nuevos puntos
    for fecha, demanda, inf, sup in result.puntos:
        db.add(ForecastSerie(
            tenant_id     = producto.tenant_id,
            sucursal_id   = producto.sucursal_id,
            producto_id   = producto.id,
            fecha_target  = datetime.combine(fecha, datetime.min.time(), tzinfo=timezone.utc),
            demanda       = round(demanda, 4),
            intervalo_inf = round(inf, 4),
            intervalo_sup = round(sup, 4),
            modelo_tipo   = result.modelo_tipo,
        ))

    # 3) Upsert metadata
    meta = (
        db.query(MlModelMetadata)
          .filter_by(
              producto_id = producto.id,
              sucursal_id = producto.sucursal_id,
              modelo_tipo = result.modelo_tipo,
          )
          .first()
    )
    if meta is None:
        meta = MlModelMetadata(
            tenant_id   = producto.tenant_id,
            sucursal_id = producto.sucursal_id,
            producto_id = producto.id,
            modelo_tipo = result.modelo_tipo,
        )
        db.add(meta)

    meta.samples       = result.samples
    meta.rmse          = round(result.rmse, 4)
    meta.mae           = round(result.mae, 4)
    meta.mape          = round(result.mape, 4) if result.mape is not None else None
    meta.demanda_media = round(result.demanda_media, 4)
    meta.parametros    = {"horizonte_dias": result.horizonte_dias}
    meta.entrenado_en  = datetime.now(timezone.utc)
