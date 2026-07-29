"""
routes/oai.py — Orion IA: Conversation Engine + Provisioning.

Endpoints:
  POST /api/oai/chat        → Chat conversacional para entender el negocio
  POST /api/oai/provision   → Crea el tenant/negocio completo desde un perfil
  GET  /api/oai/templates   → Lista industrias disponibles con sus módulos

Este módulo NO requiere autenticación en /chat ni /provision (son el
onboarding público). El /provision sí crea tokens y los devuelve.
"""
from __future__ import annotations

import json
import os
import re
import uuid
from typing import Any, Literal

from fastapi import APIRouter, Depends, HTTPException
from fastapi.responses import StreamingResponse
from pydantic import BaseModel, EmailStr, Field
from sqlalchemy.orm import Session

from backend.auth_v3.passwords import hash_password
from backend.auth_v3.tokens import emitir_par_tokens
from backend.db.session import get_db
from backend.models.orm import (
    Mesa,
    OnboardingProgress,
    Sucursal,
    Tenant,
    TenantBranding,
    Usuario,
)

router = APIRouter(prefix="/api/oai", tags=["Orion IA"])


# ── Industry templates ──────────────────────────────────────────────────────

INDUSTRY_TEMPLATES: dict[str, dict[str, Any]] = {
    "restaurante": {
        "label": "Restaurante / Cafetería",
        "emoji": "🍽️",
        "color_primary": "#f97316",    # naranja cálido
        "color_secondary": "#1c1917",  # café oscuro
        "color_accent": "#fbbf24",     # dorado
        "tipografia": "Outfit",
        "categorias_default": ["Bebidas", "Platos fuertes", "Entradas", "Postres", "Combos"],
        "metodos_pago_default": ["Efectivo", "Nequi", "Daviplata", "Tarjeta"],
        "modulos_required": ["M01_pos", "M10_inventario"],
        "modulos_recommended": ["M12_mesas", "M05_delivery", "M30_reportes"],
        "preguntas_extra": ["num_mesas", "maneja_domicilios"],
        "setup_checklist": [
            "Añade tus platos al menú",
            "Configura tus mesas",
            "Invita a tus meseros",
            "Haz tu primera venta",
        ],
    },
    "barberia": {
        "label": "Barbería / Salón",
        "emoji": "✂️",
        "color_primary": "#3b82f6",    # azul
        "color_secondary": "#0f172a",
        "color_accent": "#06b6d4",
        "tipografia": "Inter",
        "categorias_default": ["Corte", "Barba", "Combo", "Cejas", "Tratamientos"],
        "metodos_pago_default": ["Efectivo", "Nequi", "Daviplata"],
        "modulos_required": ["M04_agenda", "M20_crm"],
        "modulos_recommended": ["M01_pos", "M21_fidelidad", "M30_reportes"],
        "preguntas_extra": ["num_empleados", "tiene_agenda_online"],
        "setup_checklist": [
            "Agrega tus servicios y precios",
            "Invita a tus barberos",
            "Configura tu horario",
            "Comparte tu link de reservas",
        ],
    },
    "farmacia": {
        "label": "Farmacia / Droguería",
        "emoji": "💊",
        "color_primary": "#10b981",    # verde salud
        "color_secondary": "#064e3b",
        "color_accent": "#34d399",
        "tipografia": "Inter",
        "categorias_default": ["Medicamentos", "Personal Care", "Vitaminas", "Bebés", "Varios"],
        "metodos_pago_default": ["Efectivo", "Tarjeta", "Nequi"],
        "modulos_required": ["M01_pos", "M10_inventario"],
        "modulos_recommended": ["M30_reportes", "M20_crm"],
        "preguntas_extra": ["maneja_formula_medica"],
        "setup_checklist": [
            "Importa o añade tu catálogo de productos",
            "Configura el stock mínimo de alerta",
            "Invita a tus dispensadores",
            "Registra tu primera venta",
        ],
    },
    "retail": {
        "label": "Tienda / Papelería / Miscelánea",
        "emoji": "🛍️",
        "color_primary": "#8b5cf6",    # violeta
        "color_secondary": "#1e1b4b",
        "color_accent": "#a78bfa",
        "tipografia": "Outfit",
        "categorias_default": ["General", "Papelería", "Hogar", "Snacks", "Varios"],
        "metodos_pago_default": ["Efectivo", "Nequi", "Daviplata", "Tarjeta"],
        "modulos_required": ["M01_pos", "M10_inventario"],
        "modulos_recommended": ["M30_reportes"],
        "preguntas_extra": [],
        "setup_checklist": [
            "Añade tus productos con código y precio",
            "Configura el stock inicial",
            "Invita a tus cajeros",
            "Registra tu primera venta",
        ],
    },
    "servicios": {
        "label": "Servicios / Taller / Consultorio",
        "emoji": "🔧",
        "color_primary": "#64748b",
        "color_secondary": "#0f172a",
        "color_accent": "#94a3b8",
        "tipografia": "Inter",
        "categorias_default": ["Servicios", "Repuestos", "Mano de obra", "Otros"],
        "metodos_pago_default": ["Efectivo", "Transferencia", "Nequi"],
        "modulos_required": ["M04_agenda", "M01_pos"],
        "modulos_recommended": ["M20_crm", "M30_reportes"],
        "preguntas_extra": ["num_empleados"],
        "setup_checklist": [
            "Crea tu catálogo de servicios",
            "Invita a tu equipo",
            "Configura tu agenda",
            "Registra tu primer servicio",
        ],
    },
}

# ── OIA System Prompt ───────────────────────────────────────────────────────

OIA_SYSTEM_PROMPT = """Eres Orion, un asistente de IA que ayuda a emprendedores latinoamericanos a digitalizar su negocio en minutos.

TU MISIÓN (en orden):
1. ENTENDER el negocio en máximo 5 mensajes
2. CONFIRMAR lo que entendiste antes de avanzar
3. Cuando tengas suficiente info, marcar ready_to_provision: true

TONO: Cálido, emprendedor, amigable. Como un amigo que sabe de negocios.
IDIOMA: Siempre español.
LONGITUD: Respuestas cortas, máximo 3 oraciones. Nunca hagas más de 2 preguntas por mensaje.

REGLAS ABSOLUTAS:
- NUNCA uses términos técnicos: "tenant", "endpoint", "módulo", "backend", "servidor", "API"
- NUNCA menciones que eres una IA o software si no te lo preguntan
- SIEMPRE valida y resume lo que entendiste antes de preguntar lo siguiente
- Si el usuario dice algo ambiguo, pregunta de forma más simple

INDUSTRIAS QUE RECONOCES:
- restaurante: restaurante, cafetería, comidas, asadero, hamburguesería, pizzería, sushi, panadería, heladería
- barberia: barbería, peluquería, salón, estética, nail bar, spa
- farmacia: farmacia, droguería, botiquín
- retail: tienda, papelería, miscelánea, abarrotes, minimercado, ferretería, ropa, boutique
- servicios: taller, consultorio, lavandería, gym, estudio, academia, veterinaria

DATOS QUE NECESITAS RECOPILAR:
- nombre_negocio (obligatorio)
- tipo_negocio: uno de los 5 anteriores (obligatorio)
- num_empleados: número aproximado (opcional pero útil)
- datos extras según el tipo (mesas para restaurante, agenda para barbería, etc.)
- email y contraseña del dueño (SOLO al final, cuando todo lo demás esté listo)

CUANDO TENGAS TODO (nombre + tipo + email + password):
- Responde con ready_to_provision: true
- El reply debe ser el mensaje de confirmación final antes de crear el negocio

OUTPUT SIEMPRE EN JSON VÁLIDO:
{
  "reply": "texto que el usuario ve",
  "extracted": {
    "nombre_negocio": null,
    "tipo_negocio": null,
    "num_empleados": null,
    "num_mesas": null,
    "email": null,
    "password": null
  },
  "ready_to_provision": false,
  "confidence": 0.0
}"""


# ── Schemas ─────────────────────────────────────────────────────────────────

class ChatMessage(BaseModel):
    role: Literal["user", "assistant"]
    content: str


class OIAChatRequest(BaseModel):
    message: str = Field(..., min_length=1, max_length=2000)
    session_id: str | None = None
    history: list[ChatMessage] = Field(default_factory=list)


class ExtractedProfile(BaseModel):
    nombre_negocio: str | None = None
    tipo_negocio: str | None = None
    num_empleados: int | None = None
    num_mesas: int | None = None
    email: str | None = None
    password: str | None = None


class OIAChatResponse(BaseModel):
    reply: str
    extracted: ExtractedProfile
    ready_to_provision: bool = False
    confidence: float = Field(0.0, ge=0.0, le=1.0)
    session_id: str


class ProvisionRequest(BaseModel):
    nombre_negocio: str = Field(..., min_length=2, max_length=100)
    tipo_negocio: str = Field(..., description="restaurante|barberia|farmacia|retail|servicios")
    email: EmailStr
    password: str = Field(..., min_length=6)
    num_mesas: int | None = Field(None, ge=1, le=200)
    num_empleados: int | None = Field(None, ge=1, le=500)


class ProvisionResponse(BaseModel):
    access_token: str
    refresh_token: str
    tenant_id: int
    sucursal_id: str
    app_url: str
    setup_checklist: list[str]
    branding: dict[str, Any]


class TemplateOut(BaseModel):
    key: str
    label: str
    emoji: str
    categorias_default: list[str]
    modulos_required: list[str]
    modulos_recommended: list[str]
    setup_checklist: list[str]


# ── Helpers ──────────────────────────────────────────────────────────────────

def _clean_json_content(content: str) -> dict:
    """Extrae y parsea JSON tolerando bloques markdown (```json ... ```) de LLMs locales."""
    if not content:
        return {}
    content = content.strip()
    match = re.search(r"```(?:json)?\s*(\{.*?\})\s*```", content, re.DOTALL)
    if match:
        content = match.group(1)
    elif content.startswith("```"):
        content = re.sub(r"^```[a-z]*\s*", "", content)
        content = re.sub(r"\s*```$", "", content)
    try:
        return json.loads(content)
    except json.JSONDecodeError:
        match_obj = re.search(r"(\{.*\})", content, re.DOTALL)
        if match_obj:
            try:
                return json.loads(match_obj.group(1))
            except json.JSONDecodeError:
                pass
        return {}


def _call_openai(messages: list[dict], temperature: float = 0.7) -> dict:
    """
    Llama a OpenAI o LM Studio y parsea el JSON estructurado de la respuesta.
    Soporta:
      - LM Studio local (LM_STUDIO_URL u OPENAI_BASE_URL, e.g. http://localhost:1234/v1)
      - OpenAI oficial (OPENAI_API_KEY)
    Degrada a respuesta estática si ni OPENAI_API_KEY ni LM Studio están configurados.
    """
    api_key = os.getenv("OPENAI_API_KEY", "").strip()
    base_url = os.getenv("OPENAI_BASE_URL", "").strip() or os.getenv("LM_STUDIO_URL", "").strip()
    model = os.getenv("OPENAI_MODEL", "").strip()

    # Si se especificó base_url (ej. LM Studio) pero no api_key, usamos "lm-studio"
    if base_url and not api_key:
        api_key = "lm-studio"

    if not api_key and not base_url:
        # Fallback offline: respuesta estática para desarrollo local sin clave ni LM Studio
        return {
            "reply": "¡Hola! Soy Orion 🪐 Voy a ayudarte a crear el software para tu negocio. ¿Cómo se llama tu negocio?",
            "extracted": {},
            "ready_to_provision": False,
            "confidence": 0.5,
        }

    try:
        import openai
        client_kwargs: dict[str, Any] = {"api_key": api_key}
        if base_url:
            client_kwargs["base_url"] = base_url

        client = openai.OpenAI(**client_kwargs)
        target_model = model or ("gpt-4o-mini" if not base_url else "local-model")

        create_kwargs: dict[str, Any] = {
            "model": target_model,
            "messages": messages,
            "temperature": temperature,
            "max_tokens": 600,
        }
        if not base_url:
            create_kwargs["response_format"] = {"type": "json_object"}

        try:
            response = client.chat.completions.create(**create_kwargs)
        except Exception:
            if "response_format" in create_kwargs:
                del create_kwargs["response_format"]
                response = client.chat.completions.create(**create_kwargs)
            else:
                raise

        content = response.choices[0].message.content or "{}"
        parsed = _clean_json_content(content)
        if not parsed:
            parsed = {
                "reply": content,
                "extracted": {},
                "ready_to_provision": False,
                "confidence": 0.5,
            }
        return parsed
    except Exception as exc:
        raise HTTPException(
            status_code=503,
            detail=f"Error al contactar el asistente IA: {exc}",
        )


def _build_messages(request: OIAChatRequest) -> list[dict]:
    messages: list[dict] = [{"role": "system", "content": OIA_SYSTEM_PROMPT}]
    for h in request.history[-8:]:  # max 8 turnos de contexto
        messages.append({"role": h.role, "content": h.content})
    messages.append({"role": "user", "content": request.message})
    return messages


def _slug_from_name(nombre: str) -> str:
    """Genera un slug URL-safe desde el nombre del negocio."""
    slug = nombre.lower().strip()
    slug = re.sub(r"[áàäâ]", "a", slug)
    slug = re.sub(r"[éèëê]", "e", slug)
    slug = re.sub(r"[íìïî]", "i", slug)
    slug = re.sub(r"[óòöô]", "o", slug)
    slug = re.sub(r"[úùüû]", "u", slug)
    slug = re.sub(r"ñ", "n", slug)
    slug = re.sub(r"[^a-z0-9]+", "-", slug)
    slug = slug.strip("-")[:40]
    # Append short uuid to guarantee uniqueness
    slug = f"{slug}-{uuid.uuid4().hex[:6]}"
    return slug


# ── Endpoints ────────────────────────────────────────────────────────────────

@router.get("/templates", response_model=list[TemplateOut])
def listar_templates():
    """
    Devuelve las industrias soportadas con sus módulos y checklist.
    Usado por el Wizard UI para renderizar las opciones de tipo de negocio.
    """
    return [
        TemplateOut(
            key=key,
            label=tpl["label"],
            emoji=tpl["emoji"],
            categorias_default=tpl["categorias_default"],
            modulos_required=tpl["modulos_required"],
            modulos_recommended=tpl["modulos_recommended"],
            setup_checklist=tpl["setup_checklist"],
        )
        for key, tpl in INDUSTRY_TEMPLATES.items()
    ]


@router.post("/chat", response_model=OIAChatResponse)
def oai_chat(body: OIAChatRequest):
    """
    Endpoint de conversación del Orion IA.

    Recibe el mensaje del usuario + historial + datos ya extraídos.
    Devuelve la respuesta de Orion + datos actualizados extraídos de la conversación.
    Cuando ready_to_provision = true, el frontend llama a POST /api/oai/provision.
    """
    session_id = body.session_id or uuid.uuid4().hex

    messages = _build_messages(body)
    raw = _call_openai(messages)

    # Parsear con tolerancia a respuestas parciales
    extracted_raw = raw.get("extracted", {}) or {}
    extracted = ExtractedProfile(**{
        k: extracted_raw.get(k) for k in ExtractedProfile.model_fields
    })

    return OIAChatResponse(
        reply=raw.get("reply", "Cuéntame más sobre tu negocio 😊"),
        extracted=extracted,
        ready_to_provision=bool(raw.get("ready_to_provision", False)),
        confidence=float(raw.get("confidence", 0.0)),
        session_id=session_id,
    )


@router.post("/provision", response_model=ProvisionResponse, status_code=201)
def oai_provision(body: ProvisionRequest, db: Session = Depends(get_db)):
    """
    Crea un nuevo negocio completo a partir del perfil capturado por el chat.

    Pasos atómicos:
    1. Crear Tenant
    2. Crear TenantBranding con colores/tipografía de la industria
    3. Crear Sucursal principal
    4. Crear Usuario owner
    5. Crear OnboardingProgress
    6. Si restaurante + num_mesas → crear mesas en bulk
    7. Emitir token pair y retornar

    Si cualquier paso falla → rollback completo. El usuario puede volver a intentar.
    """
    tipo = body.tipo_negocio.lower().strip()
    template = INDUSTRY_TEMPLATES.get(tipo)
    if not template:
        raise HTTPException(
            status_code=422,
            detail=f"Industria '{tipo}' no soportada. Opciones: {list(INDUSTRY_TEMPLATES)}",
        )

    email = body.email.lower().strip()

    try:
        # 1) Verificar que el email no exista ya
        if db.query(Tenant).filter(Tenant.email == email).first():
            raise HTTPException(
                status_code=409,
                detail="Ya existe una cuenta con ese correo. ¿Quieres iniciar sesión?",
            )

        # 2) Crear Tenant
        tenant = Tenant(
            email=email,
            password_hash=hash_password(body.password),
            nombre=body.nombre_negocio,
            plan="trial",
            activo=True,
            plan_activo=True,
        )
        db.add(tenant)
        db.flush()  # obtener tenant.id

        # 3) Branding con colores de la industria
        branding = TenantBranding(
            tenant_id=tenant.id,
            nombre_comercial=body.nombre_negocio,
            nicho=tipo,
            color_primary=template["color_primary"],
            color_secondary=template["color_secondary"],
            color_accent=template["color_accent"],
            tipografia=template["tipografia"],
            categorias_default=template["categorias_default"],
        )
        db.add(branding)

        # 4) Sucursal principal
        sucursal = Sucursal(
            tenant_id=tenant.id,
            nombre="Principal",
            activo=True,
        )
        db.add(sucursal)
        db.flush()  # obtener sucursal.id

        # 5) Usuario owner
        usuario = Usuario(
            tenant_id=tenant.id,
            email=email,
            password_hash=hash_password(body.password),
            nombre=body.nombre_negocio,
            rol="owner",
            sucursal_id=sucursal.id,
            activo=True,
        )
        db.add(usuario)
        db.flush()  # obtener usuario.id

        # 6) Onboarding tracking
        onboarding = OnboardingProgress(
            tenant_id=tenant.id,
            perfil_configurado=True,  # ya está configurado desde el wizard
        )
        db.add(onboarding)

        # 7) Mesas (solo para restaurantes con num_mesas)
        if tipo == "restaurante" and body.num_mesas and body.num_mesas > 0:
            for num in range(1, body.num_mesas + 1):
                db.add(Mesa(
                    tenant_id=tenant.id,
                    sucursal_id=sucursal.id,
                    numero=num,
                    capacidad=4,
                    estado="libre",
                ))

        db.commit()
        db.refresh(usuario)

        # 8) Emitir tokens
        tokens = emitir_par_tokens(usuario)

        return ProvisionResponse(
            access_token=tokens["access_token"],
            refresh_token=tokens["refresh_token"],
            tenant_id=tenant.id,
            sucursal_id=sucursal.id,
            app_url=f"/dashboard",
            setup_checklist=template["setup_checklist"],
            branding={
                "nombre_comercial": body.nombre_negocio,
                "nicho": tipo,
                "color_primary": template["color_primary"],
                "color_secondary": template["color_secondary"],
                "color_accent": template["color_accent"],
                "tipografia": template["tipografia"],
                "categorias_default": template["categorias_default"],
            },
        )

    except HTTPException:
        db.rollback()
        raise
    except Exception as exc:
        db.rollback()
        raise HTTPException(
            status_code=500,
            detail=f"Error al crear el negocio: {exc}",
        ) from exc
