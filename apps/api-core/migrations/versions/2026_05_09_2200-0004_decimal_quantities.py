"""decimal quantities: OrdenItem.cantidad and Venta.cantidad change Integer -> Float

Revision ID: 0004_decimal_quantities
Revises: 0003_ml_tables
Create Date: 2026-05-09 22:00:00.000000

Why:
  POS sells items by `unidad_medida` which can be `kg`, `lt`, `gr`, `ml` —
  fractional quantities (0.5 kg, 250 ml) are common. Casting to FLOAT in DB +
  Pydantic enables decimal carts without breaking existing integer rows.

Notes:
  - SQLite uses `batch_alter_table` to recreate the table with new types.
  - PostgreSQL keeps the same path (alembic batch detects backend).
  - downgrade() rounds cantidades to int.
"""
from __future__ import annotations

from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa


# revision identifiers, used by Alembic.
revision: str = "0004_decimal_quantities"
down_revision: Union[str, None] = "0003_ml_tables"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    # orden_items.cantidad: Integer -> Float
    with op.batch_alter_table("orden_items") as batch:
        batch.alter_column(
            "cantidad",
            existing_type=sa.Integer(),
            type_=sa.Float(),
            existing_nullable=False,
        )

    # ventas.cantidad: Integer -> Float
    with op.batch_alter_table("ventas") as batch:
        batch.alter_column(
            "cantidad",
            existing_type=sa.Integer(),
            type_=sa.Float(),
            existing_nullable=False,
        )


def downgrade() -> None:
    # Revert to Integer (rounds existing decimals).
    with op.batch_alter_table("orden_items") as batch:
        batch.alter_column(
            "cantidad",
            existing_type=sa.Float(),
            type_=sa.Integer(),
            existing_nullable=False,
            postgresql_using="cantidad::integer",
        )
    with op.batch_alter_table("ventas") as batch:
        batch.alter_column(
            "cantidad",
            existing_type=sa.Float(),
            type_=sa.Integer(),
            existing_nullable=False,
            postgresql_using="cantidad::integer",
        )
