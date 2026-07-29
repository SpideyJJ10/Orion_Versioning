"""DIAN electronic invoicing adapter.

The production path must never mark a legal invoice as issued unless a real
authorized provider confirms it. Use DIAN_PROVIDER=mock only for demos/tests.
"""
from __future__ import annotations

import os
import uuid
from dataclasses import dataclass

import httpx

from backend.core.logger import logger
from backend.db.session import SessionLocal
from backend.models.orm import Orden


@dataclass(frozen=True)
class DianResult:
    status: str
    cufe: str | None = None
    pdf_url: str | None = None
    xml_url: str | None = None
    error: str | None = None


def _build_payload(orden: Orden) -> dict:
    return {
        "external_id": orden.id,
        "customer": orden.cliente_nombre or "Consumidor Final",
        "issue_date": orden.fecha.isoformat() if orden.fecha else None,
        "payment_method": orden.metodo_pago,
        "subtotal": float(orden.subtotal),
        "discount": float(orden.descuento or 0),
        "total": float(orden.total),
        "items": [
            {
                "name": item.producto_nombre,
                "quantity": float(item.cantidad),
                "unit_price": float(item.precio_unitario),
                "total": float(item.total),
            }
            for item in orden.items
        ],
    }


async def _emit_mock(orden: Orden) -> DianResult:
    cufe = f"{uuid.uuid4().hex}CUFE_DEMO"
    return DianResult(
        status="issued",
        cufe=cufe,
        pdf_url=f"https://demo-dian.local/facturas/{cufe}.pdf",
        xml_url=f"https://demo-dian.local/facturas/{cufe}.xml",
    )


async def _emit_http(orden: Orden) -> DianResult:
    api_url = os.getenv("DIAN_API_URL", "").strip()
    api_token = os.getenv("DIAN_API_TOKEN", "").strip()
    if not api_url or not api_token:
        return DianResult(status="failed", error="DIAN_API_URL y DIAN_API_TOKEN son obligatorios")

    async with httpx.AsyncClient(timeout=30) as client:
        response = await client.post(
            api_url.rstrip("/") + "/invoices",
            json=_build_payload(orden),
            headers={"Authorization": f"Bearer {api_token}"},
        )
        response.raise_for_status()
        data = response.json()

    cufe = data.get("cufe") or data.get("dian_cufe")
    if not cufe:
        return DianResult(status="failed", error="El proveedor no retorno CUFE")

    return DianResult(
        status="issued",
        cufe=cufe,
        pdf_url=data.get("pdf_url") or data.get("dian_pdf_url"),
        xml_url=data.get("xml_url") or data.get("dian_xml_url"),
    )


async def _emit(orden: Orden) -> DianResult:
    provider = os.getenv("DIAN_PROVIDER", "disabled").strip().lower()
    env = os.getenv("ENV", "dev").lower()

    if provider in {"", "disabled", "none"}:
        return DianResult(status="pending", error="Proveedor DIAN no configurado")
    if provider == "mock":
        if env in {"prod", "production"}:
            return DianResult(status="failed", error="DIAN_PROVIDER=mock no esta permitido en produccion")
        return await _emit_mock(orden)
    if provider == "http":
        return await _emit_http(orden)
    return DianResult(status="failed", error=f"Proveedor DIAN desconocido: {provider}")


async def emitir_factura_electronica_dian(orden_id: str) -> bool:
    """Emit or queue the DIAN invoice for a completed order."""
    logger.info("[DIAN] Iniciando proceso para orden: %s", orden_id)
    db = SessionLocal()
    try:
        orden = db.query(Orden).filter(Orden.id == orden_id).first()
        if not orden:
            logger.error("[DIAN] Orden no encontrada: %s", orden_id)
            return False
        if orden.dian_status == "issued":
            logger.info("[DIAN] Orden %s ya fue facturada", orden_id)
            return True

        orden.dian_status = "pending"
        db.commit()

        result = await _emit(orden)
        orden.dian_status = result.status
        orden.dian_cufe = result.cufe
        orden.dian_pdf_url = result.pdf_url
        orden.dian_xml_url = result.xml_url
        db.commit()

        if result.status == "issued":
            logger.info("[DIAN] Factura emitida. CUFE: %s", result.cufe)
            return True

        logger.warning("[DIAN] Orden %s queda en estado %s: %s", orden_id, result.status, result.error)
        return False
    except Exception:
        logger.exception("[DIAN] Error emitiendo factura para orden %s", orden_id)
        if "orden" in locals() and orden:
            orden.dian_status = "failed"
            db.commit()
        return False
    finally:
        db.close()
