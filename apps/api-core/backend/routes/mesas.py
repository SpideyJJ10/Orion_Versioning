"""
routes/mesas.py — Control de mesas para restaurantes (Módulo M12).

Permite al mesero:
  - Ver el plano de mesas y su estado en tiempo real
  - Abrir una mesa (asignar orden)
  - Cambiar estado (libre → ocupada → cuenta_pedida → libre)
  - Cerrar/limpiar una mesa

El modelo Mesa vive en orm.py. El estado es siempre leído de la DB
(no hay estado en memoria) para que múltiples meseros vean la misma verdad.
"""
from typing import Literal

from fastapi import APIRouter, Depends, HTTPException, Query
from pydantic import BaseModel, Field
from sqlalchemy.orm import Session

from backend.auth_v3 import get_current_usuario
from backend.db.session import get_db
from backend.models.orm import Mesa, Orden, Sucursal

router = APIRouter(prefix="/api/mesas", tags=["Mesas"])

# ── Tipos -------------------------------------------------------------------
EstadoMesa = Literal["libre", "ocupada", "reservada", "cuenta_pedida"]


# ── Schemas -----------------------------------------------------------------
class MesaCreate(BaseModel):
    numero: int = Field(..., ge=1, le=999, description="Número visible de la mesa")
    nombre: str | None = Field(None, max_length=50, description="Nombre custom (ej: 'Terraza 1')")
    capacidad: int = Field(4, ge=1, le=30)
    sucursal_id: str


class MesaUpdate(BaseModel):
    nombre: str | None = None
    capacidad: int | None = Field(None, ge=1, le=30)
    activo: bool | None = None


class MesaEstadoUpdate(BaseModel):
    estado: EstadoMesa
    orden_id: str | None = None      # se envía al OCUPAR (vincular orden)
    notas: str | None = None


class MesaOut(BaseModel):
    id: str
    sucursal_id: str
    numero: int
    nombre: str | None
    capacidad: int
    estado: str
    orden_id: str | None
    notas: str | None
    activo: bool

    model_config = {"from_attributes": True}


# ── Helpers -----------------------------------------------------------------
def _get_mesa(mesa_id: str, tenant_id: int, db: Session) -> Mesa:
    m = db.query(Mesa).filter(
        Mesa.id == mesa_id,
        Mesa.tenant_id == tenant_id,
    ).first()
    if not m:
        raise HTTPException(status_code=404, detail="Mesa no encontrada")
    return m


def _verificar_sucursal(sucursal_id: str, tenant_id: int, db: Session) -> Sucursal:
    s = db.query(Sucursal).filter(
        Sucursal.id == sucursal_id,
        Sucursal.tenant_id == tenant_id,
        Sucursal.activo == True,
    ).first()
    if not s:
        raise HTTPException(status_code=404, detail="Sucursal no encontrada")
    return s


# ── Endpoints ---------------------------------------------------------------

@router.get("", response_model=list[MesaOut])
def listar_mesas(
    sucursal_id: str | None = None,
    solo_activas: bool = True,
    usuario=Depends(get_current_usuario),
    db: Session = Depends(get_db),
):
    """
    Devuelve todas las mesas del tenant (filtradas por sucursal si se indica).
    Refresca el estado en tiempo real — ideal para polling cada 15s desde el frontend.
    """
    q = db.query(Mesa).filter(Mesa.tenant_id == usuario.tenant_id)
    if sucursal_id:
        q = q.filter(Mesa.sucursal_id == sucursal_id)
    if solo_activas:
        q = q.filter(Mesa.activo == True)
    return q.order_by(Mesa.numero).all()


@router.post("", response_model=MesaOut, status_code=201)
def crear_mesa(
    body: MesaCreate,
    usuario=Depends(get_current_usuario),
    db: Session = Depends(get_db),
):
    """
    Crea una nueva mesa. Solo owner o manager pueden añadir mesas.
    """
    if usuario.rol not in ("owner", "manager", "super_admin"):
        raise HTTPException(status_code=403, detail="Sin permiso para crear mesas")

    _verificar_sucursal(body.sucursal_id, usuario.tenant_id, db)

    # Evitar duplicado de número en la misma sucursal
    existente = db.query(Mesa).filter(
        Mesa.sucursal_id == body.sucursal_id,
        Mesa.numero == body.numero,
        Mesa.activo == True,
    ).first()
    if existente:
        raise HTTPException(
            status_code=409,
            detail=f"Ya existe una mesa número {body.numero} en esta sucursal",
        )

    mesa = Mesa(
        tenant_id=usuario.tenant_id,
        sucursal_id=body.sucursal_id,
        numero=body.numero,
        nombre=body.nombre,
        capacidad=body.capacidad,
    )
    db.add(mesa)
    db.commit()
    db.refresh(mesa)
    return mesa


@router.post("/bulk", response_model=list[MesaOut], status_code=201)
def crear_mesas_bulk(
    sucursal_id: str,
    cantidad: int = Query(..., ge=1, le=50),
    capacidad: int = Query(4, ge=1, le=30),
    usuario=Depends(get_current_usuario),
    db: Session = Depends(get_db),
):
    """
    Crea N mesas de una sola vez (ideal para el onboarding del restaurante).
    Numeradas automáticamente desde el siguiente número disponible.
    """
    if usuario.rol not in ("owner", "manager", "super_admin"):
        raise HTTPException(status_code=403, detail="Sin permiso")

    _verificar_sucursal(sucursal_id, usuario.tenant_id, db)

    # Determinar el siguiente número libre
    ultima = db.query(Mesa).filter(
        Mesa.sucursal_id == sucursal_id,
        Mesa.activo == True,
    ).order_by(Mesa.numero.desc()).first()
    inicio = (ultima.numero + 1) if ultima else 1

    nuevas = []
    for i in range(cantidad):
        m = Mesa(
            tenant_id=usuario.tenant_id,
            sucursal_id=sucursal_id,
            numero=inicio + i,
            capacidad=capacidad,
        )
        db.add(m)
        nuevas.append(m)

    db.commit()
    for m in nuevas:
        db.refresh(m)
    return nuevas


@router.get("/{mesa_id}", response_model=MesaOut)
def obtener_mesa(
    mesa_id: str,
    usuario=Depends(get_current_usuario),
    db: Session = Depends(get_db),
):
    return _get_mesa(mesa_id, usuario.tenant_id, db)


@router.patch("/{mesa_id}", response_model=MesaOut)
def actualizar_mesa(
    mesa_id: str,
    body: MesaUpdate,
    usuario=Depends(get_current_usuario),
    db: Session = Depends(get_db),
):
    """Edita nombre o capacidad de una mesa."""
    if usuario.rol not in ("owner", "manager", "super_admin"):
        raise HTTPException(status_code=403, detail="Sin permiso")

    mesa = _get_mesa(mesa_id, usuario.tenant_id, db)
    for field, val in body.model_dump(exclude_none=True).items():
        setattr(mesa, field, val)
    db.commit()
    db.refresh(mesa)
    return mesa


@router.patch("/{mesa_id}/estado", response_model=MesaOut)
def cambiar_estado_mesa(
    mesa_id: str,
    body: MesaEstadoUpdate,
    usuario=Depends(get_current_usuario),
    db: Session = Depends(get_db),
):
    """
    Cambia el estado de una mesa. El mesero lo usa para:
      - OCUPAR: pasar de libre → ocupada (se puede vincular orden_id)
      - PEDIR CUENTA: ocupada → cuenta_pedida
      - LIBERAR: cualquier estado → libre (limpia orden_id)

    Transiciones válidas:
      libre          → ocupada | reservada
      ocupada        → cuenta_pedida | libre
      cuenta_pedida  → libre
      reservada      → ocupada | libre
    """
    mesa = _get_mesa(mesa_id, usuario.tenant_id, db)

    # Validar transición
    TRANSICIONES_VALIDAS = {
        "libre":         {"ocupada", "reservada"},
        "ocupada":       {"cuenta_pedida", "libre"},
        "cuenta_pedida": {"libre"},
        "reservada":     {"ocupada", "libre"},
    }
    if body.estado not in TRANSICIONES_VALIDAS.get(mesa.estado, set()):
        raise HTTPException(
            status_code=422,
            detail=(
                f"Transición inválida: {mesa.estado} → {body.estado}. "
                f"Válidas: {TRANSICIONES_VALIDAS.get(mesa.estado)}"
            ),
        )

    # Validar orden si se vincula
    if body.orden_id:
        orden = db.query(Orden).filter(
            Orden.id == body.orden_id,
            Orden.tenant_id == usuario.tenant_id,
        ).first()
        if not orden:
            raise HTTPException(status_code=404, detail="Orden no encontrada")

    mesa.estado = body.estado
    mesa.notas = body.notas

    # Al liberar, desvinculamos la orden
    if body.estado == "libre":
        mesa.orden_id = None
        mesa.notas = None
    elif body.orden_id:
        mesa.orden_id = body.orden_id

    db.commit()
    db.refresh(mesa)
    return mesa


@router.delete("/{mesa_id}", status_code=204)
def eliminar_mesa(
    mesa_id: str,
    usuario=Depends(get_current_usuario),
    db: Session = Depends(get_db),
):
    """Soft-delete: marca la mesa como inactiva (no borra los datos históricos)."""
    if usuario.rol not in ("owner", "manager", "super_admin"):
        raise HTTPException(status_code=403, detail="Sin permiso")

    mesa = _get_mesa(mesa_id, usuario.tenant_id, db)
    if mesa.estado == "ocupada":
        raise HTTPException(
            status_code=409,
            detail="No se puede eliminar una mesa ocupada. Libérala primero.",
        )
    mesa.activo = False
    db.commit()
