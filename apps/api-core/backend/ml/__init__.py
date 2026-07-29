"""
backend.ml — Módulo de Machine Learning para forecasting de demanda y alertas.

Diseño de capas
---------------
- `data_extractor`: extrae series temporales de la BD (movimientos de venta agregados por día)
- `baseline`:       modelo simple (mediana móvil + estacionalidad semanal) — sin deps externas
- `prophet_model`:  wrapper opcional sobre Facebook Prophet (lazy import)
- `forecasting`:    fachada que decide qué modelo usar y devuelve `ForecastResult`
- `alerts`:         genera `MlAlerta` a partir de forecasts + stock actual
- `train`:          orquesta el entrenamiento masivo (usado por cron + endpoint admin)

Filosofía
---------
- El módulo es **puro** y no depende de FastAPI; recibe sesiones SQLAlchemy.
- Los modelos no se serializan en BD; se reentrenan barato (segundos por producto).
- Las predicciones SÍ se persisten en `forecast_series` para query rápida.
"""
from backend.ml.forecasting import (
    ForecastResult,
    PROPHET_AVAILABLE,
    train_producto,
)
from backend.ml.train import TrainSummary, train_tenant

__all__ = [
    "ForecastResult",
    "PROPHET_AVAILABLE",
    "TrainSummary",
    "train_producto",
    "train_tenant",
]
