"""ml: forecast_series + ml_alerts + ml_model_metadata

Revision ID: 0003_ml_tables
Revises: 0002_stock_inventario
Create Date: 2026-04-29

Crea las tres tablas que soportan el módulo de Machine Learning (Fase 2):

  • ml_model_metadata    → metadata de cada modelo entrenado por (producto, sucursal, tipo)
  • forecast_series      → predicciones individuales (producto × día futuro)
  • ml_alerts            → alertas inteligentes generadas por el motor

Idempotente: usa introspección para no recrear tablas existentes.
"""
from alembic import op
import sqlalchemy as sa


revision = "0003_ml_tables"
down_revision = "0002_stock_inventario"
branch_labels = None
depends_on = None


def _table_exists(name: str) -> bool:
    bind = op.get_bind()
    insp = sa.inspect(bind)
    return name in insp.get_table_names()


def upgrade() -> None:
    # ── ml_model_metadata ────────────────────────────────────────────────
    if not _table_exists("ml_model_metadata"):
        op.create_table(
            "ml_model_metadata",
            sa.Column("id",            sa.Integer(),  primary_key=True, autoincrement=True),
            sa.Column("tenant_id",     sa.Integer(),  sa.ForeignKey("tenants.id",    ondelete="CASCADE"), nullable=False),
            sa.Column("sucursal_id",   sa.String(),   sa.ForeignKey("sucursales.id", ondelete="CASCADE"), nullable=False),
            sa.Column("producto_id",   sa.String(),   sa.ForeignKey("productos.id",  ondelete="CASCADE"), nullable=False),
            sa.Column("modelo_tipo",   sa.String(),   nullable=False),
            sa.Column("samples",       sa.Integer(),  nullable=False),
            sa.Column("rmse",          sa.Float(),    nullable=True),
            sa.Column("mae",           sa.Float(),    nullable=True),
            sa.Column("mape",          sa.Float(),    nullable=True),
            sa.Column("demanda_media", sa.Float(),    nullable=True),
            sa.Column("parametros",    sa.JSON(),     nullable=True),
            sa.Column("artifact_path", sa.String(),   nullable=True),
            sa.Column("entrenado_en",  sa.DateTime(timezone=True), nullable=True),
            sa.UniqueConstraint("producto_id", "sucursal_id", "modelo_tipo",
                                name="uq_ml_model_producto_sucursal_tipo"),
        )
        op.create_index("ix_ml_model_tenant",       "ml_model_metadata", ["tenant_id"])
        op.create_index("ix_ml_model_sucursal",     "ml_model_metadata", ["sucursal_id"])
        op.create_index("ix_ml_model_producto",     "ml_model_metadata", ["producto_id"])
        op.create_index("ix_ml_model_entrenado_en", "ml_model_metadata", ["entrenado_en"])

    # ── forecast_series ──────────────────────────────────────────────────
    if not _table_exists("forecast_series"):
        op.create_table(
            "forecast_series",
            sa.Column("id",            sa.Integer(),  primary_key=True, autoincrement=True),
            sa.Column("tenant_id",     sa.Integer(),  sa.ForeignKey("tenants.id",    ondelete="CASCADE"), nullable=False),
            sa.Column("sucursal_id",   sa.String(),   sa.ForeignKey("sucursales.id", ondelete="CASCADE"), nullable=False),
            sa.Column("producto_id",   sa.String(),   sa.ForeignKey("productos.id",  ondelete="CASCADE"), nullable=False),
            sa.Column("fecha_target",  sa.DateTime(timezone=True), nullable=False),
            sa.Column("demanda",       sa.Float(),    nullable=False),
            sa.Column("intervalo_inf", sa.Float(),    nullable=True),
            sa.Column("intervalo_sup", sa.Float(),    nullable=True),
            sa.Column("modelo_tipo",   sa.String(),   nullable=False),
            sa.Column("generado_en",   sa.DateTime(timezone=True), nullable=True),
            sa.UniqueConstraint("producto_id", "fecha_target",
                                name="uq_forecast_producto_fecha"),
        )
        op.create_index("ix_forecast_tenant",   "forecast_series", ["tenant_id"])
        op.create_index("ix_forecast_sucursal", "forecast_series", ["sucursal_id"])
        op.create_index("ix_forecast_producto", "forecast_series", ["producto_id"])
        op.create_index("ix_forecast_fecha",    "forecast_series", ["fecha_target"])

    # ── ml_alerts ────────────────────────────────────────────────────────
    if not _table_exists("ml_alerts"):
        op.create_table(
            "ml_alerts",
            sa.Column("id",            sa.Integer(),  primary_key=True, autoincrement=True),
            sa.Column("tenant_id",     sa.Integer(),  sa.ForeignKey("tenants.id",    ondelete="CASCADE"), nullable=False),
            sa.Column("sucursal_id",   sa.String(),   sa.ForeignKey("sucursales.id", ondelete="CASCADE"), nullable=True),
            sa.Column("producto_id",   sa.String(),   sa.ForeignKey("productos.id",  ondelete="CASCADE"), nullable=True),
            sa.Column("tipo",          sa.String(),   nullable=False),
            sa.Column("severidad",     sa.String(),   nullable=False),
            sa.Column("titulo",        sa.String(),   nullable=False),
            sa.Column("mensaje",       sa.Text(),     nullable=False),
            sa.Column("recomendacion", sa.Text(),     nullable=True),
            sa.Column("metadata_json", sa.JSON(),     nullable=True),
            sa.Column("leida",         sa.Boolean(),  nullable=True),
            sa.Column("creada_en",     sa.DateTime(timezone=True), nullable=True),
            sa.Column("expira_en",     sa.DateTime(timezone=True), nullable=True),
        )
        op.create_index("ix_ml_alert_tenant",    "ml_alerts", ["tenant_id"])
        op.create_index("ix_ml_alert_sucursal",  "ml_alerts", ["sucursal_id"])
        op.create_index("ix_ml_alert_producto",  "ml_alerts", ["producto_id"])
        op.create_index("ix_ml_alert_tipo",      "ml_alerts", ["tipo"])
        op.create_index("ix_ml_alert_leida",     "ml_alerts", ["leida"])
        op.create_index("ix_ml_alert_creada_en", "ml_alerts", ["creada_en"])


def downgrade() -> None:
    if _table_exists("ml_alerts"):
        op.drop_table("ml_alerts")
    if _table_exists("forecast_series"):
        op.drop_table("forecast_series")
    if _table_exists("ml_model_metadata"):
        op.drop_table("ml_model_metadata")
