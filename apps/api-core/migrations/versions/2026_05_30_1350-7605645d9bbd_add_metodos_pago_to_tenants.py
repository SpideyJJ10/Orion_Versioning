"""add metodos_pago to tenants

Revision ID: 7605645d9bbd
Revises: 0006_orden_meta
Create Date: 2026-05-30 13:50:51.518882+00:00

"""
from __future__ import annotations

from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa


# revision identifiers, used by Alembic.
revision: str = '7605645d9bbd'
down_revision: Union[str, None] = '0006_orden_meta'
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    with op.batch_alter_table('tenants', schema=None) as batch_op:
        batch_op.add_column(sa.Column('metodos_pago', sa.JSON(), nullable=True))

def downgrade() -> None:
    with op.batch_alter_table('tenants', schema=None) as batch_op:
        batch_op.drop_column('metodos_pago')
