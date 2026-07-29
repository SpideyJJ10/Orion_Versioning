"""
routes/negocio.py — Configuración y ajustes propios del negocio (Tenant).

Endpoints:
  GET  /api/v3/negocio/metodos-pago → Obtener métodos de pago
  POST /api/v3/negocio/metodos-pago → Actualizar métodos de pago
"""

from fastapi import APIRouter, Depends, HTTPException, status
from pydantic import BaseModel
from sqlalchemy.orm import Session

from backend.auth_v3 import Rol, get_current_usuario, requiere_rol
from backend.db.session import get_db
from backend.models.orm import Tenant

router = APIRouter(prefix="/api/v3/negocio", tags=["Negocio"])

class MetodosPagoUpdate(BaseModel):
    metodos_pago: list[str]

@router.get("/metodos-pago", response_model=list[str])
def get_metodos_pago(
    usuario: dict = Depends(get_current_usuario),
    db: Session = Depends(get_db)
):
    """Obtiene los métodos de pago configurados por el negocio."""
    tenant = db.query(Tenant).filter(Tenant.id == usuario["tenant_id"]).first()
    if not tenant:
        raise HTTPException(status_code=404, detail="Negocio no encontrado")
    
    # Defaults a Efectivo y Tarjeta si no tiene
    return tenant.metodos_pago or ["Efectivo", "Tarjeta"]

@router.post("/metodos-pago", response_model=list[str])
def update_metodos_pago(
    payload: MetodosPagoUpdate,
    usuario: dict = Depends(requiere_rol(Rol.OWNER)),
    db: Session = Depends(get_db)
):
    """Actualiza los métodos de pago (solo dueño o admin)."""
    tenant = db.query(Tenant).filter(Tenant.id == usuario["tenant_id"]).first()
    if not tenant:
        raise HTTPException(status_code=404, detail="Negocio no encontrado")
    
    tenant.metodos_pago = payload.metodos_pago
    db.commit()
    
    return tenant.metodos_pago
