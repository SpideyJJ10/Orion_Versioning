"""
routes/categorias.py — CRUD completo de categorías por sucursal
Solo admin puede editar/eliminar categorías.
"""
from typing import Optional

from fastapi import APIRouter, Depends, HTTPException, Query, status
from sqlalchemy.orm import Session

from backend.db.session import get_db
from backend.models.orm import Categoria, Producto
from backend.schemas import CategoriaCreate, CategoriaOut, CategoriaUpdate
from backend.auth_v3 import get_current_usuario as get_current_user

router = APIRouter(prefix="/api/categorias", tags=["Categorías"])


@router.get("", response_model=list[CategoriaOut])
def listar_categorias(
    sucursal_id: Optional[str] = Query(None, description="ID de la sucursal"),
    user: dict    = Depends(get_current_user),
    db:   Session = Depends(get_db),
):
    """Retorna categorías activas de la sucursal indicada."""
    if not sucursal_id:
        return []

    return (
        db.query(Categoria)
        .filter(
            Categoria.tenant_id   == user["tenant_id"],
            Categoria.sucursal_id == sucursal_id,
            Categoria.activo      == True,
        )
        .all()
    )


@router.post("", response_model=CategoriaOut, status_code=201)
def crear_categoria(
    data: CategoriaCreate,
    user: dict    = Depends(get_current_user),
    db:   Session = Depends(get_db),
):
    """
    Crea una categoría nueva en la sucursal o reactiva una inactiva con el mismo nombre.
    Las categorías son independientes por sucursal.
    """
    nombre_norm = data.nombre.strip().lower()

    existente = db.query(Categoria).filter(
        Categoria.tenant_id   == user["tenant_id"],
        Categoria.sucursal_id == data.sucursal_id,
        Categoria.nombre.ilike(nombre_norm),
    ).first()

    if existente:
        if not existente.activo:
            existente.activo = True
            db.commit()
            db.refresh(existente)
        return existente

    categoria = Categoria(
        tenant_id   = user["tenant_id"],
        sucursal_id = data.sucursal_id,
        nombre      = data.nombre.strip(),
    )
    db.add(categoria)
    db.commit()
    db.refresh(categoria)
    return categoria


@router.put("/{categoria_id}", response_model=CategoriaOut)
def editar_categoria(
    categoria_id: str,
    data: CategoriaUpdate,
    user: dict    = Depends(get_current_user),
    db:   Session = Depends(get_db),
):
    """Edita el nombre de una categoría. Solo admins."""
    if not user.get("es_admin"):
        raise HTTPException(status_code=status.HTTP_403_FORBIDDEN, detail="Solo administradores pueden editar categorías")

    cat = db.query(Categoria).filter(
        Categoria.id        == categoria_id,
        Categoria.tenant_id == user["tenant_id"],
    ).first()
    if not cat:
        raise HTTPException(status_code=404, detail="Categoría no encontrada")

    cat.nombre = data.nombre
    db.commit()
    db.refresh(cat)
    return cat


@router.delete("/{categoria_id}", status_code=204)
def eliminar_categoria(
    categoria_id: str,
    user: dict    = Depends(get_current_user),
    db:   Session = Depends(get_db),
):
    """Elimina (soft delete) una categoría. Solo admins."""
    if not user.get("es_admin"):
        raise HTTPException(status_code=status.HTTP_403_FORBIDDEN, detail="Solo administradores pueden eliminar categorías")

    cat = db.query(Categoria).filter(
        Categoria.id        == categoria_id,
        Categoria.tenant_id == user["tenant_id"],
    ).first()
    if not cat:
        raise HTTPException(status_code=404, detail="Categoría no encontrada")

    # Verificar si hay productos activos en esta categoría EN ESTA SUCURSAL
    productos_activos = db.query(Producto).filter(
        Producto.tenant_id   == user["tenant_id"],
        Producto.sucursal_id == cat.sucursal_id,
        Producto.categoria   == cat.nombre,
        Producto.activo      == True,
    ).count()

    if productos_activos > 0:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=f"No se puede eliminar: hay {productos_activos} producto(s) activo(s) en esta categoría",
        )

    cat.activo = False
    db.commit()
