"""
routes/copilot.py — Orion Copilot: Asistente IA contextual para el negocio.

Endpoint:
  POST /api/copilot/chat  → Chat con contexto del negocio (ventas, stock, alertas)

Requiere autenticación (get_current_user). El LLM tiene acceso a funciones del negocio.
"""
import os
import json
from datetime import datetime, timezone, timedelta
from typing import Literal

from fastapi import APIRouter, Depends, HTTPException
from pydantic import BaseModel, Field
from sqlalchemy.orm import Session
from sqlalchemy import func

from backend.auth_v3 import get_current_usuario
from backend.db.session import get_db
from backend.models.orm import TenantBranding, Venta
from backend.routes.ml import restock_suggestions, listar_alertas

router = APIRouter(prefix="/api/copilot", tags=["Copilot"])

class ChatMessage(BaseModel):
    role: Literal["user", "assistant"]
    content: str

class CopilotChatRequest(BaseModel):
    message: str = Field(..., min_length=1, max_length=2000)
    history: list[ChatMessage] = Field(default_factory=list)

class CopilotChatResponse(BaseModel):
    reply: str

def _call_openai(messages: list[dict], temperature: float = 0.7) -> str:
    api_key = os.getenv("OPENAI_API_KEY", "").strip()
    base_url = os.getenv("OPENAI_BASE_URL", "").strip() or os.getenv("LM_STUDIO_URL", "").strip()
    model = os.getenv("OPENAI_MODEL", "").strip()

    if not api_key and not base_url:
        return "El servicio de Copilot está configurado en modo offline. ¡Prueba a configurar OPENAI_API_KEY!"

    if base_url and not api_key:
        api_key = "lm-studio"

    try:
        import openai
        client_kwargs = {"api_key": api_key}
        if base_url:
            client_kwargs["base_url"] = base_url

        client = openai.OpenAI(**client_kwargs)
        target_model = model or ("gpt-4o-mini" if not base_url else "local-model")

        response = client.chat.completions.create(
            model=target_model,
            messages=messages,
            temperature=temperature,
            max_tokens=600,
        )
        return response.choices[0].message.content or ""
    except Exception as exc:
        raise HTTPException(
            status_code=503,
            detail=f"Error al contactar el asistente IA: {exc}",
        )

@router.post("/chat", response_model=CopilotChatResponse)
def copilot_chat(
    body: CopilotChatRequest,
    user: dict = Depends(get_current_usuario),
    db: Session = Depends(get_db)
):
    tenant_id = user["tenant_id"]
    
    branding = db.query(TenantBranding).filter_by(tenant_id=tenant_id).first()
    business_name = branding.nombre_comercial if branding else "Tu Negocio"
    business_type = branding.nicho if branding else "retail"
    
    today_local = datetime.now(timezone.utc) - timedelta(hours=5)
    date_str = today_local.strftime("%Y-%m-%d")
    
    # 1. Fallback function calling: Inject context if keywords found
    msg_lower = body.message.lower()
    injected_context = ""
    
    if "venta" in msg_lower:
        start_utc = (today_local.replace(hour=0, minute=0, second=0, microsecond=0) + timedelta(hours=5)).replace(tzinfo=timezone.utc)
        ventas_hoy = db.query(func.sum(Venta.total)).filter(
            Venta.tenant_id == tenant_id,
            Venta.anulada == False,
            Venta.fecha >= start_utc
        ).scalar() or 0.0
        injected_context += f"\n- Datos inyectados (Ventas de hoy): ${ventas_hoy:,.2f}"
        
    if "restock" in msg_lower or "stock" in msg_lower or "pedido" in msg_lower:
        sug = restock_suggestions(sucursal_id=None, horizonte_dias=14, user={"tenant_id": tenant_id}, db=db)
        if sug:
            items = [f"{s.producto_nombre} (Sugerido: {s.cantidad_sugerida}, Urgencia: {s.urgencia})" for s in sug[:5]]
            injected_context += f"\n- Datos inyectados (Sugerencias de restock): {', '.join(items)}"
        else:
            injected_context += "\n- Datos inyectados (Sugerencias de restock): No hay sugerencias críticas."
            
    if "alerta" in msg_lower:
        alertas = listar_alertas(sucursal_id=None, incluir_leidas=False, severidad=None, tipo=None, limit=5, user={"tenant_id": tenant_id}, db=db)
        if alertas:
            items = [f"[{a.severidad}] {a.titulo}: {a.mensaje}" for a in alertas]
            injected_context += f"\n- Datos inyectados (Alertas recientes): {' | '.join(items)}"
        else:
            injected_context += "\n- Datos inyectados (Alertas recientes): No hay alertas no leídas."

    # 2. Build System Prompt
    system_prompt = f"""Eres el Orion Intelligence Copilot, un asistente virtual experto para el negocio '{business_name}' (Tipo: {business_type}).
Fecha actual: {date_str}

Tu objetivo es ayudar al dueño del negocio a tomar decisiones, entender sus datos y sugerir acciones (como restock de inventario, revisar alertas o consultar ventas).
Tono: Profesional, directo, útil y muy conciso. Usa markdown (puedes usar negritas, listas).
"""

    if injected_context:
        system_prompt += f"\n\nHe consultado la base de datos automáticamente por ti basándome en el mensaje del usuario. Usa esta información para responder:{injected_context}"

    messages = [{"role": "system", "content": system_prompt}]
    for h in body.history[-6:]:
        messages.append({"role": h.role, "content": h.content})
    messages.append({"role": "user", "content": body.message})
    
    reply = _call_openai(messages)
    
    return CopilotChatResponse(reply=reply)
