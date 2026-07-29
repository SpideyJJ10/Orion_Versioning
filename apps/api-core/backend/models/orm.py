"""
Modelos SQLAlchemy — tablas de la base de datos.

Tablas:
  tenants                → un registro por cliente (negocio)
  sucursales             → locales/puntos de venta de cada tenant
  productos              → catálogo de productos por sucursal (con stock)
  categorias             → categorías de productos por sucursal
  ventas                 → transacciones individuales del POS (legacy)
  ordenes                → órdenes atómicas (transacciones completas)
  orden_items            → líneas de cada orden
  movimientos_inventario → ledger de entradas/salidas de stock
  tenant_branding        → personalización white-label (1:1 con tenant)
  usuarios               → empleados con roles (N:1 con tenant)
  onboarding_progress    → tracking del tutorial (1:1 con tenant)
  forecast_series        → predicciones de demanda producidas por el módulo ML
  ml_alerts              → alertas inteligentes generadas por ML (stockout, etc.)
  ml_model_metadata      → metadata de cada modelo entrenado (rmse, samples, etc.)
"""
import uuid
from datetime import datetime, timezone

from sqlalchemy import (
    JSON,
    Boolean,
    Column,
    DateTime,
    Float,
    ForeignKey,
    Integer,
    String,
    Text,
    UniqueConstraint,
)
from sqlalchemy.orm import relationship

from backend.db.session import Base


def _uuid() -> str:
    return str(uuid.uuid4())


def _utcnow():
    return datetime.now(timezone.utc)


class Tenant(Base):
    __tablename__ = "tenants"

    id                 = Column(Integer, primary_key=True, autoincrement=True)
    email              = Column(String,  unique=True, nullable=False, index=True)
    password_hash      = Column(String,  nullable=False)
    nombre             = Column(String,  nullable=False)
    propietario        = Column(String,  nullable=True)
    telefono           = Column(String,  nullable=True)
    plan               = Column(String,  default="starter")
    activo             = Column(Boolean, default=True)
    es_admin           = Column(Boolean, default=False)
    plan_activo        = Column(Boolean, default=True)
    fecha_vencimiento  = Column(DateTime(timezone=True), nullable=True)
    metodos_pago       = Column(JSON, nullable=True)
    creado_en          = Column(DateTime(timezone=True), default=_utcnow)
    
    # ── Facturación / Stripe SaaS ──
    stripe_customer_id     = Column(String, nullable=True, index=True)
    stripe_subscription_id = Column(String, nullable=True, index=True)
    subscription_status    = Column(String, nullable=True)


    sucursales = relationship("Sucursal",  back_populates="tenant", cascade="all, delete-orphan")
    productos  = relationship("Producto",  back_populates="tenant", cascade="all, delete-orphan")
    ventas     = relationship("Venta",     back_populates="tenant", cascade="all, delete-orphan")
    categorias = relationship("Categoria", back_populates="tenant", cascade="all, delete-orphan")
    mesas      = relationship("Mesa",      back_populates="tenant", cascade="all, delete-orphan")
    # ── Nuevo en v3: branding, usuarios operativos, tutorial tracking ──
    branding   = relationship("TenantBranding",     back_populates="tenant",
                              uselist=False, cascade="all, delete-orphan")
    usuarios   = relationship("Usuario",            back_populates="tenant",
                              cascade="all, delete-orphan")
    onboarding = relationship("OnboardingProgress", back_populates="tenant",
                              uselist=False, cascade="all, delete-orphan")


class Sucursal(Base):
    __tablename__ = "sucursales"

    id        = Column(String,  primary_key=True, default=_uuid)
    tenant_id = Column(Integer, ForeignKey("tenants.id", ondelete="CASCADE"), nullable=False, index=True)
    nombre    = Column(String,  nullable=False)
    activo    = Column(Boolean, default=True)

    tenant     = relationship("Tenant",    back_populates="sucursales")
    productos  = relationship("Producto",  back_populates="sucursal", cascade="all, delete-orphan")
    ventas     = relationship("Venta",     back_populates="sucursal", cascade="all, delete-orphan")
    categorias = relationship("Categoria", back_populates="sucursal", cascade="all, delete-orphan")


class Producto(Base):
    __tablename__ = "productos"

    id            = Column(String,  primary_key=True, default=_uuid)
    tenant_id     = Column(Integer, ForeignKey("tenants.id", ondelete="CASCADE"),    nullable=False, index=True)
    sucursal_id   = Column(String,  ForeignKey("sucursales.id", ondelete="CASCADE"), nullable=True,  index=True)
    nombre        = Column(String,  nullable=False)
    precio        = Column(Float,   nullable=False)
    costo         = Column(Float,   default=0.0,  nullable=False)        # costo unitario para márgenes
    insumos       = Column(Text,    default="")
    descripcion   = Column(Text,    nullable=True)
    sku           = Column(String,  nullable=True, index=True)            # código de barras / SKU
    imagen_url    = Column(String,  nullable=True)
    categoria     = Column(String,  default="General")
    categoria_id  = Column(String,  ForeignKey("categorias.id"), nullable=True, index=True)
    activo        = Column(Boolean, default=True)
    # ── Inventario (v3.1) ──────────────────────────────────
    stock         = Column(Float,   default=0.0,  nullable=False)        # stock actual
    stock_minimo  = Column(Float,   default=0.0,  nullable=False)        # umbral de alerta
    unidad_medida = Column(String,  default="unidad", nullable=False)    # unidad|kg|lt|gr|ml|pack
    creado_en     = Column(DateTime(timezone=True), default=_utcnow)
    actualizado_en = Column(DateTime(timezone=True), default=_utcnow, onupdate=_utcnow)

    tenant        = relationship("Tenant",    back_populates="productos")
    sucursal      = relationship("Sucursal",  back_populates="productos")
    categoria_rel = relationship("Categoria", foreign_keys=[categoria_id])
    movimientos   = relationship("MovimientoInventario", back_populates="producto",
                                  cascade="all, delete-orphan")


class Venta(Base):
    """Legacy: ventas individuales. Nuevas ventas se crean vía Orden."""
    __tablename__ = "ventas"

    id               = Column(String,   primary_key=True, default=_uuid)
    tenant_id        = Column(Integer,  ForeignKey("tenants.id", ondelete="CASCADE"),   nullable=False, index=True)
    sucursal_id      = Column(String,   ForeignKey("sucursales.id", ondelete="CASCADE"), nullable=True,  index=True)
    fecha            = Column(DateTime(timezone=True), default=_utcnow, index=True)
    producto_id      = Column(String,   nullable=False)
    producto_nombre  = Column(String,   nullable=False)
    cantidad         = Column(Float,    nullable=False)
    precio_unitario  = Column(Float,    nullable=False)
    total            = Column(Float,    nullable=False)
    metodo_pago      = Column(String,   nullable=False)
    anulada          = Column(Boolean,  default=False)

    tenant   = relationship("Tenant",   back_populates="ventas")
    sucursal = relationship("Sucursal", back_populates="ventas")


class Categoria(Base):
    __tablename__ = "categorias"

    id          = Column(String,  primary_key=True, default=_uuid)
    tenant_id   = Column(Integer, ForeignKey("tenants.id", ondelete="CASCADE"),    nullable=False, index=True)
    sucursal_id = Column(String,  ForeignKey("sucursales.id", ondelete="CASCADE"), nullable=True,  index=True)
    nombre      = Column(String,  nullable=False)
    activo      = Column(Boolean, default=True)
    creado_en   = Column(DateTime(timezone=True), default=_utcnow)

    tenant   = relationship("Tenant",   back_populates="categorias")
    sucursal = relationship("Sucursal", back_populates="categorias")


# ════════════════════════════════════════════════════════════════════════
#  M12 — MESAS (restaurante / cafetería)
# ════════════════════════════════════════════════════════════════════════

class Mesa(Base):
    """Mesa física de un restaurante. Estado en tiempo real.

    estado:
      - 'libre'         → disponible para sentar clientes
      - 'ocupada'       → clientes sentados y con orden activa
      - 'reservada'     → reservada para llegar más tarde
      - 'cuenta_pedida' → listos para pagar, el mesero va en camino

    orden_id es opcional; se vincula cuando se asocia una Orden a la mesa.
    """
    __tablename__ = "mesas"

    id          = Column(String,  primary_key=True, default=_uuid)
    tenant_id   = Column(Integer, ForeignKey("tenants.id", ondelete="CASCADE"),    nullable=False, index=True)
    sucursal_id = Column(String,  ForeignKey("sucursales.id", ondelete="CASCADE"), nullable=False, index=True)
    numero      = Column(Integer, nullable=False)                        # número visible en la app
    nombre      = Column(String,  nullable=True)                         # ej: "Terraza 1"
    capacidad   = Column(Integer, default=4, nullable=False)             # comensales máximos
    estado      = Column(String,  default="libre", nullable=False,       # libre|ocupada|reservada|cuenta_pedida
                         index=True)
    orden_id    = Column(String,  ForeignKey("ordenes.id", ondelete="SET NULL"), nullable=True)
    notas       = Column(String,  nullable=True)                         # notas del mesero
    activo      = Column(Boolean, default=True)
    creado_en   = Column(DateTime(timezone=True), default=_utcnow)
    actualizado_en = Column(DateTime(timezone=True), default=_utcnow, onupdate=_utcnow)

    tenant   = relationship("Tenant",   back_populates="mesas")
    sucursal = relationship("Sucursal", foreign_keys=[sucursal_id])
    orden    = relationship("Orden",    foreign_keys=[orden_id])


class Orden(Base):
    """Orden atómica — una transacción completa del POS."""
    __tablename__ = "ordenes"

    id          = Column(String,  primary_key=True, default=_uuid)
    tenant_id   = Column(Integer, ForeignKey("tenants.id", ondelete="CASCADE"),   nullable=False, index=True)
    sucursal_id = Column(String,  ForeignKey("sucursales.id", ondelete="CASCADE"), nullable=False, index=True)
    fecha       = Column(DateTime(timezone=True), default=_utcnow, index=True)
    metodo_pago = Column(String,  nullable=False)
    subtotal    = Column(Float,   nullable=False)
    descuento   = Column(Float,   default=0)
    domicilio   = Column(Float,   default=0)
    total       = Column(Float,   nullable=False)
    efectivo_recibido = Column(Float, nullable=True)   # solo si metodo='Efectivo'
    metodo_pago_extra = Column(String, nullable=True)  # cuando hay pago mixto (json {metodo:monto})
    cliente_nombre = Column(String, nullable=True)
    notas       = Column(Text,    nullable=True)
    usuario_id  = Column(Integer, ForeignKey("usuarios.id", ondelete="SET NULL"), nullable=True)
    anulada     = Column(Boolean,  default=False)
    
    # ── Facturación Electrónica (DIAN) ──
    dian_status  = Column(String, default="no_aplica") # no_aplica | pending | issued | failed
    dian_cufe    = Column(String, nullable=True)       # Código Único de Facturación Electrónica
    dian_pdf_url = Column(String, nullable=True)       # URL del PDF generado
    dian_xml_url = Column(String, nullable=True)       # URL del XML firmado

    tenant   = relationship("Tenant")
    sucursal = relationship("Sucursal")
    items    = relationship("OrdenItem", back_populates="orden", cascade="all, delete-orphan")


class OrdenItem(Base):
    """Línea individual dentro de una orden."""
    __tablename__ = "orden_items"

    id              = Column(String, primary_key=True, default=_uuid)
    orden_id        = Column(String, ForeignKey("ordenes.id", ondelete="CASCADE"), nullable=False, index=True)
    producto_id     = Column(String, nullable=False)
    producto_nombre = Column(String, nullable=False)
    cantidad        = Column(Float,  nullable=False)
    precio_unitario = Column(Float,  nullable=False)
    total           = Column(Float,  nullable=False)

    orden = relationship("Orden", back_populates="items")


# ════════════════════════════════════════════════════════════════════════
#  v3.1 — INVENTARIO (Stock + ledger de movimientos)
# ════════════════════════════════════════════════════════════════════════

class MovimientoInventario(Base):
    """Ledger de movimientos de stock — alimenta auditoría y modelos ML.

    Cada cambio de stock (venta, entrada, ajuste, merma) genera UNA fila aquí.
    El stock actual del producto siempre debe poder reconstruirse sumando este
    ledger desde un punto de partida conocido.
    """
    __tablename__ = "movimientos_inventario"

    id           = Column(String, primary_key=True, default=_uuid)
    tenant_id    = Column(Integer, ForeignKey("tenants.id", ondelete="CASCADE"),
                          nullable=False, index=True)
    sucursal_id  = Column(String,  ForeignKey("sucursales.id", ondelete="CASCADE"),
                          nullable=True, index=True)
    producto_id  = Column(String,  ForeignKey("productos.id", ondelete="CASCADE"),
                          nullable=False, index=True)
    # Tipo: entrada | salida | ajuste | venta | merma | devolucion
    tipo         = Column(String,  nullable=False, index=True)
    cantidad     = Column(Float,   nullable=False)   # signed: positivo entra, negativo sale
    stock_antes  = Column(Float,   nullable=False)
    stock_despues = Column(Float,  nullable=False)
    motivo       = Column(String,  nullable=True)
    referencia_id = Column(String, nullable=True, index=True)  # p.ej. orden_id, devolucion_id
    usuario_id   = Column(Integer, ForeignKey("usuarios.id", ondelete="SET NULL"),
                          nullable=True)
    fecha        = Column(DateTime(timezone=True), default=_utcnow, index=True)

    producto = relationship("Producto", back_populates="movimientos")


# ════════════════════════════════════════════════════════════════════════
#  v3 — WHITE-LABEL & ROLES
# ════════════════════════════════════════════════════════════════════════

class TenantBranding(Base):
    """Personalización visual por tenant. 1:1 con Tenant.

    El LOGO ORION es inmutable (servido desde /assets/orion-logo.svg).
    Aquí solo se almacena lo que el cliente puede personalizar.
    """
    __tablename__ = "tenant_branding"

    tenant_id        = Column(Integer, ForeignKey("tenants.id", ondelete="CASCADE"),
                               primary_key=True)
    # Colores (hex #rrggbb — validados en Pydantic)
    color_primary    = Column(String(7),  default="#8b5cf6")   # violeta default
    color_secondary  = Column(String(7),  default="#0f172a")   # slate default
    color_accent     = Column(String(7),  default="#d946ef")   # fuchsia default
    # Identidad visual del negocio
    nombre_comercial = Column(String,     nullable=False)
    logo_url         = Column(String,     nullable=True)       # URL externa (S3/Cloudinary) o /uploads/
    nicho            = Column(String,     default="restaurante")  # restaurante|retail|farmacia|servicio|otro
    # Tema y tipografía
    tema             = Column(String,     default="dark")      # dark|light|warm
    tipografia       = Column(String,     default="Inter")
    # Categorías sugeridas por nicho (seed inicial)
    categorias_default = Column(JSON,     default=list)        # ej: ["Bebidas", "Platos", "Postres"]
    # Auditoría
    actualizado_en   = Column(DateTime(timezone=True), default=_utcnow, onupdate=_utcnow)

    tenant = relationship("Tenant", back_populates="branding")


class Usuario(Base):
    """Usuario operativo de un tenant (empleados: cajero, manager, inventario).

    Distinto del modelo Tenant (que representa al DUEÑO / dueño del negocio).
    El owner de cada tenant también tiene un registro aquí con rol='owner'.
    """
    __tablename__ = "usuarios"
    __table_args__ = (UniqueConstraint("tenant_id", "email", name="uq_usuario_tenant_email"),)

    id            = Column(Integer, primary_key=True, autoincrement=True)
    tenant_id     = Column(Integer, ForeignKey("tenants.id", ondelete="CASCADE"),
                           nullable=False, index=True)
    email         = Column(String,  nullable=False, index=True)
    password_hash = Column(String,  nullable=False)
    nombre        = Column(String,  nullable=False)
    rol           = Column(String,  nullable=False)   # owner|manager|cajero|inventario
    sucursal_id   = Column(String,  ForeignKey("sucursales.id", ondelete="SET NULL"),
                           nullable=True, index=True)
    pin           = Column(String(6), nullable=True, index=True)  # PIN rápido para cajeros
    activo        = Column(Boolean, default=True)
    creado_en     = Column(DateTime(timezone=True), default=_utcnow)
    ultimo_login  = Column(DateTime(timezone=True), nullable=True)

    tenant   = relationship("Tenant",   back_populates="usuarios")
    sucursal = relationship("Sucursal", foreign_keys=[sucursal_id])


class OnboardingProgress(Base):
    """Tracking del tutorial interactivo. 1:1 con Tenant."""
    __tablename__ = "onboarding_progress"

    tenant_id          = Column(Integer, ForeignKey("tenants.id", ondelete="CASCADE"),
                                primary_key=True)
    perfil_configurado = Column(Boolean, default=False)
    primer_producto    = Column(Boolean, default=False)
    primera_venta      = Column(Boolean, default=False)
    saltado            = Column(Boolean, default=False)   # usuario cerró el tour
    completado_en      = Column(DateTime(timezone=True), nullable=True)
    actualizado_en     = Column(DateTime(timezone=True), default=_utcnow, onupdate=_utcnow)

    tenant = relationship("Tenant", back_populates="onboarding")

    @property
    def porcentaje(self) -> int:
        hechos = sum([self.perfil_configurado, self.primer_producto, self.primera_venta])
        return int((hechos / 3) * 100)


# ════════════════════════════════════════════════════════════════════════
#  ML / FORECASTING — Tablas para el módulo de inteligencia (Fase 2)
# ════════════════════════════════════════════════════════════════════════
class MlModelMetadata(Base):
    """Metadata de cada modelo entrenado.

    Hay un registro por (producto_id, sucursal_id, modelo_tipo). Nuevos
    entrenamientos REEMPLAZAN el registro anterior (no se versiona el
    histórico de modelos en BD; los pesos persisten en disco si aplica).

    `modelo_tipo` valores soportados:
      - "baseline"  → media móvil + estacionalidad semanal (sin deps externas)
      - "prophet"   → Facebook Prophet (requiere `pip install prophet`)
    """
    __tablename__ = "ml_model_metadata"
    __table_args__ = (
        UniqueConstraint("producto_id", "sucursal_id", "modelo_tipo",
                         name="uq_ml_model_producto_sucursal_tipo"),
    )

    id              = Column(Integer, primary_key=True, autoincrement=True)
    tenant_id       = Column(Integer, ForeignKey("tenants.id", ondelete="CASCADE"),
                             nullable=False, index=True)
    sucursal_id     = Column(String, ForeignKey("sucursales.id", ondelete="CASCADE"),
                             nullable=False, index=True)
    producto_id     = Column(String, ForeignKey("productos.id", ondelete="CASCADE"),
                             nullable=False, index=True)
    modelo_tipo     = Column(String, nullable=False)              # baseline | prophet
    samples         = Column(Integer, nullable=False)             # nº de días con datos
    rmse            = Column(Float, nullable=True)                # error de validación
    mae             = Column(Float, nullable=True)
    mape            = Column(Float, nullable=True)
    demanda_media   = Column(Float, nullable=True)                # baseline para alertas
    parametros      = Column(JSON, nullable=True)                 # hiperparámetros usados
    artifact_path   = Column(String, nullable=True)               # ruta al modelo serializado
    entrenado_en    = Column(DateTime(timezone=True), default=_utcnow, index=True)


class ForecastSerie(Base):
    """Una predicción individual: demanda esperada para un (producto, día_futuro).

    Cada llamada a `train_models` reemplaza las predicciones del producto
    para el horizonte completo. Diseño optimizado para queries del frontend:
    `WHERE producto_id = ? AND fecha_target BETWEEN ? AND ?`.
    """
    __tablename__ = "forecast_series"
    __table_args__ = (
        UniqueConstraint("producto_id", "fecha_target",
                         name="uq_forecast_producto_fecha"),
    )

    id              = Column(Integer, primary_key=True, autoincrement=True)
    tenant_id       = Column(Integer, ForeignKey("tenants.id", ondelete="CASCADE"),
                             nullable=False, index=True)
    sucursal_id     = Column(String, ForeignKey("sucursales.id", ondelete="CASCADE"),
                             nullable=False, index=True)
    producto_id     = Column(String, ForeignKey("productos.id", ondelete="CASCADE"),
                             nullable=False, index=True)
    fecha_target    = Column(DateTime(timezone=True), nullable=False, index=True)
    demanda         = Column(Float, nullable=False)               # punto estimado
    intervalo_inf   = Column(Float, nullable=True)                # P10 (o yhat_lower)
    intervalo_sup   = Column(Float, nullable=True)                # P90 (o yhat_upper)
    modelo_tipo     = Column(String, nullable=False)
    generado_en     = Column(DateTime(timezone=True), default=_utcnow)


class MlAlerta(Base):
    """Alerta inteligente generada por el motor ML.

    A diferencia de las alertas de stock_minimo (que son reglas fijas), estas
    consideran la velocidad de venta proyectada y dan recomendaciones
    accionables.

    Tipos:
      - "stockout_riesgo"   → se predice agotamiento dentro del horizonte
      - "sobrestock"        → exceso de stock vs demanda futura
      - "demanda_anomala"   → spike o caída fuera del intervalo de confianza
      - "producto_estrella" → top-N productos por crecimiento
    """
    __tablename__ = "ml_alerts"

    id              = Column(Integer, primary_key=True, autoincrement=True)
    tenant_id       = Column(Integer, ForeignKey("tenants.id", ondelete="CASCADE"),
                             nullable=False, index=True)
    sucursal_id     = Column(String, ForeignKey("sucursales.id", ondelete="CASCADE"),
                             nullable=True, index=True)
    producto_id     = Column(String, ForeignKey("productos.id", ondelete="CASCADE"),
                             nullable=True, index=True)
    tipo            = Column(String, nullable=False, index=True)
    severidad       = Column(String, nullable=False)              # info | warning | critical
    titulo          = Column(String, nullable=False)
    mensaje         = Column(Text,   nullable=False)
    recomendacion   = Column(Text,   nullable=True)
    metadata_json   = Column(JSON,   nullable=True)               # datos extra (días hasta agotamiento, etc.)
    leida           = Column(Boolean, default=False, index=True)
    creada_en       = Column(DateTime(timezone=True), default=_utcnow, index=True)
    expira_en       = Column(DateTime(timezone=True), nullable=True)
