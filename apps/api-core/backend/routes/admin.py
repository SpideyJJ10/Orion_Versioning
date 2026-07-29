"""
routes/admin.py — Panel de super-administrador

Endpoints protegidos por es_admin=True en el JWT.
Solo accesibles con el token emitido por POST /api/admin/login.
"""
from datetime import datetime
from typing import Optional

from fastapi import APIRouter, Depends, HTTPException, status
from pydantic import BaseModel
from sqlalchemy.orm import Session

from backend.auth_v3 import (
    crear_access_token,
    get_current_usuario,
    verify_password,
)
from backend.db.session import get_db
from backend.models.orm import Tenant, Usuario
from backend.schemas import LoginRequest, TokenResponse

router = APIRouter(prefix="/api/admin", tags=["Admin"])


# ── Dependency: only super-admin role can access these endpoints ──────────
def get_admin_user(user: dict = Depends(get_current_usuario)) -> dict:
    if not user.get("es_admin"):
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Acceso restringido a administradores",
        )
    return user


# ── Schema PATCH ──────────────────────────────────────────────────────────
class PatchTenantBody(BaseModel):
    plan_activo:       Optional[bool]     = None
    fecha_vencimiento: Optional[datetime] = None
    nombre:            Optional[str]      = None
    email:             Optional[str]      = None
    plan:              Optional[str]      = None


# ── Admin-only login ──────────────────────────────────────────────────────
# Validates Tenant credentials (legacy admin contract) but issues a v3 JWT for
# the matching super_admin Usuario row. This keeps the public API stable while
# letting all downstream routes use the unified `get_current_usuario` dep.
@router.post("/login", response_model=TokenResponse)
def admin_login(data: LoginRequest, db: Session = Depends(get_db)):
    email = data.email.strip().lower()
    tenant = db.query(Tenant).filter(Tenant.email == email).first()
    if not tenant or not verify_password(data.password, tenant.password_hash):
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Credenciales incorrectas",
        )
    if not tenant.es_admin:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Acceso restringido a administradores",
        )
    usuario = (
        db.query(Usuario)
        .filter_by(tenant_id=tenant.id, rol="super_admin", activo=True)
        .first()
    )
    if not usuario:
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Usuario super_admin no inicializado. Reinicia el servidor.",
        )
    token = crear_access_token(
        usuario_id=usuario.id,
        tenant_id=usuario.tenant_id,
        rol=usuario.rol,
        email=usuario.email,
        sucursal_id=usuario.sucursal_id,
    )
    return TokenResponse(access_token=token, nombre=tenant.nombre, es_admin=True)


# ── GET /tenants ──────────────────────────────────────────────────────────
@router.get("/tenants")
def listar_tenants(
    db: Session = Depends(get_db),
    _: dict = Depends(get_admin_user),
):
    tenants = db.query(Tenant).order_by(Tenant.creado_en.desc()).all()
    return [
        {
            "id":                t.id,
            "email":             t.email,
            "nombre":            t.nombre,
            "plan":              t.plan,
            "plan_activo":       t.plan_activo,
            "fecha_vencimiento": t.fecha_vencimiento.isoformat() if t.fecha_vencimiento else None,
            "creado_en":         t.creado_en.isoformat() if t.creado_en else None,
        }
        for t in tenants
    ]


# ── PATCH /tenants/{id} ───────────────────────────────────────────────────
@router.patch("/tenants/{tenant_id}")
def actualizar_tenant(
    tenant_id: int,
    body: PatchTenantBody,
    db: Session = Depends(get_db),
    _: dict = Depends(get_admin_user),
):
    tenant = db.query(Tenant).filter(Tenant.id == tenant_id).first()
    if not tenant:
        raise HTTPException(status_code=404, detail="Tenant no encontrado")

    # Validar email único si se está actualizando
    if body.email is not None and body.email != tenant.email:
        existing = db.query(Tenant).filter(Tenant.email == body.email.strip().lower()).first()
        if existing:
            raise HTTPException(status_code=422, detail="Ya existe un tenant con ese correo")
        tenant.email = body.email.strip().lower()

    if body.nombre is not None:
        tenant.nombre = body.nombre.strip()

    if body.plan is not None:
        tenant.plan = body.plan.strip().lower()

    if body.plan_activo is not None:
        tenant.plan_activo = body.plan_activo

    # model_fields_set distingue "no enviado" de "enviado como null"
    if "fecha_vencimiento" in body.model_fields_set:
        tenant.fecha_vencimiento = body.fecha_vencimiento

    db.commit()
    db.refresh(tenant)
    return {
        "id":                tenant.id,
        "nombre":            tenant.nombre,
        "email":             tenant.email,
        "plan":              tenant.plan,
        "plan_activo":       tenant.plan_activo,
        "fecha_vencimiento": tenant.fecha_vencimiento.isoformat() if tenant.fecha_vencimiento else None,
    }


# ── DELETE /tenants/{id} ──────────────────────────────────────────────────
@router.delete("/tenants/{tenant_id}")
def eliminar_tenant(
    tenant_id: int,
    db: Session = Depends(get_db),
    _: dict = Depends(get_admin_user),
):
    """
    Elimina permanentemente un tenant y todos sus datos asociados.
    Esta acción no se puede deshacer.
    """
    tenant = db.query(Tenant).filter(Tenant.id == tenant_id).first()
    if not tenant:
        raise HTTPException(status_code=404, detail="Tenant no encontrado")

    # Prevenir eliminación del super admin
    if tenant.es_admin:
        raise HTTPException(status_code=403, detail="No se puede eliminar la cuenta de super administrador")

    nombre = tenant.nombre
    db.delete(tenant)
    db.commit()

    return {
        "message": f"Tenant '{nombre}' eliminado permanentemente",
        "id": tenant_id
    }
