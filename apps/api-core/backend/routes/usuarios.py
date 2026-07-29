"""
routes/usuarios.py — Gestión de usuarios operativos por parte del owner/manager.

Permisos:
  - OWNER puede crear/editar/eliminar cualquier rol menor (manager, cajero, inventario)
  - MANAGER puede crear/editar cajero e inventario
  - CAJERO e INVENTARIO: solo lectura de sí mismos (GET /me vía /api/v3/auth/me)
"""
from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy.orm import Session

from backend.auth_v3 import Rol, hash_password, requiere_rol
from backend.db.session import get_db
from backend.models.orm import Usuario
from backend.schemas import CrearUsuarioRequest, UsuarioPublico

router = APIRouter(prefix="/api/v3/usuarios", tags=["Usuarios"])


@router.get("", response_model=list[UsuarioPublico])
def listar_usuarios(
    user: dict = Depends(requiere_rol(Rol.MANAGER)),
    db:   Session = Depends(get_db),
):
    """Lista usuarios del tenant actual (solo manager o superior)."""
    usuarios = db.query(Usuario).filter_by(
        tenant_id=user["tenant_id"], activo=True
    ).all()
    return [
        UsuarioPublico(
            id=u.id, email=u.email, nombre=u.nombre, rol=u.rol,
            tenant_id=u.tenant_id, sucursal_id=u.sucursal_id,
        )
        for u in usuarios
    ]


@router.post("", response_model=UsuarioPublico, status_code=status.HTTP_201_CREATED)
def crear_usuario(
    data: CrearUsuarioRequest,
    user: dict = Depends(requiere_rol(Rol.MANAGER)),
    db:   Session = Depends(get_db),
):
    """Crea un usuario operativo dentro del tenant del solicitante."""
    # Normalizar email a minúsculas (login también normaliza)
    email_normalizado = data.email.strip().lower()

    # Manager no puede crear otro manager (solo owner puede)
    if data.rol == Rol.MANAGER.value and user["rol"] != Rol.OWNER.value:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Solo el propietario puede crear usuarios con rol 'manager'.",
        )

    # Verificar email único dentro del tenant
    existente = db.query(Usuario).filter_by(
        tenant_id=user["tenant_id"], email=email_normalizado
    ).first()
    if existente:
        raise HTTPException(
            status_code=status.HTTP_409_CONFLICT,
            detail="Ya existe un usuario con ese correo en tu negocio.",
        )

    # Verificar PIN único dentro del tenant (si se envía)
    if data.pin:
        pin_existente = db.query(Usuario).filter_by(
            tenant_id=user["tenant_id"], pin=data.pin
        ).first()
        if pin_existente:
            raise HTTPException(
                status_code=status.HTTP_409_CONFLICT,
                detail="Ese PIN ya está en uso. Elige otro.",
            )

    nuevo = Usuario(
        tenant_id     = user["tenant_id"],
        email         = email_normalizado,
        password_hash = hash_password(data.password),
        nombre        = data.nombre,
        rol           = data.rol,
        sucursal_id   = data.sucursal_id,
        pin           = data.pin,
        activo        = True,
    )
    db.add(nuevo)
    db.commit()
    db.refresh(nuevo)

    return UsuarioPublico(
        id=nuevo.id, email=nuevo.email, nombre=nuevo.nombre, rol=nuevo.rol,
        tenant_id=nuevo.tenant_id, sucursal_id=nuevo.sucursal_id,
    )


@router.delete("/{usuario_id}", status_code=status.HTTP_204_NO_CONTENT)
def desactivar_usuario(
    usuario_id: int,
    user: dict = Depends(requiere_rol(Rol.OWNER)),
    db:   Session = Depends(get_db),
):
    """Desactiva un usuario (soft delete). Solo owner."""
    u = db.query(Usuario).filter_by(id=usuario_id, tenant_id=user["tenant_id"]).first()
    if not u:
        raise HTTPException(status_code=404, detail="Usuario no encontrado.")
    if u.id == user["usuario_id"]:
        raise HTTPException(status_code=400, detail="No puedes desactivarte a ti mismo.")
    u.activo = False
    db.commit()
