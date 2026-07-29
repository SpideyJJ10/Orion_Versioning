"""
scripts/train_models.py — Cron diario: re-entrena modelos ML para todos los tenants.

Uso:
    py -3 scripts/train_models.py                        # todos los tenants activos
    py -3 scripts/train_models.py --tenant-id 12         # un tenant específico
    py -3 scripts/train_models.py --horizonte 21         # cambiar horizonte
    py -3 scripts/train_models.py --no-prophet           # forzar baseline

Diseñado para correr como cron job en Render (o cualquier scheduler).
Imprime un resumen JSON-like al final, fácil de parsear desde logs.
"""
from __future__ import annotations

import argparse
import json
import logging
import sys
import time
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))

from backend.db.session import SessionLocal  # noqa: E402
from backend.ml import PROPHET_AVAILABLE, train_tenant  # noqa: E402
from backend.models.orm import Tenant  # noqa: E402

logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s [%(levelname)s] %(name)s — %(message)s",
)
log = logging.getLogger("tizon.cron.ml")


def main() -> int:
    parser = argparse.ArgumentParser(description="Re-entrena modelos ML por tenant.")
    parser.add_argument("--tenant-id",  type=int, default=None,
                        help="Solo este tenant (default: todos los activos).")
    parser.add_argument("--horizonte",  type=int, default=14,
                        help="Días de horizonte para forecasting (default 14).")
    parser.add_argument("--historial",  type=int, default=90,
                        help="Días de historial usados para entrenar (default 90).")
    parser.add_argument("--no-prophet", action="store_true",
                        help="Fuerza modelo baseline aunque Prophet esté instalado.")
    args = parser.parse_args()

    use_prophet = PROPHET_AVAILABLE and not args.no_prophet
    log.info("Inicio cron ML | prophet_disponible=%s | usar_prophet=%s",
             PROPHET_AVAILABLE, use_prophet)

    db = SessionLocal()
    t_global = time.time()
    resumen_global = {
        "tenants_evaluados":     0,
        "tenants_con_modelos":   0,
        "modelos_entrenados":    0,
        "forecasts_generados":   0,
        "alertas_creadas":       0,
        "errores":               0,
        "duracion_total_seg":    0.0,
        "modelo_tipo_usado":     "prophet" if use_prophet else "baseline",
        "detalles_por_tenant":   [],
    }

    try:
        query = db.query(Tenant).filter(
            Tenant.activo      == True,
            Tenant.plan_activo == True,
        )
        if args.tenant_id is not None:
            query = query.filter(Tenant.id == args.tenant_id)

        tenants = query.all()
        if not tenants:
            log.warning("No hay tenants activos a procesar.")
            return 0

        for t in tenants:
            log.info("Tenant %d (%s) — entrenando…", t.id, t.email)
            resumen_global["tenants_evaluados"] += 1
            try:
                summary = train_tenant(
                    db, t.id,
                    horizonte_dias = args.horizonte,
                    historial_dias = args.historial,
                    prefer_prophet = use_prophet,
                )
                resumen_global["modelos_entrenados"]  += summary.modelos_entrenados
                resumen_global["forecasts_generados"] += summary.forecasts_generados
                resumen_global["alertas_creadas"]     += summary.alertas_creadas
                if summary.modelos_entrenados > 0:
                    resumen_global["tenants_con_modelos"] += 1
                resumen_global["detalles_por_tenant"].append({
                    "tenant_id":           t.id,
                    "email":               t.email,
                    "productos_evaluados": summary.productos_evaluados,
                    "modelos_entrenados":  summary.modelos_entrenados,
                    "modelos_omitidos":    summary.modelos_omitidos,
                    "forecasts":           summary.forecasts_generados,
                    "alertas":             summary.alertas_creadas,
                    "duracion_seg":        summary.duracion_segundos,
                    "errores":             summary.errores[:5],  # truncar
                })
                if summary.errores:
                    resumen_global["errores"] += len(summary.errores)
                log.info(
                    "  -> entrenados=%d, forecasts=%d, alertas=%d en %.2fs",
                    summary.modelos_entrenados,
                    summary.forecasts_generados,
                    summary.alertas_creadas,
                    summary.duracion_segundos,
                )
            except Exception as exc:
                resumen_global["errores"] += 1
                log.exception("Error procesando tenant %d: %s", t.id, exc)

        resumen_global["duracion_total_seg"] = round(time.time() - t_global, 2)
        log.info("Resumen final: %s", json.dumps({
            k: v for k, v in resumen_global.items() if k != "detalles_por_tenant"
        }))
        # Imprime también detalles para logs estructurados
        print(json.dumps(resumen_global, indent=2, ensure_ascii=False))
        return 0 if resumen_global["errores"] == 0 else 1
    finally:
        db.close()


if __name__ == "__main__":
    sys.exit(main())
