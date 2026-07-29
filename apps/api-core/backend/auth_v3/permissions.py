"""
permissions.py — Roles y dependencies FastAPI para control de acceso.
"""
from enum import Enum

from fastapi import Depends, HTTPException, status


class Rol(str, Enum):
    """Roles del sistema, ordenados jerárquicamente (mayor privilegio primero)."""
    SUPER_ADMIN = "super_admin"   # Staff de Orion (global)
    OWNER       = "owner"         # Dueño del negocio (tenant)
    MANAGER     = "manager"       # Gerente de sucursal
    INVENTARIO  = "inventario"    # Encargado de productos/stock
    CAJERO      = "cajero"        # Operador de POS


# Nivel numérico para comparaciones. Más alto = más privilegio.
JERARQUIA: dict[Rol, int] = {
    Rol.SUPER_ADMIN: 100,
    Rol.OWNER:       80,
    Rol.MANAGER:     60,
    Rol.INVENTARIO:  40,
    Rol.CAJERO:      20,
}


def requiere_rol(minimo: Rol):
    """Dependency factory — exige que el usuario autenticado tenga rol >= minimo.

    Uso:
        @router.delete("/api/ordenes/{id}")
        def anular(id: str, user = Depends(requiere_rol(Rol.MANAGER))):
            ...
    """
    # Import local para evitar circular
    from backend.auth_v3.tokens import get_current_usuario

    def _check(user: dict = Depends(get_current_usuario)) -> dict:
        rol_user = user.get("rol", "")
        try:
            nivel_user = JERARQUIA[Rol(rol_user)]
        except (ValueError, KeyError):
            nivel_user = 0

        if nivel_user < JERARQUIA[minimo]:
            raise HTTPException(
                status_code=status.HTTP_403_FORBIDDEN,
                detail=f"Acción no permitida. Requiere rol '{minimo.value}' o superior.",
            )
        return user
    return _check


def requiere_tenant_activo(user: dict = Depends(lambda: None)):
    """Verifica que el tenant del usuario tenga plan activo.

    Se usa en rutas que requieren suscripción al día (ej. generar reportes).
    """
    from backend.auth_v3.tokens import get_current_usuario
    from backend.db.session import SessionLocal
    from backend.models.orm import Tenant

    def _check(user: dict = Depends(get_current_usuario)):
        db = SessionLocal()
        try:
            tenant = db.query(Tenant).filter_by(id=user["tenant_id"]).first()
            if not tenant or not tenant.plan_activo:
                raise HTTPException(
                    status_code=status.HTTP_402_PAYMENT_REQUIRED,
                    detail="El plan de tu negocio está suspendido. Contacta soporte.",
                )
            return user
        finally:
            db.close()
    return _check
