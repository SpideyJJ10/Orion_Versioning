"""
routes/auth_v3.py — Endpoints de autenticación v3 con roles y refresh tokens.
"""
import os
from datetime import datetime, timezone

from fastapi import APIRouter, Depends, HTTPException, status
from pydantic import BaseModel, Field
from sqlalchemy.orm import Session

from backend.auth_v3 import (
    Rol,
    decodificar_token,
    emitir_par_tokens,
    get_current_usuario,
    hash_password,
    verify_password,
)
from backend.db.session import get_db
from backend.core.security import assert_not_locked, brute_force_tracker, refresh_registry
from backend.models.orm import OnboardingProgress, Sucursal, Tenant, TenantBranding, Usuario
from backend.schemas import (
    CrearUsuarioRequest,
    LoginPinRequest,
    LoginRequest,
    RefreshRequest,
    RegisterV3Request,
    TokenPair,
    UsuarioPublico,
)

router = APIRouter(prefix="/api/v3/auth", tags=["Auth v3"])
# ─────────────────────────────────────────────────────────────────────────
@router.post("/register", response_model=TokenPair, status_code=status.HTTP_201_CREATED)
def registrar_negocio(data: RegisterV3Request, db: Session = Depends(get_db)):
    """Registra un nuevo negocio completo (atomico)."""
    # Normalizar email a minúsculas (login también normaliza)
    email = data.email.strip().lower()

    # 1) Validar que el email no exista en Tenants ni en Usuarios
    if db.query(Tenant).filter_by(email=email).first():
        raise HTTPException(
            status_code=status.HTTP_409_CONFLICT,
            detail="Este correo ya está registrado como negocio.",
        )
    if db.query(Usuario).filter_by(email=email).first():
        raise HTTPException(
            status_code=status.HTTP_409_CONFLICT,
            detail="Este correo ya está en uso.",
        )

    hashed = hash_password(data.password)

    try:
        # 2) Crear Tenant (negocio)
        tenant = Tenant(
            email         = email,
            password_hash = hashed,
            nombre        = data.nombre_comercial,
            propietario   = data.nombre_propietario,
            telefono      = data.telefono,
            plan          = "starter",
            plan_activo   = True,
        )
        db.add(tenant)
        db.flush()  # obtiene tenant.id sin commit

        # 3) Crear Branding default con nicho-specific categorías
        categorias_seed = _categorias_por_nicho(data.nicho)
        db.add(TenantBranding(
            tenant_id          = tenant.id,
            nombre_comercial   = data.nombre_comercial,
            nicho              = data.nicho,
            categorias_default = categorias_seed,
        ))

        # 4) Crear tracking de onboarding
        db.add(OnboardingProgress(tenant_id=tenant.id))

        # 5) Crear sucursal default "Principal" para que el POS sea operativo desde día 1
        sucursal_principal = Sucursal(
            tenant_id = tenant.id,
            nombre    = "Principal",
        )
        db.add(sucursal_principal)
        db.flush()  # obtiene sucursal.id sin commit

        # 6) Crear Usuario owner asignado a la sucursal principal
        owner = Usuario(
            tenant_id     = tenant.id,
            email         = email,
            password_hash = hashed,
            nombre        = data.nombre_propietario,
            rol           = Rol.OWNER.value,
            sucursal_id   = sucursal_principal.id,
            activo        = True,
        )
        db.add(owner)
        db.commit()
        db.refresh(owner)

    except Exception as e:
        db.rollback()
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Error al crear el negocio: {str(e)}",
        )

    return emitir_par_tokens(owner)


# ─────────────────────────────────────────────────────────────────────────
#  LOGIN con email + contraseña (cualquier rol)
# ─────────────────────────────────────────────────────────────────────────
@router.post("/login", response_model=TokenPair)
def login(data: LoginRequest, db: Session = Depends(get_db)):
    """Login para cualquier usuario (owner, manager, cajero, inventario, super_admin)."""
    email = data.email.strip().lower()
    assert_not_locked(email)
    user = db.query(Usuario).filter_by(email=email, activo=True).first()

    if not user or not verify_password(data.password, user.password_hash):
        brute_force_tracker.record_failure(email)
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Correo o contraseña incorrectos.",
        )

    # Verificar que el tenant no esté suspendido (excepto super_admin)
    if user.rol != Rol.SUPER_ADMIN.value:
        tenant = db.query(Tenant).filter_by(id=user.tenant_id).first()
        if not tenant or not tenant.plan_activo:
            raise HTTPException(
                status_code=status.HTTP_402_PAYMENT_REQUIRED,
                detail="El plan de tu negocio está suspendido. Contacta soporte.",
            )

    # Registrar último login (auditoría)
    user.ultimo_login = datetime.now(timezone.utc)
    db.commit()
    brute_force_tracker.record_success(email)

    return emitir_par_tokens(user)


# ─────────────────────────────────────────────────────────────────────────
#  LOGIN con PIN (cajeros — modo táctil rápido)
# ─────────────────────────────────────────────────────────────────────────
@router.post("/login-pin", response_model=TokenPair)
def login_por_pin(data: LoginPinRequest, db: Session = Depends(get_db)):
    """Login rápido con PIN de 4-6 dígitos. Típicamente usado por cajeros.

    Requiere conocer el tenant_id (enviado desde tablet configurada).
    """
    lock_key = f"tenant:{data.tenant_id}:pin:{data.pin}"
    assert_not_locked(lock_key)
    user = db.query(Usuario).filter_by(
        tenant_id = data.tenant_id,
        pin       = data.pin,
        activo    = True,
    ).first()

    if not user:
        brute_force_tracker.record_failure(lock_key)
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="PIN incorrecto.",
        )

    user.ultimo_login = datetime.now(timezone.utc)
    db.commit()
    brute_force_tracker.record_success(lock_key)
    return emitir_par_tokens(user)


# ─────────────────────────────────────────────────────────────────────────
#  REFRESH TOKEN
# ─────────────────────────────────────────────────────────────────────────
@router.post("/refresh", response_model=TokenPair)
def refrescar_tokens(data: RefreshRequest, db: Session = Depends(get_db)):
    """Renueva access_token (y emite nuevo refresh) usando refresh_token válido."""
    payload = decodificar_token(data.refresh_token, tipo_esperado="refresh")
    usuario_id = int(payload["sub"])
    jti = payload.get("jti")
    if not jti or not refresh_registry.consumir(usuario_id, jti):
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Refresh token reutilizado o revocado. Inicia sesion nuevamente.",
        )

    user = db.query(Usuario).filter_by(id=usuario_id, activo=True).first()
    if not user:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Usuario no encontrado o desactivado.",
        )

    return emitir_par_tokens(user)


# ─────────────────────────────────────────────────────────────────────────
#  INFO DEL USUARIO AUTENTICADO
# ─────────────────────────────────────────────────────────────────────────
@router.get("/me", response_model=UsuarioPublico)
def info_actual(user: dict = Depends(get_current_usuario), db: Session = Depends(get_db)):
    """Devuelve los datos del usuario autenticado."""
    u = db.query(Usuario).filter_by(id=user["usuario_id"]).first()
    if not u:
        raise HTTPException(status_code=404, detail="Usuario no encontrado.")
    return UsuarioPublico(
        id=u.id, email=u.email, nombre=u.nombre, rol=u.rol,
        tenant_id=u.tenant_id, sucursal_id=u.sucursal_id,
    )


class VerifyAdminPinRequest(BaseModel):
    pin: str = Field(..., min_length=4, max_length=6)


@router.post("/verify-admin-pin")
def verificar_admin_pin(
    data: VerifyAdminPinRequest,
    user: dict = Depends(get_current_usuario),
    db: Session = Depends(get_db),
):
    """Verifica si un PIN pertenece a un Administrador/Owner del tenant o al ADMIN_PIN global."""
    admin_pin_env = os.getenv("ADMIN_PIN", "").strip()
    if admin_pin_env and data.pin == admin_pin_env:
        return {"ok": True}

    match = (
        db.query(Usuario)
        .filter(
            Usuario.tenant_id == user["tenant_id"],
            Usuario.pin == data.pin,
            Usuario.rol.in_(["owner", "manager", "super_admin"]),
            Usuario.activo == True,  # noqa: E712
        )
        .first()
    )
    if not match:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="PIN de Administrador incorrecto.",
        )
    return {"ok": True}


# ─────────────────────────────────────────────────────────────────────────
#  HELPERS internos
# ─────────────────────────────────────────────────────────────────────────
def _categorias_por_nicho(nicho: str) -> list[str]:
    """Retorna categorías iniciales sugeridas según el tipo de negocio."""
    presets = {
        "restaurante": ["Bebidas", "Entradas", "Platos fuertes", "Postres", "Extras"],
        "retail":      ["Hombre", "Mujer", "Niños", "Accesorios", "Ofertas"],
        "farmacia":    ["Analgésicos", "Vitaminas", "Higiene", "Cuidado personal", "Bebés"],
        "servicio":    ["Servicios básicos", "Servicios premium", "Productos", "Paquetes"],
        "otro":        ["General"],
    }
    return presets.get(nicho, ["General"])
