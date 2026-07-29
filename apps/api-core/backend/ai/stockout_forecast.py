"""
Predicción de fecha de quiebre de stock por producto-sucursal.

Modelo: RandomForestRegressor con features temporales (lags + calendario).
Diseñado para correr en el cron nocturno con CPU única.

Documentación: docs/AI_MODULES.md sección 1
"""
from __future__ import annotations

from dataclasses import dataclass
from datetime import date, timedelta
from typing import Optional

# Dependencias opcionales: solo se cargan cuando el módulo se usa realmente.
try:
    import numpy as np
    import pandas as pd
    from sklearn.ensemble import RandomForestRegressor
    from sklearn.metrics import mean_absolute_error
    SKLEARN_OK = True
except ImportError:  # pragma: no cover
    SKLEARN_OK = False


@dataclass
class StockoutForecaster:
    """Predictor de quiebre de stock para un producto-sucursal.

    Uso:
        f = StockoutForecaster("prod-1", "suc-1").fit(df_historico)
        fecha_quiebre, demanda_total = f.predict_stockout(stock_actual=42)
    """

    producto_id: str
    sucursal_id: str
    horizonte_dias: int = 7
    n_estimators: int = 50      # liviano para Free Tier
    random_state: int = 42

    def __post_init__(self) -> None:
        if not SKLEARN_OK:
            raise RuntimeError(
                "scikit-learn/numpy/pandas no están instalados. "
                "Instala: pip install -r requirements-ml.txt"
            )
        self.model_: Optional[RandomForestRegressor] = None
        self.mae_: Optional[float] = None

    # ── Feature engineering ─────────────────────────────────────────
    def _features(self, df: "pd.DataFrame") -> "pd.DataFrame":
        """Espera columnas: fecha (datetime), unidades_vendidas (numeric)."""
        df = df.copy().sort_values("fecha")
        df["fecha"]    = pd.to_datetime(df["fecha"])
        df["dow"]      = df["fecha"].dt.dayofweek
        df["dom"]      = df["fecha"].dt.day
        df["mes"]      = df["fecha"].dt.month
        df["lag_1"]    = df["unidades_vendidas"].shift(1)
        df["lag_7"]    = df["unidades_vendidas"].shift(7)
        df["roll_7"]   = df["unidades_vendidas"].rolling(7, min_periods=1).mean()
        return df.dropna()

    # ── Entrenamiento ───────────────────────────────────────────────
    def fit(self, historico: "pd.DataFrame") -> "StockoutForecaster":
        if len(historico) < 14:
            raise ValueError(
                f"Se necesitan ≥14 días de historia, recibido: {len(historico)}"
            )
        feats = self._features(historico)
        X = feats[["dow", "dom", "mes", "lag_1", "lag_7", "roll_7"]]
        y = feats["unidades_vendidas"]
        self.model_ = RandomForestRegressor(
            n_estimators=self.n_estimators,
            max_depth=8,
            random_state=self.random_state,
            n_jobs=1,
        )
        self.model_.fit(X, y)
        self.mae_ = float(mean_absolute_error(y, self.model_.predict(X)))
        return self

    # ── Predicción ──────────────────────────────────────────────────
    def predict_demand(self, fecha_inicio: date) -> "np.ndarray":
        """Devuelve array de demanda predicha para `horizonte_dias`."""
        if self.model_ is None:
            raise RuntimeError("Modelo no entrenado. Llama .fit() primero.")
        futuras = pd.DataFrame({
            "fecha": [fecha_inicio + timedelta(days=i) for i in range(self.horizonte_dias)]
        })
        futuras["fecha"]   = pd.to_datetime(futuras["fecha"])
        futuras["dow"]     = futuras["fecha"].dt.dayofweek
        futuras["dom"]     = futuras["fecha"].dt.day
        futuras["mes"]     = futuras["fecha"].dt.month
        # Fallback frío: usa MAE como proxy de la media histórica.
        media = (self.mae_ or 1.0) * 2
        futuras["lag_1"]   = media
        futuras["lag_7"]   = media
        futuras["roll_7"]  = media
        return self.model_.predict(
            futuras[["dow", "dom", "mes", "lag_1", "lag_7", "roll_7"]]
        )

    def predict_stockout(
        self,
        stock_actual: float,
        fecha_hoy: Optional[date] = None,
    ) -> tuple[Optional[date], float]:
        """Retorna (fecha_estimada_de_quiebre, demanda_total_horizonte).

        Si stock alcanza para más del horizonte, devuelve (None, demanda).
        """
        fecha_hoy = fecha_hoy or date.today()
        demanda   = self.predict_demand(fecha_hoy)
        acumulada = np.cumsum(demanda)
        idx_quiebre = int(np.searchsorted(acumulada, stock_actual))
        fecha = (
            fecha_hoy + timedelta(days=idx_quiebre)
            if idx_quiebre < self.horizonte_dias
            else None
        )
        return fecha, float(demanda.sum())
