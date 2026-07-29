"""
routes/ml.py — Endpoints públicos del módulo de Machine Learning.

Todos los endpoints requieren autenticación. Algunos requieren rol manager+
para operaciones costosas (training).

Rutas:
  GET    /api/v3/ml/forecast/{producto_id}     → predicción del producto
  GET    /api/v3/ml/forecasts                  → forecasts agregados de la sucursal
  GET    /api/v3/ml/alerts                     → alertas inteligentes (no leídas)
  PATCH  /api/v3/ml/alerts/{id}/acknowledge    → marca alerta como leída
  GET    /api/v3/ml/restock-suggestions        → sugerencias de reorden
  POST   /api/v3/ml/train                      → entrena modelos (manager+)
  GET    /api/v3/ml/status                     → metadata de modelos del tenant
"""
from __future__ import annotations

from datetime import datetime, timezone
from typing import Optional

from fastapi import APIRouter, BackgroundTasks, Depends, HTTPException, Query
from sqlalchemy import func
from sqlalchemy.orm import Session

from backend.auth_v3 import Rol, get_current_usuario, requiere_rol
from backend.db.session import get_db
from backend.ml import PROPHET_AVAILABLE, train_tenant
from backend.models.orm import (
    ForecastSerie,
    MlAlerta,
    MlModelMetadata,
    Producto,
    Sucursal,
)
from backend.schemas import (
    ForecastPunto,
    ForecastResponse,
    MlAlertaOut,
    RestockSugerencia,
    TrainResultOut,
)

router = APIRouter(prefix="/api/v3/ml", tags=["ML / Forecasting"])


# ─────────────────────────────────────────────────────────────────────────
#  GET /forecast/{producto_id}
# ─────────────────────────────────────────────────────────────────────────
@router.get("/forecast/{producto_id}", response_model=ForecastResponse)
def get_forecast_producto(
    producto_id: str,
    user: dict = Depends(get_current_usuario),
    db:   Session = Depends(get_db),
):
    """Predicción de demanda para un producto específico.

    Devuelve el forecast persistido. Si no existe, sugiere entrenar primero
    con `POST /api/v3/ml/train`.
    """
    producto = (
        db.query(Producto)
          .filter_by(id=producto_id, tenant_id=user["tenant_id"])
          .first()
    )
    if not producto:
        raise HTTPException(status_code=404, detail="Producto no encontrado.")

    puntos_db = (
        db.query(ForecastSerie)
          .filter_by(producto_id=producto_id, tenant_id=user["tenant_id"])
          .order_by(ForecastSerie.fecha_target.asc())
          .all()
    )
    if not puntos_db:
        raise HTTPException(
            status_code=404,
            detail=(
                "No hay predicción disponible. Ejecuta POST /api/v3/ml/train "
                "para generar modelos."
            ),
        )

    meta = (
        db.query(MlModelMetadata)
          .filter_by(producto_id=producto_id, sucursal_id=producto.sucursal_id)
          .order_by(MlModelMetadata.entrenado_en.desc())
          .first()
    )

    puntos_out = [
        ForecastPunto(
            fecha         = p.fecha_target.date().isoformat(),
            demanda       = p.demanda,
            intervalo_inf = p.intervalo_inf,
            intervalo_sup = p.intervalo_sup,
        )
        for p in puntos_db
    ]
    demanda_total = sum(p.demanda for p in puntos_out)

    return ForecastResponse(
        producto_id     = producto.id,
        producto_nombre = producto.nombre,
        sucursal_id     = producto.sucursal_id,
        modelo_tipo     = meta.modelo_tipo if meta else (puntos_db[0].modelo_tipo if puntos_db else "baseline"),
        horizonte_dias  = len(puntos_db),
        demanda_total   = round(demanda_total, 2),
        rmse            = meta.rmse if meta else None,
        entrenado_en    = meta.entrenado_en.isoformat() if meta and meta.entrenado_en else None,
        puntos          = puntos_out,
    )


# ─────────────────────────────────────────────────────────────────────────
#  GET /alerts
# ─────────────────────────────────────────────────────────────────────────
@router.get("/alerts", response_model=list[MlAlertaOut])
def listar_alertas(
    sucursal_id: Optional[str] = Query(None),
    incluir_leidas: bool = Query(False),
    severidad: Optional[str] = Query(None, pattern="^(info|warning|critical)$"),
    tipo: Optional[str] = Query(None),
    limit: int = Query(50, ge=1, le=200),
    user: dict = Depends(get_current_usuario),
    db:   Session = Depends(get_db),
):
    """Lista alertas inteligentes generadas por ML."""
    query = db.query(MlAlerta).filter_by(tenant_id=user["tenant_id"])
    if not incluir_leidas:
        query = query.filter_by(leida=False)
    if sucursal_id:
        query = query.filter_by(sucursal_id=sucursal_id)
    if severidad:
        query = query.filter_by(severidad=severidad)
    if tipo:
        query = query.filter_by(tipo=tipo)

    # Ordenar: críticas primero, luego warnings, luego info; dentro, más recientes primero
    severidad_order = {"critical": 0, "warning": 1, "info": 2}
    alertas = query.order_by(MlAlerta.creada_en.desc()).limit(limit).all()
    alertas.sort(key=lambda a: (severidad_order.get(a.severidad, 9), -a.creada_en.timestamp()))

    return [
        MlAlertaOut(
            id            = a.id,
            tipo          = a.tipo,
            severidad     = a.severidad,
            titulo        = a.titulo,
            mensaje       = a.mensaje,
            recomendacion = a.recomendacion,
            producto_id   = a.producto_id,
            sucursal_id   = a.sucursal_id,
            metadata      = a.metadata_json,
            leida         = bool(a.leida),
            creada_en     = a.creada_en.isoformat() if a.creada_en else "",
        )
        for a in alertas
    ]


@router.patch("/alerts/{alerta_id}/acknowledge", response_model=MlAlertaOut)
def acknowledge_alerta(
    alerta_id: int,
    user: dict = Depends(get_current_usuario),
    db:   Session = Depends(get_db),
):
    """Marca una alerta como leída."""
    a = (
        db.query(MlAlerta)
          .filter_by(id=alerta_id, tenant_id=user["tenant_id"])
          .first()
    )
    if not a:
        raise HTTPException(status_code=404, detail="Alerta no encontrada.")
    a.leida = True
    db.commit()
    db.refresh(a)
    return MlAlertaOut(
        id            = a.id,
        tipo          = a.tipo,
        severidad     = a.severidad,
        titulo        = a.titulo,
        mensaje       = a.mensaje,
        recomendacion = a.recomendacion,
        producto_id   = a.producto_id,
        sucursal_id   = a.sucursal_id,
        metadata      = a.metadata_json,
        leida         = bool(a.leida),
        creada_en     = a.creada_en.isoformat() if a.creada_en else "",
    )


# ─────────────────────────────────────────────────────────────────────────
#  GET /restock-suggestions
# ─────────────────────────────────────────────────────────────────────────
@router.get("/restock-suggestions", response_model=list[RestockSugerencia])
def restock_suggestions(
    sucursal_id: Optional[str] = Query(None),
    horizonte_dias: int = Query(14, ge=1, le=60),
    user: dict = Depends(get_current_usuario),
    db:   Session = Depends(get_db),
):
    """Sugerencias de reorden basadas en forecast vs stock actual.

    Cruza productos con forecast persistido. Para cada uno calcula:
      - demanda_proyectada (suma del forecast en el horizonte)
      - dias_cobertura (stock_actual / demanda_diaria_media)
      - cantidad_sugerida (cubrir 14 días + buffer 30%)
      - urgencia (basada en dias_cobertura)
    """
    # Productos del tenant con forecast disponible
    query = db.query(Producto, Sucursal).join(
        Sucursal, Producto.sucursal_id == Sucursal.id, isouter=True,
    ).filter(
        Producto.tenant_id == user["tenant_id"],
        Producto.activo    == True,
    )
    if sucursal_id:
        query = query.filter(Producto.sucursal_id == sucursal_id)

    productos = query.all()
    sugerencias: list[RestockSugerencia] = []

    for producto, sucursal in productos:
        # Suma de demanda proyectada en el horizonte
        demanda_total = (
            db.query(func.sum(ForecastSerie.demanda))
              .filter_by(producto_id=producto.id)
              .scalar()
        ) or 0.0
        demanda_total = float(demanda_total)
        if demanda_total <= 0:
            continue  # producto sin forecast → ignorar

        stock_actual = float(producto.stock or 0.0)
        demanda_diaria = demanda_total / horizonte_dias if horizonte_dias > 0 else 0.0
        dias_cobertura = stock_actual / demanda_diaria if demanda_diaria > 0 else None

        # Cantidad sugerida: cubrir el horizonte + buffer 30%
        cantidad_sugerida = max(0.0, round(demanda_total * 1.3 - stock_actual, 1))

        # Urgencia
        if stock_actual <= 0:
            urgencia = "critica"
        elif dias_cobertura is not None and dias_cobertura <= 3:
            urgencia = "critica"
        elif dias_cobertura is not None and dias_cobertura <= 7:
            urgencia = "alta"
        elif dias_cobertura is not None and dias_cobertura <= 14:
            urgencia = "media"
        else:
            urgencia = "baja"

        # Solo sugerimos si hay algo que pedir
        if cantidad_sugerida <= 0 and urgencia == "baja":
            continue

        sugerencias.append(RestockSugerencia(
            producto_id        = producto.id,
            producto_nombre    = producto.nombre,
            sucursal_id        = producto.sucursal_id,
            sucursal_nombre    = sucursal.nombre if sucursal else None,
            stock_actual       = stock_actual,
            demanda_proyectada = round(demanda_total, 2),
            dias_cobertura     = round(dias_cobertura, 1) if dias_cobertura is not None else None,
            cantidad_sugerida  = cantidad_sugerida,
            urgencia           = urgencia,
        ))

    # Ordenar: critica → alta → media → baja
    orden = {"critica": 0, "alta": 1, "media": 2, "baja": 3}
    sugerencias.sort(key=lambda s: (orden.get(s.urgencia, 9), -(s.demanda_proyectada or 0)))
    return sugerencias


# ─────────────────────────────────────────────────────────────────────────
#  POST /train  (manager+)
# ─────────────────────────────────────────────────────────────────────────
@router.post("/train", response_model=TrainResultOut, status_code=200)
def trigger_train(
    background_tasks: BackgroundTasks,
    sucursal_id: Optional[str] = Query(None),
    horizonte_dias: int = Query(14, ge=1, le=60),
    historial_dias: int = Query(90, ge=14, le=365),
    sincrono: bool = Query(True, description="Si False, ejecuta en background y devuelve estimación."),
    user: dict = Depends(requiere_rol(Rol.MANAGER)),
    db:   Session = Depends(get_db),
):
    """Lanza el entrenamiento de modelos para el tenant del usuario.

    Modo síncrono (default): bloquea hasta terminar y devuelve métricas reales.
    Modo asíncrono: encola y devuelve resultado parcial. Útil cuando hay muchos
    productos y el frontend ya tiene polling sobre `/status`.
    """
    if sincrono:
        summary = train_tenant(
            db, user["tenant_id"],
            horizonte_dias = horizonte_dias,
            historial_dias = historial_dias,
            prefer_prophet = PROPHET_AVAILABLE,
            sucursal_id    = sucursal_id,
        )
        return TrainResultOut(
            tenant_id           = summary.tenant_id,
            productos_evaluados = summary.productos_evaluados,
            modelos_entrenados  = summary.modelos_entrenados,
            modelos_omitidos    = summary.modelos_omitidos,
            forecasts_generados = summary.forecasts_generados,
            alertas_creadas     = summary.alertas_creadas,
            duracion_segundos   = summary.duracion_segundos,
            modelo_tipo         = summary.modelo_tipo,
        )
    else:
        # En modo asíncrono lanzamos en background. Para retornar al usuario
        # algo útil ahora, aproximamos los productos.
        from backend.ml.data_extractor import listar_productos_entrenables
        productos = listar_productos_entrenables(
            db, tenant_id=user["tenant_id"], sucursal_id=sucursal_id,
        )

        def _bg():
            from backend.db.session import SessionLocal
            session = SessionLocal()
            try:
                train_tenant(
                    session, user["tenant_id"],
                    horizonte_dias=horizonte_dias,
                    historial_dias=historial_dias,
                    prefer_prophet=PROPHET_AVAILABLE,
                    sucursal_id=sucursal_id,
                )
            finally:
                session.close()

        background_tasks.add_task(_bg)
        return TrainResultOut(
            tenant_id           = user["tenant_id"],
            productos_evaluados = len(productos),
            modelos_entrenados  = 0,
            modelos_omitidos    = 0,
            forecasts_generados = 0,
            alertas_creadas     = 0,
            duracion_segundos   = 0.0,
            modelo_tipo         = "prophet" if PROPHET_AVAILABLE else "baseline",
        )


# ─────────────────────────────────────────────────────────────────────────
#  GET /status
# ─────────────────────────────────────────────────────────────────────────
@router.get("/status")
def status_modelos(
    user: dict = Depends(get_current_usuario),
    db:   Session = Depends(get_db),
):
    """Estado del módulo ML para el tenant."""
    metas = (
        db.query(MlModelMetadata)
          .filter_by(tenant_id=user["tenant_id"])
          .order_by(MlModelMetadata.entrenado_en.desc())
          .all()
    )
    n_forecasts = (
        db.query(func.count(ForecastSerie.id))
          .filter_by(tenant_id=user["tenant_id"])
          .scalar()
    ) or 0
    n_alertas = (
        db.query(func.count(MlAlerta.id))
          .filter_by(tenant_id=user["tenant_id"], leida=False)
          .scalar()
    ) or 0

    ultimo_entrenamiento = metas[0].entrenado_en.isoformat() if metas and metas[0].entrenado_en else None

    return {
        "prophet_disponible":      PROPHET_AVAILABLE,
        "modelos_entrenados":      len(metas),
        "forecasts_persistidos":   n_forecasts,
        "alertas_no_leidas":       n_alertas,
        "ultimo_entrenamiento":    ultimo_entrenamiento,
        "rmse_promedio":           round(sum((m.rmse or 0) for m in metas) / len(metas), 4) if metas else None,
        "mape_promedio":           (
            round(sum((m.mape or 0) for m in metas if m.mape is not None) /
                  max(1, sum(1 for m in metas if m.mape is not None)), 2)
            if any(m.mape is not None for m in metas) else None
        ),
    }
