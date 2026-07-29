"""
routes/sucursales.py — CRUD de sucursales (locales del negocio)
Cada tenant puede tener múltiples sucursales.
Productos, categorías y ventas están aislados por sucursal.
"""
from fastapi import APIRouter, HTTPException, Depends
from sqlalchemy.orm import Session

from backend.db.session import get_db
from backend.models.orm import Sucursal
from backend.schemas import SucursalCreate, SucursalOut
from backend.auth_v3 import get_current_usuario as get_current_user

router = APIRouter(prefix="/api/sucursales", tags=["Sucursales"])


@router.get("", response_model=list[SucursalOut])
def listar_sucursales(
    user: dict    = Depends(get_current_user),
    db:   Session = Depends(get_db),
):
    """Retorna todas las sucursales activas del tenant."""
    return (
        db.query(Sucursal)
        .filter(
            Sucursal.tenant_id == user["tenant_id"],
            Sucursal.activo    == True,
        )
        .order_by(Sucursal.nombre)
        .all()
    )


@router.post("", response_model=SucursalOut, status_code=201)
def crear_sucursal(
    data: SucursalCreate,
    user: dict    = Depends(get_current_user),
    db:   Session = Depends(get_db),
):
    """Crea una nueva sucursal para el tenant autenticado."""
    existente = db.query(Sucursal).filter(
        Sucursal.tenant_id == user["tenant_id"],
        Sucursal.nombre.ilike(data.nombre),
        Sucursal.activo    == True,
    ).first()
    if existente:
        raise HTTPException(status_code=400, detail="Ya existe una sucursal con ese nombre")

    sucursal = Sucursal(
        tenant_id = user["tenant_id"],
        nombre    = data.nombre,
    )
    db.add(sucursal)
    db.commit()
    db.refresh(sucursal)
    return sucursal


@router.put("/{sucursal_id}", response_model=SucursalOut)
def editar_sucursal(
    sucursal_id: str,
    data: SucursalCreate,
    user: dict    = Depends(get_current_user),
    db:   Session = Depends(get_db),
):
    """Renombra una sucursal del tenant."""
    sucursal = db.query(Sucursal).filter(
        Sucursal.id        == sucursal_id,
        Sucursal.tenant_id == user["tenant_id"],
    ).first()
    if not sucursal:
        raise HTTPException(status_code=404, detail="Sucursal no encontrada")

    sucursal.nombre = data.nombre
    db.commit()
    db.refresh(sucursal)
    return sucursal


@router.delete("/{sucursal_id}", status_code=204)
def eliminar_sucursal(
    sucursal_id: str,
    user: dict    = Depends(get_current_user),
    db:   Session = Depends(get_db),
):
    """Soft-delete de sucursal. No se puede eliminar si es la última activa."""
    sucursal = db.query(Sucursal).filter(
        Sucursal.id        == sucursal_id,
        Sucursal.tenant_id == user["tenant_id"],
    ).first()
    if not sucursal:
        raise HTTPException(status_code=404, detail="Sucursal no encontrada")

    activas = db.query(Sucursal).filter(
        Sucursal.tenant_id == user["tenant_id"],
        Sucursal.activo    == True,
    ).count()
    if activas <= 1:
        raise HTTPException(
            status_code=400,
            detail="Debes tener al menos una sucursal activa",
        )

    sucursal.activo = False
    db.commit()
