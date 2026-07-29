"""producto meta fields: costo, sku, descripcion, imagen_url

Revision ID: 0005_producto_meta
Revises: 0004_decimal_quantities
Create Date: 2026-05-09 22:10:00.000000

Adds the metadata fields needed by the Products CRUD UI:
  - costo: Float, default 0 (allows margin calculations on dashboard)
  - sku: String, unique-per-(tenant, sucursal) (search + barcode support)
  - descripcion: Text (long description shown on product card)
  - imagen_url: String (external CDN URL; upload UI ships later)
"""
from __future__ import annotations

from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa


revision: str = "0005_producto_meta"
down_revision: Union[str, None] = "0004_decimal_quantities"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def _column_exists(table: str, column: str) -> bool:
    bind = op.get_bind()
    inspector = sa.inspect(bind)
    return column in [c["name"] for c in inspector.get_columns(table)]


def upgrade() -> None:
    with op.batch_alter_table("productos") as batch:
        if not _column_exists("productos", "costo"):
            batch.add_column(sa.Column("costo", sa.Float(), nullable=False, server_default="0"))
        if not _column_exists("productos", "sku"):
            batch.add_column(sa.Column("sku", sa.String(), nullable=True))
        if not _column_exists("productos", "descripcion"):
            batch.add_column(sa.Column("descripcion", sa.Text(), nullable=True))
        if not _column_exists("productos", "imagen_url"):
            batch.add_column(sa.Column("imagen_url", sa.String(), nullable=True))

    # Index on sku to speed search/filter; not unique because two sucursales of
    # the same tenant may legitimately share an SKU.
    op.create_index("ix_productos_sku", "productos", ["sku"])


def downgrade() -> None:
    op.drop_index("ix_productos_sku", table_name="productos")
    with op.batch_alter_table("productos") as batch:
        for col in ("imagen_url", "descripcion", "sku", "costo"):
            if _column_exists("productos", col):
                batch.drop_column(col)
