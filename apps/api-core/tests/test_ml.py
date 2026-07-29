"""
tests/test_ml.py — Suite del módulo de Machine Learning.

Cubre:
  • Baseline forecaster (puro, sin BD)
  • Data extractor (lee MovimientoInventario)
  • Forecasting end-to-end (entrena + persiste)
  • Motor de alertas (stockout / sobrestock / producto_estrella)
  • Endpoints HTTP (/api/v3/ml/*)
"""
from __future__ import annotations

from datetime import date, datetime, timedelta, timezone
from typing import Sequence

import pytest

from backend.ml.alerts import (
    generar_alertas_globales,
    generar_alertas_para_producto,
)
from backend.ml.baseline import (
    BaselineModel,
    entrenar_baseline,
    predecir_horizonte,
)
from backend.ml.data_extractor import (
    extraer_serie_diaria,
    listar_productos_entrenables,
)
from backend.ml.forecasting import (
    PROPHET_AVAILABLE,
    train_producto,
)
from backend.ml.train import train_tenant
from backend.models.orm import (
    Categoria,
    ForecastSerie,
    MlAlerta,
    MlModelMetadata,
    MovimientoInventario,
    Producto,
)


# ════════════════════════════════════════════════════════════════════════
#  HELPERS LOCALES
# ════════════════════════════════════════════════════════════════════════
def _crear_producto(
    db_session,
    tenant_owner,
    nombre: str = "Pollo a la plancha",
    *,
    stock: float = 100,
    stock_minimo: float = 10,
    precio: float = 22000,
) -> Producto:
    cat = Categoria(
        tenant_id   = tenant_owner["tenant"].id,
        sucursal_id = tenant_owner["sucursal"].id,
        nombre      = "Fuertes",
    )
    db_session.add(cat)
    db_session.flush()

    p = Producto(
        tenant_id     = tenant_owner["tenant"].id,
        sucursal_id   = tenant_owner["sucursal"].id,
        nombre        = nombre,
        precio        = precio,
        stock         = stock,
        stock_minimo  = stock_minimo,
        categoria     = cat.nombre,
        categoria_id  = cat.id,
        unidad_medida = "unidad",
    )
    db_session.add(p)
    db_session.commit()
    db_session.refresh(p)
    return p


def _seed_ventas_diarias(
    db_session,
    producto: Producto,
    *,
    dias: int = 30,
    cantidad_base: float = 5,
    factor_finde: float = 1.4,
    hoy: date | None = None,
) -> None:
    """Crea N días de movimientos tipo='venta' con patrón día-semana.

    Lun-jue → cantidad_base
    Vie     → cantidad_base * 1.2
    Sáb-dom → cantidad_base * factor_finde
    """
    hoy = hoy or datetime.now(timezone.utc).date()
    for d in range(dias, 0, -1):
        fecha_dia = hoy - timedelta(days=d)
        dow = fecha_dia.weekday()
        if dow == 5 or dow == 6:
            cant = cantidad_base * factor_finde
        elif dow == 4:
            cant = cantidad_base * 1.2
        else:
            cant = cantidad_base

        ts = datetime.combine(fecha_dia, datetime.min.time(), tzinfo=timezone.utc) + timedelta(hours=13)
        db_session.add(MovimientoInventario(
            tenant_id     = producto.tenant_id,
            sucursal_id   = producto.sucursal_id,
            producto_id   = producto.id,
            tipo          = "venta",
            cantidad      = -float(cant),
            stock_antes   = 0,
            stock_despues = 0,
            motivo        = None,
            referencia_id = None,
            usuario_id    = None,
            fecha         = ts,
        ))
    db_session.commit()


# ════════════════════════════════════════════════════════════════════════
#  PARTE 1 — BASELINE PURO (sin BD)
# ════════════════════════════════════════════════════════════════════════
class TestBaselineModel:
    def test_serie_constante_predice_constante(self):
        """Con valores constantes, la predicción debe coincidir."""
        hoy = date(2026, 4, 1)
        fechas  = [hoy - timedelta(days=i) for i in range(28, 0, -1)]
        valores = [10.0] * 28
        modelo = entrenar_baseline(fechas, valores)

        puntos = predecir_horizonte(modelo, desde=hoy, horizonte=7)
        assert len(puntos) == 7
        # Todas las predicciones deben rondar 10
        for _, demanda, _, _ in puntos:
            assert abs(demanda - 10.0) < 0.5

    def test_serie_creciente_detecta_tendencia(self):
        """Con tendencia positiva, predicciones futuras crecen entre días."""
        hoy = date(2026, 4, 1)
        fechas  = [hoy - timedelta(days=i) for i in range(28, 0, -1)]
        valores = [float(i) for i in range(28)]  # 0,1,...,27
        modelo = entrenar_baseline(fechas, valores)

        # La pendiente debe ser positiva
        assert modelo.slope > 0.5

        # Predicción al final del horizonte debe ser mayor que al inicio
        puntos = predecir_horizonte(modelo, desde=hoy, horizonte=14)
        primera_semana = sum(p[1] for p in puntos[:7]) / 7
        segunda_semana = sum(p[1] for p in puntos[7:]) / 7
        assert segunda_semana > primera_semana

    def test_estacionalidad_semanal_capturada(self):
        """Con factor diferente sáb/dom, los factores semanales reflejan el patrón."""
        hoy = date(2026, 4, 1)  # martes
        fechas  = [hoy - timedelta(days=i) for i in range(56, 0, -1)]
        valores = []
        for d in fechas:
            valores.append(20.0 if d.weekday() in (5, 6) else 10.0)
        modelo = entrenar_baseline(fechas, valores)

        # Sábado y domingo deben ser ~1.5x; lun-vie ~0.75x (normalizado)
        assert modelo.factores_semanales[5] > 1.2
        assert modelo.factores_semanales[6] > 1.2
        assert modelo.factores_semanales[0] < 1.0

    def test_intervalo_confianza_envuelve_prediccion(self):
        """Para cada punto: intervalo_inf <= demanda <= intervalo_sup."""
        hoy = date(2026, 4, 1)
        fechas  = [hoy - timedelta(days=i) for i in range(30, 0, -1)]
        # Serie con ruido uniforme
        valores = [10.0 + (i % 5) * 2 for i in range(30)]
        modelo = entrenar_baseline(fechas, valores)

        puntos = predecir_horizonte(modelo, desde=hoy, horizonte=14)
        for _, demanda, inf, sup in puntos:
            assert inf <= demanda <= sup
            assert inf >= 0  # no permitimos predicciones negativas

    def test_serie_vacia_devuelve_modelo_cero(self):
        """Caso degenerado: serie vacía no debe explotar."""
        modelo = entrenar_baseline([], [])
        assert modelo.nivel == 0.0
        assert modelo.samples == 0

    def test_metricas_holdout_con_serie_larga(self):
        """Con serie >= 14 días, las métricas deben venir del holdout y ser finitas."""
        hoy = date(2026, 4, 1)
        fechas  = [hoy - timedelta(days=i) for i in range(30, 0, -1)]
        valores = [10.0 + i * 0.1 for i in range(30)]
        modelo = entrenar_baseline(fechas, valores)
        assert modelo.rmse >= 0
        assert modelo.mae  >= 0


# ════════════════════════════════════════════════════════════════════════
#  PARTE 2 — DATA EXTRACTOR
# ════════════════════════════════════════════════════════════════════════
class TestDataExtractor:
    def test_serie_diaria_devuelve_serie_densa(self, db_session, tenant_owner):
        """La serie debe tener un punto por cada día del rango, incluso días sin ventas."""
        p = _crear_producto(db_session, tenant_owner)
        _seed_ventas_diarias(db_session, p, dias=14, cantidad_base=5)

        hoy = datetime.now(timezone.utc).date()
        serie = extraer_serie_diaria(
            db_session,
            producto_id=p.id,
            sucursal_id=p.sucursal_id,
            desde=hoy - timedelta(days=20),
            hasta=hoy - timedelta(days=1),
        )

        # 20 días en el rango → 20 puntos densos
        assert serie.n == 20
        # Algunos puntos serán 0 (los días previos al seed)
        assert any(v == 0.0 for v in serie.valores)
        # Otros serán positivos (los días con seed)
        assert any(v > 0.0 for v in serie.valores)

    def test_serie_ignora_devoluciones_y_ajustes(self, db_session, tenant_owner):
        """Solo movimientos tipo='venta' cuentan."""
        p = _crear_producto(db_session, tenant_owner)
        hoy = datetime.now(timezone.utc).date()
        ts = datetime.combine(hoy - timedelta(days=2), datetime.min.time(),
                              tzinfo=timezone.utc) + timedelta(hours=12)

        # Una venta + una devolución del mismo día
        db_session.add(MovimientoInventario(
            tenant_id=p.tenant_id, sucursal_id=p.sucursal_id, producto_id=p.id,
            tipo="venta", cantidad=-3, stock_antes=10, stock_despues=7, fecha=ts,
        ))
        db_session.add(MovimientoInventario(
            tenant_id=p.tenant_id, sucursal_id=p.sucursal_id, producto_id=p.id,
            tipo="devolucion", cantidad=2, stock_antes=7, stock_despues=9, fecha=ts,
        ))
        db_session.add(MovimientoInventario(
            tenant_id=p.tenant_id, sucursal_id=p.sucursal_id, producto_id=p.id,
            tipo="ajuste", cantidad=-1, stock_antes=9, stock_despues=8, fecha=ts,
        ))
        db_session.commit()

        serie = extraer_serie_diaria(
            db_session,
            producto_id=p.id, sucursal_id=p.sucursal_id,
            desde=hoy - timedelta(days=3), hasta=hoy - timedelta(days=1),
        )
        # El día con venta debe tener exactamente 3 (no 2 ni 1)
        valores_no_cero = [v for v in serie.valores if v > 0]
        assert valores_no_cero == [3.0]

    def test_listar_productos_entrenables_filtra_por_dias(self, db_session, tenant_owner):
        """Productos con < min_dias_con_ventas no deben aparecer."""
        p_largo = _crear_producto(db_session, tenant_owner, nombre="Producto A")
        p_corto = _crear_producto(db_session, tenant_owner, nombre="Producto B")

        _seed_ventas_diarias(db_session, p_largo, dias=20, cantidad_base=2)
        _seed_ventas_diarias(db_session, p_corto, dias=5,  cantidad_base=2)

        productos = listar_productos_entrenables(
            db_session,
            tenant_id=tenant_owner["tenant"].id,
            min_dias_con_ventas=14,
        )
        nombres = {p.nombre for p in productos}
        assert "Producto A" in nombres
        assert "Producto B" not in nombres


# ════════════════════════════════════════════════════════════════════════
#  PARTE 3 — FORECASTING END-TO-END
# ════════════════════════════════════════════════════════════════════════
class TestForecastingEndToEnd:
    def test_train_producto_persiste_metadata_y_forecasts(self, db_session, tenant_owner):
        p = _crear_producto(db_session, tenant_owner, stock=100)
        _seed_ventas_diarias(db_session, p, dias=30, cantidad_base=4)

        result = train_producto(db_session, p, horizonte_dias=14, persist=True)
        db_session.commit()

        assert result is not None
        assert result.modelo_tipo in {"baseline", "prophet"}
        assert len(result.puntos) == 14

        # Forecasts en BD
        forecasts = db_session.query(ForecastSerie).filter_by(producto_id=p.id).all()
        assert len(forecasts) == 14

        # Metadata en BD
        meta = db_session.query(MlModelMetadata).filter_by(producto_id=p.id).one()
        assert meta.samples >= 30
        assert meta.modelo_tipo == result.modelo_tipo

    def test_train_producto_sin_datos_devuelve_none(self, db_session, tenant_owner):
        """Producto sin ventas (o muy pocas) debe ser saltado."""
        p = _crear_producto(db_session, tenant_owner)
        # Sin ventas seed
        result = train_producto(db_session, p, horizonte_dias=14, persist=True)
        assert result is None

        # Solo 3 días con ventas: insuficiente (mínimo 7)
        hoy = datetime.now(timezone.utc).date()
        for d in [3, 5, 7]:
            ts = datetime.combine(hoy - timedelta(days=d), datetime.min.time(),
                                  tzinfo=timezone.utc)
            db_session.add(MovimientoInventario(
                tenant_id=p.tenant_id, sucursal_id=p.sucursal_id, producto_id=p.id,
                tipo="venta", cantidad=-1, stock_antes=0, stock_despues=0, fecha=ts,
            ))
        db_session.commit()
        result = train_producto(db_session, p, horizonte_dias=14, persist=True)
        assert result is None

    def test_re_entrenar_reemplaza_forecasts_viejos(self, db_session, tenant_owner):
        """Re-entrenar el mismo producto debe REEMPLAZAR forecasts, no acumular."""
        p = _crear_producto(db_session, tenant_owner)
        _seed_ventas_diarias(db_session, p, dias=20, cantidad_base=3)

        train_producto(db_session, p, horizonte_dias=14, persist=True)
        db_session.commit()
        assert db_session.query(ForecastSerie).filter_by(producto_id=p.id).count() == 14

        # Segundo entrenamiento con horizonte distinto
        train_producto(db_session, p, horizonte_dias=7, persist=True)
        db_session.commit()
        assert db_session.query(ForecastSerie).filter_by(producto_id=p.id).count() == 7

    def test_train_tenant_resumen_es_consistente(self, db_session, tenant_owner):
        """El resumen agregado debe coincidir con la cuenta real."""
        p1 = _crear_producto(db_session, tenant_owner, nombre="Producto A")
        p2 = _crear_producto(db_session, tenant_owner, nombre="Producto B")
        _seed_ventas_diarias(db_session, p1, dias=20, cantidad_base=3)
        _seed_ventas_diarias(db_session, p2, dias=20, cantidad_base=5)

        summary = train_tenant(
            db_session, tenant_owner["tenant"].id,
            horizonte_dias=14, prefer_prophet=False,
        )
        assert summary.modelos_entrenados == 2
        assert summary.forecasts_generados == 28  # 2 productos × 14 días
        assert summary.modelo_tipo == "baseline"
        assert summary.duracion_segundos >= 0


# ════════════════════════════════════════════════════════════════════════
#  PARTE 4 — ALERTAS INTELIGENTES
# ════════════════════════════════════════════════════════════════════════
class TestAlertas:
    def test_stockout_alerta_se_genera_con_stock_bajo(self, db_session, tenant_owner):
        """Si stock < demanda proyectada → alerta stockout."""
        p = _crear_producto(db_session, tenant_owner, stock=10)  # poco stock
        _seed_ventas_diarias(db_session, p, dias=30, cantidad_base=8)  # demanda alta

        result = train_producto(db_session, p, horizonte_dias=14, persist=True)
        db_session.commit()
        assert result is not None

        alertas = generar_alertas_para_producto(db_session, p, result, persist=True)
        db_session.commit()

        tipos = {a.tipo for a in alertas}
        assert "stockout_riesgo" in tipos

        a = next(a for a in alertas if a.tipo == "stockout_riesgo")
        assert a.severidad in {"info", "warning", "critical"}
        # El mensaje habla de "día" o "días" (singular o plural según urgencia)
        assert "día" in a.mensaje.lower()
        assert a.metadata_json is not None
        assert "dias_hasta_stockout" in a.metadata_json

    def test_sobrestock_alerta_con_cobertura_alta(self, db_session, tenant_owner):
        """Stock cubre > 30 días → alerta sobrestock (severidad info)."""
        p = _crear_producto(db_session, tenant_owner, stock=300)  # mucho stock
        _seed_ventas_diarias(db_session, p, dias=30, cantidad_base=2)  # demanda baja

        result = train_producto(db_session, p, horizonte_dias=14, persist=True)
        db_session.commit()
        assert result is not None

        alertas = generar_alertas_para_producto(db_session, p, result, persist=True)
        tipos = {a.tipo for a in alertas}
        assert "sobrestock" in tipos

    def test_alertas_no_se_duplican(self, db_session, tenant_owner):
        """Re-llamar genera_alertas con la misma situación NO duplica alertas activas."""
        p = _crear_producto(db_session, tenant_owner, stock=10)
        _seed_ventas_diarias(db_session, p, dias=30, cantidad_base=8)

        result = train_producto(db_session, p, horizonte_dias=14, persist=True)
        db_session.commit()

        generar_alertas_para_producto(db_session, p, result, persist=True)
        db_session.commit()
        cnt1 = db_session.query(MlAlerta).filter_by(
            producto_id=p.id, tipo="stockout_riesgo", leida=False,
        ).count()

        # Segunda llamada con mismo input
        generar_alertas_para_producto(db_session, p, result, persist=True)
        db_session.commit()
        cnt2 = db_session.query(MlAlerta).filter_by(
            producto_id=p.id, tipo="stockout_riesgo", leida=False,
        ).count()

        assert cnt1 == cnt2 == 1

    def test_producto_estrella_top_n(self, db_session, tenant_owner):
        """Las alertas globales eligen los top N por demanda total."""
        productos = []
        for i, base in enumerate([10, 5, 3, 1]):
            p = _crear_producto(db_session, tenant_owner, nombre=f"Prod {i}")
            _seed_ventas_diarias(db_session, p, dias=20, cantidad_base=base)
            productos.append(p)

        resultados = []
        for p in productos:
            r = train_producto(db_session, p, horizonte_dias=14, persist=True)
            assert r is not None
            resultados.append(r)
        db_session.commit()

        productos_por_id = {p.id: p for p in productos}
        alertas = generar_alertas_globales(
            db_session,
            tenant_owner["tenant"].id,
            forecasts=resultados,
            productos_por_id=productos_por_id,
            persist=True,
            top_n_estrella=2,
        )
        db_session.commit()

        estrellas = [a for a in alertas if a.tipo == "producto_estrella"]
        assert len(estrellas) == 2
        # Los productos estrella deben ser los de mayor demanda (Prod 0 y Prod 1)
        nombres = [a.titulo for a in estrellas]
        assert any("Prod 0" in n for n in nombres)


# ════════════════════════════════════════════════════════════════════════
#  PARTE 5 — ENDPOINTS HTTP
# ════════════════════════════════════════════════════════════════════════
class TestMlEndpoints:
    def test_status_endpoint_responde(self, client, auth_headers_owner):
        r = client.get("/api/v3/ml/status", headers=auth_headers_owner)
        assert r.status_code == 200
        body = r.json()
        assert "prophet_disponible" in body
        assert body["modelos_entrenados"] == 0
        assert body["forecasts_persistidos"] == 0

    def test_train_endpoint_genera_modelos(
        self, client, db_session, tenant_owner, auth_headers_owner,
    ):
        p = _crear_producto(db_session, tenant_owner, stock=100)
        _seed_ventas_diarias(db_session, p, dias=20, cantidad_base=3)

        r = client.post("/api/v3/ml/train", headers=auth_headers_owner)
        assert r.status_code == 200, r.text
        body = r.json()
        assert body["modelos_entrenados"] == 1
        assert body["forecasts_generados"] == 14
        assert body["modelo_tipo"] in {"baseline", "prophet"}

        # Status refleja los modelos
        r = client.get("/api/v3/ml/status", headers=auth_headers_owner)
        assert r.json()["modelos_entrenados"] == 1

    def test_forecast_producto_devuelve_puntos(
        self, client, db_session, tenant_owner, auth_headers_owner,
    ):
        p = _crear_producto(db_session, tenant_owner, stock=100)
        _seed_ventas_diarias(db_session, p, dias=20, cantidad_base=3)
        client.post("/api/v3/ml/train", headers=auth_headers_owner)

        r = client.get(f"/api/v3/ml/forecast/{p.id}", headers=auth_headers_owner)
        assert r.status_code == 200, r.text
        body = r.json()
        assert body["producto_id"] == p.id
        assert body["horizonte_dias"] == 14
        assert len(body["puntos"]) == 14
        # Cada punto tiene fecha + demanda
        for punto in body["puntos"]:
            assert "fecha" in punto
            assert "demanda" in punto
            assert punto["demanda"] >= 0

    def test_forecast_404_si_no_entrenado(
        self, client, db_session, tenant_owner, auth_headers_owner,
    ):
        p = _crear_producto(db_session, tenant_owner)
        r = client.get(f"/api/v3/ml/forecast/{p.id}", headers=auth_headers_owner)
        assert r.status_code == 404

    def test_alerts_endpoint_filtra_no_leidas_por_default(
        self, client, db_session, tenant_owner, auth_headers_owner,
    ):
        p = _crear_producto(db_session, tenant_owner, stock=10)
        _seed_ventas_diarias(db_session, p, dias=20, cantidad_base=8)
        client.post("/api/v3/ml/train", headers=auth_headers_owner)

        r = client.get("/api/v3/ml/alerts", headers=auth_headers_owner)
        assert r.status_code == 200
        alertas = r.json()
        # Debe haber al menos la stockout
        tipos = {a["tipo"] for a in alertas}
        assert "stockout_riesgo" in tipos
        # Todas no leídas
        assert all(a["leida"] is False for a in alertas)

    def test_acknowledge_alerta(
        self, client, db_session, tenant_owner, auth_headers_owner,
    ):
        p = _crear_producto(db_session, tenant_owner, stock=10)
        _seed_ventas_diarias(db_session, p, dias=20, cantidad_base=8)
        client.post("/api/v3/ml/train", headers=auth_headers_owner)

        alertas = client.get("/api/v3/ml/alerts", headers=auth_headers_owner).json()
        assert alertas
        alerta_id = alertas[0]["id"]

        r = client.patch(
            f"/api/v3/ml/alerts/{alerta_id}/acknowledge",
            headers=auth_headers_owner,
        )
        assert r.status_code == 200
        assert r.json()["leida"] is True

        # Ya no debe aparecer en la lista de no-leídas
        alertas2 = client.get("/api/v3/ml/alerts", headers=auth_headers_owner).json()
        ids = {a["id"] for a in alertas2}
        assert alerta_id not in ids

    def test_restock_suggestions_ordena_por_urgencia(
        self, client, db_session, tenant_owner, auth_headers_owner,
    ):
        # Crear 2 productos: uno crítico (stock 0) y uno normal
        p_crit = _crear_producto(db_session, tenant_owner, nombre="Crítico", stock=0)
        p_ok   = _crear_producto(db_session, tenant_owner, nombre="OK",       stock=200)
        _seed_ventas_diarias(db_session, p_crit, dias=20, cantidad_base=4)
        _seed_ventas_diarias(db_session, p_ok,   dias=20, cantidad_base=4)
        client.post("/api/v3/ml/train", headers=auth_headers_owner)

        r = client.get("/api/v3/ml/restock-suggestions", headers=auth_headers_owner)
        assert r.status_code == 200, r.text
        sugerencias = r.json()
        # Debe haber al menos una crítica
        assert any(s["urgencia"] == "critica" for s in sugerencias)
        # La primera debe ser la más urgente
        if len(sugerencias) >= 2:
            urgencias = [s["urgencia"] for s in sugerencias]
            orden = {"critica": 0, "alta": 1, "media": 2, "baja": 3}
            assert orden[urgencias[0]] <= orden[urgencias[-1]]

    def test_aislamiento_entre_tenants(
        self, client, db_session, tenant_factory, make_auth_headers,
    ):
        """Un tenant NO debe ver alertas/forecasts de otro tenant."""
        t1 = tenant_factory(email="t1@test.com")
        t2 = tenant_factory(email="t2@test.com")

        p1 = _crear_producto(db_session, t1, stock=10)
        _seed_ventas_diarias(db_session, p1, dias=20, cantidad_base=8)

        h1 = make_auth_headers(t1["owner"])
        h2 = make_auth_headers(t2["owner"])

        client.post("/api/v3/ml/train", headers=h1)

        # T1 ve sus alertas
        r1 = client.get("/api/v3/ml/alerts", headers=h1)
        assert len(r1.json()) > 0

        # T2 NO ve nada
        r2 = client.get("/api/v3/ml/alerts", headers=h2)
        assert r2.json() == []

        # T2 NO puede leer forecast de p1
        r3 = client.get(f"/api/v3/ml/forecast/{p1.id}", headers=h2)
        assert r3.status_code == 404
