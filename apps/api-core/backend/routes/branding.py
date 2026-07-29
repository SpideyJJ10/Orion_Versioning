"""
routes/branding.py — CRUD de personalización visual por tenant.

Endpoints:
  GET  /api/v3/branding       → Obtener branding del tenant actual
  PUT  /api/v3/branding       → Actualizar branding (owner/manager)
  GET  /api/v3/branding/public/{tenant_id} → Branding público (para login screens)
"""
import re

from fastapi import APIRouter, Depends, HTTPException, status
from pydantic import BaseModel, Field
from sqlalchemy.orm import Session
from typing import Optional

from backend.auth_v3 import Rol, get_current_usuario, requiere_rol
from backend.db.session import get_db
from backend.models.orm import TenantBranding

router = APIRouter(prefix="/api/v3/branding", tags=["Branding"])

HEX_RE = re.compile(r"^#[0-9a-fA-F]{6}$")


# ── Schemas locales ──────────────────────────────────────────────────────
class BrandingOut(BaseModel):
    tenant_id:        int
    nombre_comercial: str
    logo_url:         Optional[str] = None
    color_primary:    str
    color_secondary:  str
    color_accent:     str
    nicho:            str
    tema:             str
    tipografia:       str
    categorias_default: list[str] = []


class BrandingUpdate(BaseModel):
    nombre_comercial:  Optional[str] = Field(None, min_length=2, max_length=100)
    logo_url:          Optional[str] = None
    color_primary:     Optional[str] = None
    color_secondary:   Optional[str] = None
    color_accent:      Optional[str] = None
    nicho:             Optional[str] = Field(None, pattern=r"^(restaurante|retail|farmacia|servicio|otro)$")
    tema:              Optional[str] = Field(None, pattern=r"^(dark|light|warm)$")
    tipografia:        Optional[str] = Field(None, pattern=r"^(Inter|Roboto|Poppins|Nunito|Lato)$")
    categorias_default: Optional[list[str]] = None


# ── Default branding (usado si no existe registro aún) ───────────────────
DEFAULT_BRANDING = BrandingOut(
    tenant_id=0,
    nombre_comercial="Mi Negocio",
    color_primary="#8b5cf6",
    color_secondary="#0f172a",
    color_accent="#d946ef",
    nicho="restaurante",
    tema="dark",
    tipografia="Inter",
    categorias_default=[],
)


def _to_out(b: TenantBranding) -> BrandingOut:
    return BrandingOut(
        tenant_id=b.tenant_id,
        nombre_comercial=b.nombre_comercial,
        logo_url=b.logo_url,
        color_primary=b.color_primary or "#8b5cf6",
        color_secondary=b.color_secondary or "#0f172a",
        color_accent=b.color_accent or "#d946ef",
        nicho=b.nicho or "restaurante",
        tema=b.tema or "dark",
        tipografia=b.tipografia or "Inter",
        categorias_default=b.categorias_default or [],
    )


# ─────────────────────────────────────────────────────────────────────────
#  GET — Obtener branding del tenant autenticado
# ─────────────────────────────────────────────────────────────────────────
@router.get("", response_model=BrandingOut)
def get_branding(
    user: dict = Depends(get_current_usuario),
    db:   Session = Depends(get_db),
):
    b = db.query(TenantBranding).filter_by(tenant_id=user["tenant_id"]).first()
    if not b:
        default = DEFAULT_BRANDING.model_copy()
        default.tenant_id = user["tenant_id"]
        return default
    return _to_out(b)


# ─────────────────────────────────────────────────────────────────────────
#  PUT — Actualizar branding (owner o manager)
# ─────────────────────────────────────────────────────────────────────────
@router.put("", response_model=BrandingOut)
def update_branding(
    data: BrandingUpdate,
    user: dict = Depends(requiere_rol(Rol.MANAGER)),
    db:   Session = Depends(get_db),
):
    b = db.query(TenantBranding).filter_by(tenant_id=user["tenant_id"]).first()
    if not b:
        raise HTTPException(status_code=404, detail="Branding no encontrado.")

    # Validar colores hex
    for campo in ("color_primary", "color_secondary", "color_accent"):
        val = getattr(data, campo, None)
        if val is not None and not HEX_RE.match(val):
            raise HTTPException(
                status_code=422,
                detail=f"Color inválido para '{campo}'. Usa formato hex #rrggbb.",
            )

    # Aplicar solo los campos enviados (patch parcial)
    update_data = data.model_dump(exclude_unset=True)
    for key, val in update_data.items():
        setattr(b, key, val)

    db.commit()
    db.refresh(b)
    return _to_out(b)


# ─────────────────────────────────────────────────────────────────────────
#  GET — Branding público (sin auth — para login screen del tenant)
# ─────────────────────────────────────────────────────────────────────────
@router.get("/public/{tenant_id}", response_model=BrandingOut)
def get_branding_public(tenant_id: int, db: Session = Depends(get_db)):
    """Branding público para la pantalla de login de un negocio específico."""
    b = db.query(TenantBranding).filter_by(tenant_id=tenant_id).first()
    if not b:
        raise HTTPException(status_code=404, detail="Negocio no encontrado.")
    return _to_out(b)
