"""baseline: initial schema (Tenant, Sucursal, Producto, Venta, Orden, Categoria, v3 tables)

Revision ID: 0001_baseline
Revises:
Create Date: 2026-04-29 02:50:00.000000

This is the baseline migration that mirrors the schema previously created by
Base.metadata.create_all(...). It uses CREATE TABLE IF NOT EXISTS semantics
via checkfirst=True so it is safe to apply on databases that already have
the tables (legacy SQLite/Postgres deployments).

For brand-new databases it creates the full schema in one shot.
"""
from __future__ import annotations

from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa


# revision identifiers, used by Alembic.
revision: str = "0001_baseline"
down_revision: Union[str, None] = None
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def _table_exists(name: str) -> bool:
    bind = op.get_bind()
    inspector = sa.inspect(bind)
    return name in inspector.get_table_names()


def upgrade() -> None:
    # ── tenants ──────────────────────────────────────────────────────────
    if not _table_exists("tenants"):
        op.create_table(
            "tenants",
            sa.Column("id", sa.Integer(), primary_key=True, autoincrement=True),
            sa.Column("email", sa.String(), nullable=False, unique=True),
            sa.Column("password_hash", sa.String(), nullable=False),
            sa.Column("nombre", sa.String(), nullable=False),
            sa.Column("propietario", sa.String(), nullable=True),
            sa.Column("telefono", sa.String(), nullable=True),
            sa.Column("plan", sa.String(), server_default="starter"),
            sa.Column("activo", sa.Boolean(), server_default=sa.text("true")),
            sa.Column("es_admin", sa.Boolean(), server_default=sa.text("false")),
            sa.Column("plan_activo", sa.Boolean(), server_default=sa.text("true")),
            sa.Column("fecha_vencimiento", sa.DateTime(timezone=True), nullable=True),
            sa.Column("creado_en", sa.DateTime(timezone=True), nullable=True),
        )
        op.create_index("ix_tenants_email", "tenants", ["email"])

    # ── sucursales ───────────────────────────────────────────────────────
    if not _table_exists("sucursales"):
        op.create_table(
            "sucursales",
            sa.Column("id", sa.String(), primary_key=True),
            sa.Column("tenant_id", sa.Integer(), nullable=False),
            sa.Column("nombre", sa.String(), nullable=False),
            sa.Column("activo", sa.Boolean(), server_default=sa.text("true")),
            sa.ForeignKeyConstraint(["tenant_id"], ["tenants.id"], ondelete="CASCADE"),
        )
        op.create_index("ix_sucursales_tenant_id", "sucursales", ["tenant_id"])

    # ── categorias ───────────────────────────────────────────────────────
    if not _table_exists("categorias"):
        op.create_table(
            "categorias",
            sa.Column("id", sa.String(), primary_key=True),
            sa.Column("tenant_id", sa.Integer(), nullable=False),
            sa.Column("sucursal_id", sa.String(), nullable=True),
            sa.Column("nombre", sa.String(), nullable=False),
            sa.Column("activo", sa.Boolean(), server_default=sa.text("true")),
            sa.ForeignKeyConstraint(["tenant_id"], ["tenants.id"], ondelete="CASCADE"),
            sa.ForeignKeyConstraint(["sucursal_id"], ["sucursales.id"], ondelete="CASCADE"),
        )
        op.create_index("ix_categorias_tenant_id", "categorias", ["tenant_id"])
        op.create_index("ix_categorias_sucursal_id", "categorias", ["sucursal_id"])

    # ── productos ────────────────────────────────────────────────────────
    if not _table_exists("productos"):
        op.create_table(
            "productos",
            sa.Column("id", sa.String(), primary_key=True),
            sa.Column("tenant_id", sa.Integer(), nullable=False),
            sa.Column("sucursal_id", sa.String(), nullable=True),
            sa.Column("nombre", sa.String(), nullable=False),
            sa.Column("precio", sa.Float(), nullable=False),
            sa.Column("insumos", sa.Text(), server_default=""),
            sa.Column("categoria", sa.String(), server_default="General"),
            sa.Column("categoria_id", sa.String(), nullable=True),
            sa.Column("activo", sa.Boolean(), server_default=sa.text("true")),
            sa.ForeignKeyConstraint(["tenant_id"], ["tenants.id"], ondelete="CASCADE"),
            sa.ForeignKeyConstraint(["sucursal_id"], ["sucursales.id"], ondelete="CASCADE"),
            sa.ForeignKeyConstraint(["categoria_id"], ["categorias.id"]),
        )
        op.create_index("ix_productos_tenant_id", "productos", ["tenant_id"])
        op.create_index("ix_productos_sucursal_id", "productos", ["sucursal_id"])
        op.create_index("ix_productos_categoria_id", "productos", ["categoria_id"])

    # ── ventas (legacy) ──────────────────────────────────────────────────
    if not _table_exists("ventas"):
        op.create_table(
            "ventas",
            sa.Column("id", sa.String(), primary_key=True),
            sa.Column("tenant_id", sa.Integer(), nullable=False),
            sa.Column("sucursal_id", sa.String(), nullable=True),
            sa.Column("fecha", sa.DateTime(timezone=True), nullable=True),
            sa.Column("producto_id", sa.String(), nullable=False),
            sa.Column("producto_nombre", sa.String(), nullable=False),
            sa.Column("cantidad", sa.Integer(), nullable=False),
            sa.Column("precio_unitario", sa.Float(), nullable=False),
            sa.Column("total", sa.Float(), nullable=False),
            sa.Column("metodo_pago", sa.String(), nullable=False),
            sa.Column("anulada", sa.Boolean(), server_default=sa.text("false")),
            sa.ForeignKeyConstraint(["tenant_id"], ["tenants.id"], ondelete="CASCADE"),
            sa.ForeignKeyConstraint(["sucursal_id"], ["sucursales.id"], ondelete="CASCADE"),
        )
        op.create_index("ix_ventas_tenant_id", "ventas", ["tenant_id"])
        op.create_index("ix_ventas_sucursal_id", "ventas", ["sucursal_id"])
        op.create_index("ix_ventas_fecha", "ventas", ["fecha"])

    # ── ordenes ──────────────────────────────────────────────────────────
    if not _table_exists("ordenes"):
        op.create_table(
            "ordenes",
            sa.Column("id", sa.String(), primary_key=True),
            sa.Column("tenant_id", sa.Integer(), nullable=False),
            sa.Column("sucursal_id", sa.String(), nullable=False),
            sa.Column("fecha", sa.DateTime(timezone=True), nullable=True),
            sa.Column("metodo_pago", sa.String(), nullable=False),
            sa.Column("subtotal", sa.Float(), nullable=False),
            sa.Column("domicilio", sa.Float(), server_default="0"),
            sa.Column("total", sa.Float(), nullable=False),
            sa.Column("anulada", sa.Boolean(), server_default=sa.text("false")),
            sa.ForeignKeyConstraint(["tenant_id"], ["tenants.id"], ondelete="CASCADE"),
            sa.ForeignKeyConstraint(["sucursal_id"], ["sucursales.id"], ondelete="CASCADE"),
        )
        op.create_index("ix_ordenes_tenant_id", "ordenes", ["tenant_id"])
        op.create_index("ix_ordenes_sucursal_id", "ordenes", ["sucursal_id"])
        op.create_index("ix_ordenes_fecha", "ordenes", ["fecha"])

    # ── orden_items ──────────────────────────────────────────────────────
    if not _table_exists("orden_items"):
        op.create_table(
            "orden_items",
            sa.Column("id", sa.String(), primary_key=True),
            sa.Column("orden_id", sa.String(), nullable=False),
            sa.Column("producto_id", sa.String(), nullable=False),
            sa.Column("producto_nombre", sa.String(), nullable=False),
            sa.Column("cantidad", sa.Integer(), nullable=False),
            sa.Column("precio_unitario", sa.Float(), nullable=False),
            sa.Column("total", sa.Float(), nullable=False),
            sa.ForeignKeyConstraint(["orden_id"], ["ordenes.id"], ondelete="CASCADE"),
        )
        op.create_index("ix_orden_items_orden_id", "orden_items", ["orden_id"])

    # ── tenant_branding (v3) ─────────────────────────────────────────────
    if not _table_exists("tenant_branding"):
        op.create_table(
            "tenant_branding",
            sa.Column("tenant_id", sa.Integer(), primary_key=True),
            sa.Column("color_primary", sa.String(length=7), server_default="#e25822"),
            sa.Column("color_secondary", sa.String(length=7), server_default="#1a1714"),
            sa.Column("color_accent", sa.String(length=7), server_default="#22c55e"),
            sa.Column("nombre_comercial", sa.String(), nullable=False),
            sa.Column("logo_url", sa.String(), nullable=True),
            sa.Column("nicho", sa.String(), server_default="restaurante"),
            sa.Column("tema", sa.String(), server_default="dark"),
            sa.Column("tipografia", sa.String(), server_default="Inter"),
            sa.Column("categorias_default", sa.JSON(), nullable=True),
            sa.Column("actualizado_en", sa.DateTime(timezone=True), nullable=True),
            sa.ForeignKeyConstraint(["tenant_id"], ["tenants.id"], ondelete="CASCADE"),
        )

    # ── usuarios (v3) ────────────────────────────────────────────────────
    if not _table_exists("usuarios"):
        op.create_table(
            "usuarios",
            sa.Column("id", sa.Integer(), primary_key=True, autoincrement=True),
            sa.Column("tenant_id", sa.Integer(), nullable=False),
            sa.Column("email", sa.String(), nullable=False),
            sa.Column("password_hash", sa.String(), nullable=False),
            sa.Column("nombre", sa.String(), nullable=False),
            sa.Column("rol", sa.String(), nullable=False),
            sa.Column("sucursal_id", sa.String(), nullable=True),
            sa.Column("pin", sa.String(length=6), nullable=True),
            sa.Column("activo", sa.Boolean(), server_default=sa.text("true")),
            sa.Column("creado_en", sa.DateTime(timezone=True), nullable=True),
            sa.Column("ultimo_login", sa.DateTime(timezone=True), nullable=True),
            sa.ForeignKeyConstraint(["tenant_id"], ["tenants.id"], ondelete="CASCADE"),
            sa.ForeignKeyConstraint(["sucursal_id"], ["sucursales.id"], ondelete="SET NULL"),
            sa.UniqueConstraint("tenant_id", "email", name="uq_usuario_tenant_email"),
        )
        op.create_index("ix_usuarios_tenant_id", "usuarios", ["tenant_id"])
        op.create_index("ix_usuarios_email", "usuarios", ["email"])
        op.create_index("ix_usuarios_sucursal_id", "usuarios", ["sucursal_id"])
        op.create_index("ix_usuarios_pin", "usuarios", ["pin"])

    # ── onboarding_progress (v3) ─────────────────────────────────────────
    if not _table_exists("onboarding_progress"):
        op.create_table(
            "onboarding_progress",
            sa.Column("tenant_id", sa.Integer(), primary_key=True),
            sa.Column("perfil_configurado", sa.Boolean(), server_default=sa.text("false")),
            sa.Column("primer_producto", sa.Boolean(), server_default=sa.text("false")),
            sa.Column("primera_venta", sa.Boolean(), server_default=sa.text("false")),
            sa.Column("saltado", sa.Boolean(), server_default=sa.text("false")),
            sa.Column("completado_en", sa.DateTime(timezone=True), nullable=True),
            sa.Column("actualizado_en", sa.DateTime(timezone=True), nullable=True),
            sa.ForeignKeyConstraint(["tenant_id"], ["tenants.id"], ondelete="CASCADE"),
        )


def downgrade() -> None:
    # Baseline: dropping the entire schema. Use with care.
    op.drop_table("onboarding_progress")
    op.drop_table("usuarios")
    op.drop_table("tenant_branding")
    op.drop_table("orden_items")
    op.drop_table("ordenes")
    op.drop_table("ventas")
    op.drop_table("productos")
    op.drop_table("categorias")
    op.drop_table("sucursales")
    op.drop_table("tenants")
