"""inventario v3.1: stock fields on producto + movimientos_inventario + categoria.creado_en

Revision ID: 0002_stock_inventario
Revises: 0001_baseline
Create Date: 2026-04-29 02:55:00.000000

Changes:
  - productos: adds stock, stock_minimo, unidad_medida, creado_en, actualizado_en
  - categorias: adds creado_en
  - new table: movimientos_inventario (ledger of stock changes)
"""
from __future__ import annotations

from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa


# revision identifiers, used by Alembic.
revision: str = "0002_stock_inventario"
down_revision: Union[str, None] = "0001_baseline"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def _column_exists(table: str, column: str) -> bool:
    bind = op.get_bind()
    inspector = sa.inspect(bind)
    cols = [c["name"] for c in inspector.get_columns(table)]
    return column in cols


def _table_exists(name: str) -> bool:
    bind = op.get_bind()
    inspector = sa.inspect(bind)
    return name in inspector.get_table_names()


def upgrade() -> None:
    # ── productos: nuevas columnas ──────────────────────────────────────
    with op.batch_alter_table("productos") as batch:
        if not _column_exists("productos", "stock"):
            batch.add_column(sa.Column("stock", sa.Float(), nullable=False, server_default="0"))
        if not _column_exists("productos", "stock_minimo"):
            batch.add_column(sa.Column("stock_minimo", sa.Float(), nullable=False, server_default="0"))
        if not _column_exists("productos", "unidad_medida"):
            batch.add_column(
                sa.Column("unidad_medida", sa.String(), nullable=False, server_default="unidad")
            )
        if not _column_exists("productos", "creado_en"):
            batch.add_column(sa.Column("creado_en", sa.DateTime(timezone=True), nullable=True))
        if not _column_exists("productos", "actualizado_en"):
            batch.add_column(
                sa.Column("actualizado_en", sa.DateTime(timezone=True), nullable=True)
            )

    # ── categorias: creado_en ────────────────────────────────────────────
    if not _column_exists("categorias", "creado_en"):
        with op.batch_alter_table("categorias") as batch:
            batch.add_column(sa.Column("creado_en", sa.DateTime(timezone=True), nullable=True))

    # ── movimientos_inventario: nueva tabla ─────────────────────────────
    if not _table_exists("movimientos_inventario"):
        op.create_table(
            "movimientos_inventario",
            sa.Column("id", sa.String(), primary_key=True),
            sa.Column("tenant_id", sa.Integer(), nullable=False),
            sa.Column("sucursal_id", sa.String(), nullable=True),
            sa.Column("producto_id", sa.String(), nullable=False),
            sa.Column("tipo", sa.String(), nullable=False),
            sa.Column("cantidad", sa.Float(), nullable=False),
            sa.Column("stock_antes", sa.Float(), nullable=False),
            sa.Column("stock_despues", sa.Float(), nullable=False),
            sa.Column("motivo", sa.String(), nullable=True),
            sa.Column("referencia_id", sa.String(), nullable=True),
            sa.Column("usuario_id", sa.Integer(), nullable=True),
            sa.Column("fecha", sa.DateTime(timezone=True), nullable=True),
            sa.ForeignKeyConstraint(["tenant_id"], ["tenants.id"], ondelete="CASCADE"),
            sa.ForeignKeyConstraint(["sucursal_id"], ["sucursales.id"], ondelete="CASCADE"),
            sa.ForeignKeyConstraint(["producto_id"], ["productos.id"], ondelete="CASCADE"),
            sa.ForeignKeyConstraint(["usuario_id"], ["usuarios.id"], ondelete="SET NULL"),
        )
        op.create_index(
            "ix_movimientos_inventario_tenant_id", "movimientos_inventario", ["tenant_id"]
        )
        op.create_index(
            "ix_movimientos_inventario_sucursal_id", "movimientos_inventario", ["sucursal_id"]
        )
        op.create_index(
            "ix_movimientos_inventario_producto_id", "movimientos_inventario", ["producto_id"]
        )
        op.create_index("ix_movimientos_inventario_tipo", "movimientos_inventario", ["tipo"])
        op.create_index(
            "ix_movimientos_inventario_referencia_id", "movimientos_inventario", ["referencia_id"]
        )
        op.create_index("ix_movimientos_inventario_fecha", "movimientos_inventario", ["fecha"])


def downgrade() -> None:
    if _table_exists("movimientos_inventario"):
        op.drop_table("movimientos_inventario")

    with op.batch_alter_table("categorias") as batch:
        if _column_exists("categorias", "creado_en"):
            batch.drop_column("creado_en")

    with op.batch_alter_table("productos") as batch:
        for col in ("actualizado_en", "creado_en", "unidad_medida", "stock_minimo", "stock"):
            if _column_exists("productos", col):
                batch.drop_column(col)
