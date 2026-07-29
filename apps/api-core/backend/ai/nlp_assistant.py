"""
Asistente NLP contextual para el admin del POS.

Estrategia:
  - Clasificación rápida por keywords/regex (ahorra tokens al LLM).
  - Datos reales: queries SQL acotadas por tenant_id.
  - Composición final con LLM si OPENAI_API_KEY está presente; si no, fallback texto.

Documentación: docs/AI_MODULES.md sección 3
"""
from __future__ import annotations

import os
import re
from dataclasses import dataclass, asdict
from datetime import date
from typing import Optional

# OpenAI / LM Studio client opcional (no rompe el arranque si no está)
try:
    from openai import OpenAI
    _api_key = os.getenv("OPENAI_API_KEY", "").strip()
    _base_url = os.getenv("OPENAI_BASE_URL", "").strip() or os.getenv("LM_STUDIO_URL", "").strip()
    _model_name = os.getenv("OPENAI_MODEL", "").strip() or ("gpt-4o-mini" if not _base_url else "local-model")

    if _base_url and not _api_key:
        _api_key = "lm-studio"

    if _api_key or _base_url:
        _client_kwargs = {"api_key": _api_key}
        if _base_url:
            _client_kwargs["base_url"] = _base_url
        _client: Optional[OpenAI] = OpenAI(**_client_kwargs)
    else:
        _client = None
except ImportError:  # pragma: no cover
    _client = None


# ── Clasificación de intent (sin LLM) ───────────────────────────────
INTENT_PATTERNS = {
    "ventas_dia":     re.compile(r"\b(vent[ae]s?|cobr[ée]|gan[éa]).*(hoy|ayer|d[ií]a)", re.I),
    "stock_bajo":     re.compile(r"\b(stock\s*bajo|sin\s*stock|qu[ée]\s*falta|por\s*acabarse)", re.I),
    "top_productos":  re.compile(r"\b(m[áa]s\s*vendid[oa]s?|top\s*\d*|estrella)", re.I),
    "ayuda_invitar":  re.compile(r"\b(invit[ae]r|crear|alta|nuevo)\s*(usuario|cajero|empleado)", re.I),
    "ayuda_branding": re.compile(r"\b(cambi[ae]r?|personali[zs]ar)\s*(color|logo|marca|tema)", re.I),
    "ayuda_precio":   re.compile(r"\b(cambi[ae]r|actualizar|modificar)\s*(precio|costo)", re.I),
}

# ── Knowledge Base local (snippets oficiales) ───────────────────────
KB_SNIPPETS: dict[str, str] = {
    "ayuda_invitar": (
        "Para invitar un cajero ve a **Equipo > Nuevo usuario**, ingresa email y selecciona el rol "
        "`cajero`. Recibirá un email para definir su contraseña. Si tu negocio usa PIN, además "
        "puedes generar uno de 6 dígitos en el detalle del usuario."
    ),
    "ayuda_branding": (
        "Para cambiar el branding ve a **Branding** en el menú lateral, ajusta color primario, "
        "tema y nombre comercial. Los cambios son inmediatos y se persisten para todos los usuarios "
        "del tenant."
    ),
    "ayuda_precio": (
        "Para cambiar el precio de un producto ve a **Productos**, busca el producto y haz click en "
        "él. Modifica el campo Precio o Costo y guarda. Los cambios afectan ventas futuras; las "
        "ventas históricas quedan con el precio que tenían al momento de la transacción."
    ),
}


@dataclass
class RespuestaAsistente:
    texto: str
    intent: str
    datos: Optional[dict] = None
    sugerencia_ruta: Optional[str] = None

    def to_dict(self) -> dict:
        return asdict(self)


def _detectar_intent(pregunta: str) -> str:
    for intent, pattern in INTENT_PATTERNS.items():
        if pattern.search(pregunta):
            return intent
    return "fallback"


def _consultar_datos(intent: str, db, tenant_id: int) -> Optional[dict]:
    """Queries SQL acotadas por tenant_id. Devuelve dict listo para renderizar."""
    from sqlalchemy import func
    from backend.models.orm import Orden, OrdenItem, Producto

    if intent == "ventas_dia":
        hoy = date.today()
        total = db.query(func.coalesce(func.sum(Orden.total), 0)).filter(
            Orden.tenant_id == tenant_id,
            func.date(Orden.creado_en) == hoy,
            Orden.estado == "pagada",
        ).scalar()
        cnt = db.query(func.count(Orden.id)).filter(
            Orden.tenant_id == tenant_id,
            func.date(Orden.creado_en) == hoy,
            Orden.estado == "pagada",
        ).scalar()
        return {
            "fecha":         hoy.isoformat(),
            "total_ventas":  float(total or 0),
            "total_ordenes": int(cnt or 0),
        }

    if intent == "stock_bajo":
        prods = db.query(
            Producto.nombre, Producto.stock, Producto.stock_minimo
        ).filter(
            Producto.tenant_id == tenant_id,
            Producto.activo == True,    # noqa: E712
            Producto.stock <= Producto.stock_minimo,
        ).limit(10).all()
        return {
            "productos": [
                {"nombre": p[0], "stock": float(p[1] or 0), "minimo": float(p[2] or 0)}
                for p in prods
            ],
            "total": len(prods),
        }

    if intent == "top_productos":
        rows = db.query(
            Producto.nombre,
            func.sum(OrdenItem.cantidad).label("vendido"),
        ).join(OrdenItem, OrdenItem.producto_id == Producto.id) \
         .join(Orden, Orden.id == OrdenItem.orden_id) \
         .filter(Producto.tenant_id == tenant_id, Orden.estado == "pagada") \
         .group_by(Producto.nombre) \
         .order_by(func.sum(OrdenItem.cantidad).desc()) \
         .limit(5).all()
        return {"top": [
            {"nombre": r[0], "unidades": int(r[1] or 0)} for r in rows
        ]}

    return None


def _componer_con_llm(pregunta: str, datos: dict | None, snippet: str | None) -> str:
    """Compone respuesta natural; usa fallback si no hay LLM disponible."""
    if _client is None:
        if datos:
            return f"Datos solicitados: {datos}"
        if snippet:
            return snippet
        return ("No tengo respuesta para eso. Consulta la documentación en /docs o "
                "escribe a soporte@orionpos.com.")

    contexto_partes = []
    if datos:
        contexto_partes.append(f"DATOS REALES DEL NEGOCIO: {datos}")
    if snippet:
        contexto_partes.append(f"INSTRUCCIONES OFICIALES: {snippet}")
    contexto = "\n\n".join(contexto_partes) or "(sin datos disponibles)"

    completion = _client.chat.completions.create(
        model=_model_name,
        max_tokens=200,
        temperature=0.3,
        messages=[
            {
                "role": "system",
                "content": (
                    "Eres el asistente del POS Orion. Responde siempre en español, breve "
                    "(<=80 palabras), con datos concretos. Nunca inventes cifras: si no hay "
                    "datos, dilo. Sugiere la sección del POS si aplica."
                ),
            },
            {
                "role": "user",
                "content": f"Pregunta: {pregunta}\n\nContexto:\n{contexto}",
            },
        ],
    )
    return completion.choices[0].message.content.strip()


# ── Mapa intent → ruta sugerida ─────────────────────────────────────
_RUTAS = {
    "ayuda_invitar":  "/usuarios",
    "ayuda_branding": "/branding",
    "ayuda_precio":   "/productos",
    "stock_bajo":     "/inventario",
    "top_productos":  "/reportes",
    "ventas_dia":     "/dashboard",
}


def responder(pregunta: str, db, tenant_id: int) -> RespuestaAsistente:
    """API pública: devuelve respuesta lista para mostrar al usuario."""
    intent = _detectar_intent(pregunta)
    datos = (
        _consultar_datos(intent, db, tenant_id)
        if intent in {"ventas_dia", "stock_bajo", "top_productos"}
        else None
    )
    snippet = KB_SNIPPETS.get(intent)
    texto = _componer_con_llm(pregunta, datos, snippet)
    return RespuestaAsistente(
        texto=texto,
        intent=intent,
        datos=datos,
        sugerencia_ruta=_RUTAS.get(intent),
    )
