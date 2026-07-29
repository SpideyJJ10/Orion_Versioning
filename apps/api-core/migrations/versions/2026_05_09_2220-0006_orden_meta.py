"""orden meta: descuento, cliente, notas, pago mixto, usuario, efectivo recibido

Revision ID: 0006_orden_meta
Revises: 0005_producto_meta
Create Date: 2026-05-09 22:20:00.000000

Adds columns required by the new POS Pro flows:
  - descuento: total discount (COP) applied to the order
  - efectivo_recibido: amount tendered for change calc (cash only)
  - metodo_pago_extra: JSON-encoded breakdown for mixed payments
  - cliente_nombre: optional buyer name (printed on receipt)
  - notas: free-text annotations
  - usuario_id: FK to usuarios — who rang up the order
"""
from __future__ import annotations

from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa


revision: str = "0006_orden_meta"
down_revision: Union[str, None] = "0005_producto_meta"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def _column_exists(table: str, column: str) -> bool:
    bind = op.get_bind()
    inspector = sa.inspect(bind)
    return column in [c["name"] for c in inspector.get_columns(table)]


def upgrade() -> None:
    with op.batch_alter_table("ordenes") as batch:
        if not _column_exists("ordenes", "descuento"):
            batch.add_column(sa.Column("descuento", sa.Float(), nullable=False, server_default="0"))
        if not _column_exists("ordenes", "efectivo_recibido"):
            batch.add_column(sa.Column("efectivo_recibido", sa.Float(), nullable=True))
        if not _column_exists("ordenes", "metodo_pago_extra"):
            batch.add_column(sa.Column("metodo_pago_extra", sa.String(), nullable=True))
        if not _column_exists("ordenes", "cliente_nombre"):
            batch.add_column(sa.Column("cliente_nombre", sa.String(), nullable=True))
        if not _column_exists("ordenes", "notas"):
            batch.add_column(sa.Column("notas", sa.Text(), nullable=True))
        if not _column_exists("ordenes", "usuario_id"):
            batch.add_column(sa.Column("usuario_id", sa.Integer(), nullable=True))


def downgrade() -> None:
    with op.batch_alter_table("ordenes") as batch:
        for col in (
            "usuario_id",
            "notas",
            "cliente_nombre",
            "metodo_pago_extra",
            "efectivo_recibido",
            "descuento",
        ):
            if _column_exists("ordenes", col):
                batch.drop_column(col)
