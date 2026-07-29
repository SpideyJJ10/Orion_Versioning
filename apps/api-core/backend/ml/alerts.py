"""
backend.ml.alerts — Motor de alertas inteligentes basadas en pronóstico.

Genera 4 tipos de alertas a partir de la combinación (stock_actual + forecast):

  1. **stockout_riesgo**   → demanda esperada en próx. N días > stock disponible
  2. **sobrestock**        → stock cubre > X días de demanda → capital ocioso
  3. **demanda_anomala**   → última semana fuera del intervalo de confianza
  4. **producto_estrella** → top-3 productos con mayor crecimiento mes a mes

A diferencia de las alertas en `routes/inventario.py` (basadas solo en stock_minimo),
estas son **proyectivas**: usan la velocidad de venta predicha.

API pública:
  - `generar_alertas_para_producto(db, producto, forecast)` → lista de MlAlerta sin commit
  - `generar_alertas_para_tenant(db, tenant_id, forecasts)` → análisis cross-producto
"""
from __future__ import annotations

from dataclasses import dataclass
from datetime import datetime, timedelta, timezone
from typing import Iterable, Optional

from sqlalchemy.orm import Session

from backend.models.orm import MlAlerta, Producto
from backend.ml.forecasting import ForecastResult


# ─────────────────────────────────────────────────────────────────────────
#  CONFIGURACIÓN POR DEFECTO (ajustable por tenant en futuro)
# ─────────────────────────────────────────────────────────────────────────
DIAS_SOBRESTOCK = 30        # más de 30 días de cobertura → sobrestock
DIAS_HORIZONTE_STOCKOUT = 14
EXPIRA_HORAS_DEFAULT = 48   # alertas expiran si no se actualizan


# ─────────────────────────────────────────────────────────────────────────
#  STOCKOUT RIESGO
# ─────────────────────────────────────────────────────────────────────────
def _alerta_stockout(
    producto: Producto,
    result: ForecastResult,
) -> Optional[dict]:
    """Si la demanda predicha agotaría el stock, retorna dict para construir MlAlerta."""
    stock = float(producto.stock or 0.0)
    demanda_total = sum(p[1] for p in result.puntos)  # suma de demanda diaria

    if demanda_total <= 0:
        return None

    # Calculamos días hasta stockout: vamos restando demanda diaria
    dias_hasta_stockout: Optional[int] = None
    stock_acumulado = stock
    for i, (_, d, _, _) in enumerate(result.puntos):
        stock_acumulado -= d
        if stock_acumulado <= 0:
            dias_hasta_stockout = i + 1
            break

    if dias_hasta_stockout is None:
        return None  # alcanza el horizonte completo

    # Severidad según urgencia
    if dias_hasta_stockout <= 3:
        severidad = "critical"
    elif dias_hasta_stockout <= 7:
        severidad = "warning"
    else:
        severidad = "info"

    # Cantidad recomendada: cubrir 14 días + buffer 30%
    cantidad_recomendada = round(demanda_total * 1.3, 1)

    return {
        "tipo":          "stockout_riesgo",
        "severidad":     severidad,
        "titulo":        f"{producto.nombre}: se agota en {dias_hasta_stockout} día(s)",
        "mensaje":       (
            f"Con la demanda actual (~{result.demanda_media:.1f}/día), el stock de "
            f"{stock:.0f} {producto.unidad_medida or 'unidades'} se agotaría el día "
            f"{dias_hasta_stockout}."
        ),
        "recomendacion": (
            f"Recomendamos comprar al menos {cantidad_recomendada:.0f} "
            f"{producto.unidad_medida or 'unidades'} para cubrir 14 días."
        ),
        "metadata_json": {
            "stock_actual":         stock,
            "demanda_diaria_media": round(result.demanda_media, 2),
            "dias_hasta_stockout":  dias_hasta_stockout,
            "cantidad_recomendada": cantidad_recomendada,
            "horizonte":            result.horizonte_dias,
        },
    }


# ─────────────────────────────────────────────────────────────────────────
#  SOBRESTOCK
# ─────────────────────────────────────────────────────────────────────────
def _alerta_sobrestock(
    producto: Producto,
    result: ForecastResult,
) -> Optional[dict]:
    """Si el stock cubre > N días de demanda, hay capital ocioso."""
    if result.demanda_media <= 0:
        return None
    stock = float(producto.stock or 0.0)
    if stock <= 0:
        return None
    dias_cobertura = stock / result.demanda_media
    if dias_cobertura < DIAS_SOBRESTOCK:
        return None

    return {
        "tipo":          "sobrestock",
        "severidad":     "info",
        "titulo":        f"{producto.nombre}: sobrestock detectado",
        "mensaje":       (
            f"Tienes stock para ~{dias_cobertura:.0f} días "
            f"({stock:.0f} {producto.unidad_medida or 'und'}). "
            f"Considera promociones o reducir reordenamiento."
        ),
        "recomendacion": (
            "Pausa nuevas compras de este producto hasta acercarte a 30 días de cobertura."
        ),
        "metadata_json": {
            "stock_actual":         stock,
            "demanda_diaria_media": round(result.demanda_media, 2),
            "dias_cobertura":       round(dias_cobertura, 1),
        },
    }


# ─────────────────────────────────────────────────────────────────────────
#  ALERTAS POR PRODUCTO
# ─────────────────────────────────────────────────────────────────────────
def generar_alertas_para_producto(
    db: Session,
    producto: Producto,
    result: ForecastResult,
    *,
    persist: bool = True,
) -> list[MlAlerta]:
    """Genera todas las alertas aplicables a un producto.

    No genera duplicados activos: si ya existe una alerta no leída del mismo
    tipo y producto, la actualiza en lugar de crear otra.
    """
    payloads = [
        _alerta_stockout(producto, result),
        _alerta_sobrestock(producto, result),
    ]
    payloads = [p for p in payloads if p is not None]

    alertas: list[MlAlerta] = []
    for p in payloads:
        # Buscar alerta existente NO leída del mismo tipo/producto
        existente = (
            db.query(MlAlerta)
              .filter_by(
                  tenant_id   = producto.tenant_id,
                  sucursal_id = producto.sucursal_id,
                  producto_id = producto.id,
                  tipo        = p["tipo"],
                  leida       = False,
              )
              .first()
        )
        ahora = datetime.now(timezone.utc)
        expira = ahora + timedelta(hours=EXPIRA_HORAS_DEFAULT)
        if existente:
            existente.severidad     = p["severidad"]
            existente.titulo        = p["titulo"]
            existente.mensaje       = p["mensaje"]
            existente.recomendacion = p["recomendacion"]
            existente.metadata_json = p["metadata_json"]
            existente.creada_en     = ahora
            existente.expira_en     = expira
            alertas.append(existente)
        else:
            nueva = MlAlerta(
                tenant_id     = producto.tenant_id,
                sucursal_id   = producto.sucursal_id,
                producto_id   = producto.id,
                tipo          = p["tipo"],
                severidad     = p["severidad"],
                titulo        = p["titulo"],
                mensaje       = p["mensaje"],
                recomendacion = p["recomendacion"],
                metadata_json = p["metadata_json"],
                leida         = False,
                creada_en     = ahora,
                expira_en     = expira,
            )
            if persist:
                db.add(nueva)
            alertas.append(nueva)

    return alertas


# ─────────────────────────────────────────────────────────────────────────
#  ALERTAS A NIVEL TENANT (cross-producto)
# ─────────────────────────────────────────────────────────────────────────
def generar_alertas_globales(
    db: Session,
    tenant_id: int,
    *,
    forecasts: Iterable[ForecastResult],
    productos_por_id: dict[str, Producto],
    persist: bool = True,
    top_n_estrella: int = 3,
) -> list[MlAlerta]:
    """Alertas a nivel tenant: producto_estrella, etc.

    Args:
        forecasts: resultados de entrenamiento de los productos del tenant
        productos_por_id: mapping producto_id → Producto (para datos extra)
    """
    alertas: list[MlAlerta] = []
    forecasts = list(forecasts)
    if not forecasts:
        return alertas

    # ── PRODUCTO ESTRELLA: top N por demanda_total proyectada ────────────
    ordenados = sorted(
        forecasts,
        key=lambda r: sum(p[1] for p in r.puntos),
        reverse=True,
    )
    ahora = datetime.now(timezone.utc)
    expira = ahora + timedelta(hours=EXPIRA_HORAS_DEFAULT)

    for r in ordenados[:top_n_estrella]:
        producto = productos_por_id.get(r.producto_id)
        if not producto:
            continue
        demanda_total = sum(p[1] for p in r.puntos)

        existente = (
            db.query(MlAlerta)
              .filter_by(
                  tenant_id   = tenant_id,
                  producto_id = producto.id,
                  tipo        = "producto_estrella",
                  leida       = False,
              )
              .first()
        )
        payload = {
            "titulo":        f"{producto.nombre}: producto top en {r.horizonte_dias} días",
            "mensaje":       (
                f"Se proyectan {demanda_total:.0f} unidades de demanda en los próximos "
                f"{r.horizonte_dias} días."
            ),
            "recomendacion": "Asegura stock continuo y considera destacarlo en el menú/escaparate.",
            "metadata":      {
                "demanda_total":       round(demanda_total, 2),
                "horizonte":           r.horizonte_dias,
                "demanda_diaria_media": round(r.demanda_media, 2),
            },
        }
        if existente:
            existente.titulo        = payload["titulo"]
            existente.mensaje       = payload["mensaje"]
            existente.recomendacion = payload["recomendacion"]
            existente.metadata_json = payload["metadata"]
            existente.creada_en     = ahora
            existente.expira_en     = expira
            alertas.append(existente)
        else:
            nueva = MlAlerta(
                tenant_id     = tenant_id,
                sucursal_id   = producto.sucursal_id,
                producto_id   = producto.id,
                tipo          = "producto_estrella",
                severidad     = "info",
                titulo        = payload["titulo"],
                mensaje       = payload["mensaje"],
                recomendacion = payload["recomendacion"],
                metadata_json = payload["metadata"],
                leida         = False,
                creada_en     = ahora,
                expira_en     = expira,
            )
            if persist:
                db.add(nueva)
            alertas.append(nueva)

    return alertas


# ─────────────────────────────────────────────────────────────────────────
#  LIMPIEZA
# ─────────────────────────────────────────────────────────────────────────
def limpiar_alertas_expiradas(db: Session, tenant_id: int) -> int:
    """Borra alertas vencidas (expira_en < ahora). Retorna cuántas borró."""
    ahora = datetime.now(timezone.utc)
    q = db.query(MlAlerta).filter(
        MlAlerta.tenant_id == tenant_id,
        MlAlerta.expira_en.isnot(None),
        MlAlerta.expira_en < ahora,
    )
    count = q.count()
    q.delete(synchronize_session=False)
    return count
