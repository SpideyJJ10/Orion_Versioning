"""
routes/onboarding.py — Tracking del tutorial interactivo.

Endpoints:
  GET  /api/v3/onboarding          → Progreso actual del onboarding
  PATCH /api/v3/onboarding/{paso}  → Marcar paso como completado
  POST /api/v3/onboarding/skip     → Saltar el tutorial
"""
from datetime import datetime, timezone

from fastapi import APIRouter, Depends, HTTPException
from pydantic import BaseModel
from sqlalchemy.orm import Session

from backend.auth_v3 import get_current_usuario
from backend.db.session import get_db
from backend.models.orm import OnboardingProgress

router = APIRouter(prefix="/api/v3/onboarding", tags=["Onboarding"])


class OnboardingOut(BaseModel):
    tenant_id:          int
    perfil_configurado: bool
    primer_producto:    bool
    primera_venta:      bool
    saltado:            bool
    porcentaje:         int
    completado:         bool


def _to_out(o: OnboardingProgress) -> OnboardingOut:
    return OnboardingOut(
        tenant_id=o.tenant_id,
        perfil_configurado=o.perfil_configurado,
        primer_producto=o.primer_producto,
        primera_venta=o.primera_venta,
        saltado=o.saltado,
        porcentaje=o.porcentaje,
        completado=o.completado_en is not None,
    )


def _check_complete(o: OnboardingProgress):
    """Si todos los pasos están hechos, marca como completado."""
    if o.perfil_configurado and o.primer_producto and o.primera_venta:
        if not o.completado_en:
            o.completado_en = datetime.now(timezone.utc)


@router.get("", response_model=OnboardingOut)
def get_progreso(
    user: dict = Depends(get_current_usuario),
    db:   Session = Depends(get_db),
):
    o = db.query(OnboardingProgress).filter_by(tenant_id=user["tenant_id"]).first()
    if not o:
        o = OnboardingProgress(tenant_id=user["tenant_id"])
        db.add(o)
        db.commit()
        db.refresh(o)
    return _to_out(o)


@router.patch("/{paso}", response_model=OnboardingOut)
def marcar_paso(
    paso: str,
    user: dict = Depends(get_current_usuario),
    db:   Session = Depends(get_db),
):
    """Marca un paso como completado. Valores: perfil, producto, venta."""
    campos = {
        "perfil":   "perfil_configurado",
        "producto": "primer_producto",
        "venta":    "primera_venta",
    }
    if paso not in campos:
        raise HTTPException(
            status_code=400,
            detail=f"Paso inválido '{paso}'. Usa: perfil, producto, venta.",
        )

    o = db.query(OnboardingProgress).filter_by(tenant_id=user["tenant_id"]).first()
    if not o:
        o = OnboardingProgress(tenant_id=user["tenant_id"])
        db.add(o)

    setattr(o, campos[paso], True)
    _check_complete(o)
    db.commit()
    db.refresh(o)
    return _to_out(o)


@router.post("/skip", response_model=OnboardingOut)
def saltar_onboarding(
    user: dict = Depends(get_current_usuario),
    db:   Session = Depends(get_db),
):
    """El usuario decidió saltar el tutorial."""
    o = db.query(OnboardingProgress).filter_by(tenant_id=user["tenant_id"]).first()
    if not o:
        o = OnboardingProgress(tenant_id=user["tenant_id"])
        db.add(o)
    o.saltado = True
    db.commit()
    db.refresh(o)
    return _to_out(o)
