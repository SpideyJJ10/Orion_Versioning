"""
Schemas Pydantic para validación de entrada/salida.
"""
from datetime import datetime
from enum import Enum
from typing import List, Optional

from pydantic import BaseModel, EmailStr, Field, field_validator


class MetodoPago(str, Enum):
    efectivo     = "Efectivo"
    nequi        = "Nequi"
    daviplata    = "Daviplata"
    tarjeta      = "Tarjeta"
    transferencia = "Transferencia"
    mixto        = "Mixto"


# Límites de cantidad y carrito en POS
MAX_QTY_POR_LINEA  = 999_999.0
MIN_QTY_DECIMAL    = 0.001
MAX_LINEAS_CARRITO = 200


# ── Validadores reutilizables ────────────────────────────────────────
def validate_non_empty_string(v: str, field_name: str = "campo") -> str:
    """Valida que un string no esté vacío después de strip."""
    if not v or not v.strip():
        raise ValueError(f"El {field_name} no puede estar vacío")
    return v.strip()


def validate_positive_number(v: float, field_name: str = "valor") -> float:
    """Valida que un número sea positivo."""
    if v <= 0:
        raise ValueError(f"El {field_name} debe ser mayor a 0")
    return v


# ── Sucursales ───────────────────────────────────────────────────────
class SucursalCreate(BaseModel):
    nombre: str

    @field_validator("nombre")
    @classmethod
    def nombre_no_vacio(cls, v):
        return validate_non_empty_string(v, "nombre de la sucursal")


class SucursalOut(BaseModel):
    id:     str
    nombre: str
    activo: bool

    model_config = {"from_attributes": True}


# ── Productos ────────────────────────────────────────────────────────
UNIDADES_VALIDAS = {"unidad", "kg", "lt", "gr", "ml", "pack", "caja", "docena"}


class ProductoCreate(BaseModel):
    nombre:        str
    precio:        float
    costo:         Optional[float] = 0.0
    insumos:       Optional[str]   = ""
    descripcion:   Optional[str]   = None
    sku:           Optional[str]   = None
    imagen_url:    Optional[str]   = None
    categoria:     str = "General"
    sucursal_id:   str
    stock:         Optional[float] = 0.0
    stock_minimo:  Optional[float] = 0.0
    unidad_medida: Optional[str]   = "unidad"

    @field_validator("precio")
    @classmethod
    def precio_positivo(cls, v):
        return validate_positive_number(v, "precio")

    @field_validator("nombre")
    @classmethod
    def nombre_no_vacio(cls, v):
        return validate_non_empty_string(v, "nombre")

    @field_validator("categoria")
    @classmethod
    def categoria_no_vacia(cls, v):
        return validate_non_empty_string(v, "categoría")

    @field_validator("sucursal_id")
    @classmethod
    def sucursal_requerida(cls, v):
        return validate_non_empty_string(v, "sucursal")

    @field_validator("stock", "stock_minimo")
    @classmethod
    def stock_no_negativo(cls, v):
        if v is not None and v < 0:
            raise ValueError("El stock no puede ser negativo")
        return v

    @field_validator("unidad_medida")
    @classmethod
    def unidad_valida(cls, v):
        if v is None or not v.strip():
            return "unidad"
        if v.strip().lower() not in UNIDADES_VALIDAS:
            raise ValueError(
                f"unidad_medida debe ser una de: {', '.join(sorted(UNIDADES_VALIDAS))}"
            )
        return v.strip().lower()

    @field_validator("costo")
    @classmethod
    def costo_no_negativo(cls, v):
        if v is not None and v < 0:
            raise ValueError("El costo no puede ser negativo")
        return v

    @field_validator("sku")
    @classmethod
    def sku_normalizado(cls, v):
        if v is None:
            return None
        v = v.strip()
        return v or None


class ProductoUpdate(BaseModel):
    """Schema para edición parcial de productos."""
    nombre:        Optional[str]   = None
    precio:        Optional[float] = None
    costo:         Optional[float] = None
    insumos:       Optional[str]   = None
    descripcion:   Optional[str]   = None
    sku:           Optional[str]   = None
    imagen_url:    Optional[str]   = None
    categoria:     Optional[str]   = None
    sucursal_id:   Optional[str]   = None
    stock_minimo:  Optional[float] = None
    unidad_medida: Optional[str]   = None
    activo:        Optional[bool]  = None

    @field_validator("precio")
    @classmethod
    def precio_positivo(cls, v):
        if v is not None and v <= 0:
            raise ValueError("El precio debe ser mayor a 0")
        return v

    @field_validator("nombre")
    @classmethod
    def nombre_no_vacio(cls, v):
        if v is not None:
            return validate_non_empty_string(v, "nombre")
        return v

    @field_validator("stock_minimo")
    @classmethod
    def stock_minimo_no_negativo(cls, v):
        if v is not None and v < 0:
            raise ValueError("stock_minimo no puede ser negativo")
        return v

    @field_validator("unidad_medida")
    @classmethod
    def unidad_valida(cls, v):
        if v is None:
            return v
        if not v.strip() or v.strip().lower() not in UNIDADES_VALIDAS:
            raise ValueError(
                f"unidad_medida debe ser una de: {', '.join(sorted(UNIDADES_VALIDAS))}"
            )
        return v.strip().lower()


class ProductoOut(BaseModel):
    id:            str
    nombre:        str
    precio:        float
    costo:         float = 0.0
    insumos:       str
    descripcion:   Optional[str] = None
    sku:           Optional[str] = None
    imagen_url:    Optional[str] = None
    categoria:     str
    activo:        bool
    sucursal_id:   Optional[str] = None
    stock:         float = 0.0
    stock_minimo:  float = 0.0
    unidad_medida: str   = "unidad"

    model_config = {"from_attributes": True}


class AjusteStockRequest(BaseModel):
    """Body para POST /api/productos/{id}/ajuste-stock.

    tipo:
      - 'entrada'   → cantidad_delta positivo (compra/recepción)
      - 'salida'    → cantidad_delta negativo (uso interno, no venta)
      - 'ajuste'    → fija el stock al valor `stock_final` provisto (cantidad_delta se calcula)
      - 'merma'     → cantidad_delta negativo (deterioro/pérdida)
      - 'devolucion'→ cantidad_delta positivo (devuelto por cliente)
    """
    tipo:        str = Field(..., pattern="^(entrada|salida|ajuste|merma|devolucion)$")
    cantidad:    float = Field(..., description="Cantidad absoluta (>0). Para ajuste se ignora.")
    motivo:      Optional[str]   = None
    stock_final: Optional[float] = None  # Solo para tipo='ajuste'

    @field_validator("cantidad")
    @classmethod
    def cantidad_positiva(cls, v):
        if v <= 0:
            raise ValueError("cantidad debe ser mayor a 0 (el signo lo determina el tipo)")
        return v


class MovimientoInventarioOut(BaseModel):
    id:            str
    producto_id:   str
    sucursal_id:   Optional[str] = None
    tipo:          str
    cantidad:      float
    stock_antes:   float
    stock_despues: float
    motivo:        Optional[str] = None
    referencia_id: Optional[str] = None
    usuario_id:    Optional[int] = None
    fecha:         str

    model_config = {"from_attributes": True}


class AlertaStockBajo(BaseModel):
    """Resumen de un producto con stock bajo o crítico (uso en /api/inventario/alertas)."""
    producto_id:   str
    producto_nombre: str
    sucursal_id:   Optional[str] = None
    sucursal_nombre: Optional[str] = None
    stock:         float
    stock_minimo:  float
    unidad_medida: str
    severidad:     str  # 'warning' | 'critical' | 'agotado'


# ── Categorías ───────────────────────────────────────────────────────
class CategoriaCreate(BaseModel):
    nombre:      str
    sucursal_id: str

    @field_validator("nombre")
    @classmethod
    def nombre_no_vacio(cls, v):
        return validate_non_empty_string(v, "nombre de la categoría")

    @field_validator("sucursal_id")
    @classmethod
    def sucursal_requerida(cls, v):
        return validate_non_empty_string(v, "sucursal")


class CategoriaOut(BaseModel):
    id:          str
    nombre:      str
    activo:      bool
    sucursal_id: Optional[str] = None

    model_config = {"from_attributes": True}


class CategoriaUpdate(BaseModel):
    nombre: str

    @field_validator("nombre")
    @classmethod
    def nombre_no_vacio(cls, v):
        return validate_non_empty_string(v, "nombre")


# ── Ventas (legacy, mantenidas para compatibilidad) ──────────────────
class VentaCreate(BaseModel):
    producto_id:     str
    producto_nombre: Optional[str]   = None
    precio_unitario: Optional[float] = None
    cantidad:        float
    metodo_pago:     MetodoPago
    sucursal_id:     str

    @field_validator("cantidad")
    @classmethod
    def cantidad_positiva(cls, v):
        return validate_positive_number(v, "cantidad")

    @field_validator("sucursal_id")
    @classmethod
    def sucursal_requerida(cls, v):
        return validate_non_empty_string(v, "sucursal")


class VentaOut(BaseModel):
    id:              str
    fecha:           str
    producto_id:     str
    producto_nombre: str
    cantidad:        float
    precio_unitario: float
    total:           float
    metodo_pago:     str
    anulada:         bool = False

    model_config = {"from_attributes": True}


class VentaListOut(BaseModel):
    id:              str
    fecha:           str
    producto_nombre: str
    cantidad:        float
    precio_unitario: float
    total:           float
    metodo_pago:     str
    anulada:         bool = False

    model_config = {"from_attributes": True}


class VentaUpdate(BaseModel):
    metodo_pago: Optional[MetodoPago] = None
    cantidad:    Optional[float]      = None

    @field_validator("cantidad")
    @classmethod
    def cantidad_positiva(cls, v):
        if v is not None and v <= 0:
            raise ValueError("La cantidad debe ser mayor a 0")
        return v


# ── Órdenes (modelo atómico — reemplaza ventas individuales) ─────────
class OrdenItemCreate(BaseModel):
    producto_id:     str
    producto_nombre: Optional[str]   = None
    precio_unitario: Optional[float] = None
    cantidad:        float

    @field_validator("cantidad")
    @classmethod
    def cantidad_positiva(cls, v):
        if v < MIN_QTY_DECIMAL:
            raise ValueError(f"La cantidad debe ser al menos {MIN_QTY_DECIMAL}")
        if v > MAX_QTY_POR_LINEA:
            raise ValueError(f"La cantidad máxima por línea es {MAX_QTY_POR_LINEA:.0f}")
        return round(v, 3)


class PagoMixto(BaseModel):
    """Una porción del total cubierta por un método de pago."""
    metodo: MetodoPago
    monto:  float = Field(..., gt=0)


class OrdenCreate(BaseModel):
    sucursal_id:       str
    metodo_pago:       MetodoPago
    domicilio:         float = 0
    descuento:         float = 0
    cliente_nombre:    Optional[str] = None
    notas:             Optional[str] = None
    efectivo_recibido: Optional[float] = None    # solo si metodo='Efectivo'
    pagos_mixtos:      Optional[List[PagoMixto]] = None  # cuando metodo='Mixto'
    items:             List[OrdenItemCreate]

    @field_validator("sucursal_id")
    @classmethod
    def sucursal_requerida(cls, v):
        return validate_non_empty_string(v, "sucursal")

    @field_validator("items")
    @classmethod
    def items_no_vacio(cls, v):
        if not v:
            raise ValueError("La orden debe tener al menos un producto")
        if len(v) > MAX_LINEAS_CARRITO:
            raise ValueError(f"La orden no puede exceder {MAX_LINEAS_CARRITO} líneas")
        return v

    @field_validator("descuento", "domicilio")
    @classmethod
    def no_negativo(cls, v):
        if v < 0:
            raise ValueError("El valor no puede ser negativo")
        return round(v, 2)


class OrdenItemOut(BaseModel):
    id:              str
    producto_id:     str
    producto_nombre: str
    cantidad:        float
    precio_unitario: float
    total:           float

    model_config = {"from_attributes": True}


class OrdenOut(BaseModel):
    id:                 str
    fecha:              str
    sucursal_id:        Optional[str] = None
    metodo_pago:        str
    subtotal:           float
    descuento:          float = 0
    domicilio:          float
    total:              float
    efectivo_recibido:  Optional[float] = None
    cambio:             Optional[float] = None      # calculado en endpoint
    cliente_nombre:     Optional[str]   = None
    notas:              Optional[str]   = None
    metodo_pago_extra:  Optional[str]   = None
    anulada:            bool = False
    
    # ── DIAN ──
    dian_status:        str = "no_aplica"
    dian_cufe:          Optional[str] = None
    dian_pdf_url:       Optional[str] = None
    dian_xml_url:       Optional[str] = None
    
    items:              List[OrdenItemOut] = []

    model_config = {"from_attributes": True}


class OrdenListOut(BaseModel):
    id:          str
    fecha:       str
    metodo_pago: str
    total:       float
    anulada:     bool = False
    num_items:   int  = 0

    model_config = {"from_attributes": True}


# ── Reportes ─────────────────────────────────────────────────────────
class ReporteProducto(BaseModel):
    producto_id:     Optional[str] = None
    producto_nombre: str
    cantidad_total:  float
    total_ingresos:  float


class ResumenCaja(BaseModel):
    total_dia:    float
    efectivo:     float
    nequi:        float
    daviplata:    float
    tarjeta:      float
    transferencia: float = 0.0


class ReporteDia(BaseModel):
    fecha:         str
    sucursal_id:   str
    productos:     List[ReporteProducto]
    resumen_caja:  ResumenCaja


class TopProducto(BaseModel):
    producto_id:     Optional[str] = None
    nombre:          str
    cantidad:        float
    total:           float


class ReporteDiarioOut(BaseModel):
    """Forma consumida por el dashboard del frontend.

    Combina ventas legacy + órdenes en un set unificado de KPIs.
    """
    fecha:           str
    sucursal_id:     Optional[str] = None
    total_ventas:    float
    total_ordenes:   int
    ticket_promedio: float
    total_items:     float
    por_metodo_pago: dict
    top_productos:   List[TopProducto]


class ReporteRangoOut(BaseModel):
    """Reporte agregado para un rango de fechas.

    Devuelve además una serie diaria para gráficas.
    """
    desde:           str
    hasta:           str
    sucursal_id:     Optional[str] = None
    total_ventas:    float
    total_ordenes:   int
    ticket_promedio: float
    total_items:     float
    por_metodo_pago: dict
    top_productos:   List[TopProducto]
    serie_diaria:    list[dict]   # [{fecha, total_ventas, total_ordenes}]


# ── Auth ─────────────────────────────────────────────────────────────
class RegisterRequest(BaseModel):
    email:       EmailStr
    password:    str
    nombre:      str
    propietario: str = ""
    telefono:    str = ""


class LoginRequest(BaseModel):
    email:    EmailStr
    password: str


class TokenResponse(BaseModel):
    access_token: str
    token_type:   str = "bearer"
    nombre:       str = ""
    es_admin:     bool = False


class RegisterResponse(BaseModel):
    access_token: str
    token_type:   str = "bearer"
    nombre:       str
    es_admin:     bool = False


# ══ v3 — Auth con roles + refresh tokens ═════════════════════════════
class UsuarioPublico(BaseModel):
    id:          int
    email:       str
    nombre:      str
    rol:         str
    tenant_id:   int
    sucursal_id: str | None = None


class TokenPair(BaseModel):
    """Respuesta estándar de endpoints de auth v3: access + refresh + datos usuario."""
    access_token:  str
    refresh_token: str
    token_type:    str = "bearer"
    expires_in:    int                  # segundos
    usuario:       UsuarioPublico


class RegisterV3Request(BaseModel):
    """Registro de un nuevo NEGOCIO (tenant) + su usuario owner."""
    email:            EmailStr
    password:         str = Field(..., min_length=8, description="Mínimo 8 caracteres")
    nombre_comercial: str = Field(..., min_length=2, max_length=100)
    nombre_propietario: str = Field(..., min_length=2)
    nicho:            str = Field(default="restaurante",
                                   pattern="^(restaurante|retail|farmacia|servicio|otro)$")
    telefono:         str = ""


class RefreshRequest(BaseModel):
    refresh_token: str


class LoginPinRequest(BaseModel):
    tenant_id: int
    pin:       str = Field(..., min_length=4, max_length=6, pattern="^[0-9]+$")


class CrearUsuarioRequest(BaseModel):
    """Owner/Manager crea un usuario operativo para su tenant."""
    email:       EmailStr
    password:    str = Field(..., min_length=6)
    nombre:      str = Field(..., min_length=2)
    rol:         str = Field(..., pattern="^(manager|cajero|inventario)$")
    sucursal_id: str | None = None
    pin:         str | None = Field(None, pattern="^[0-9]{4,6}$")


# ════════════════════════════════════════════════════════════════════════
#  ML / FORECASTING — Schemas para el módulo de inteligencia (Fase 2)
# ════════════════════════════════════════════════════════════════════════
class ForecastPunto(BaseModel):
    """Una predicción puntual: demanda esperada para un día."""
    fecha:         str            # ISO date YYYY-MM-DD
    demanda:       float
    intervalo_inf: Optional[float] = None
    intervalo_sup: Optional[float] = None


class ForecastResponse(BaseModel):
    """Predicción completa para un producto sobre N días futuros."""
    producto_id:    str
    producto_nombre: str
    sucursal_id:    str
    modelo_tipo:    str            # "baseline" | "prophet"
    horizonte_dias: int
    demanda_total:  float          # suma del horizonte (útil para sugerir reorden)
    rmse:           Optional[float] = None
    entrenado_en:   Optional[str]  = None
    puntos:         list[ForecastPunto]


class MlAlertaOut(BaseModel):
    """Alerta inteligente generada por ML."""
    id:             int
    tipo:           str
    severidad:      str
    titulo:         str
    mensaje:        str
    recomendacion:  Optional[str] = None
    producto_id:    Optional[str] = None
    sucursal_id:    Optional[str] = None
    metadata:       Optional[dict] = None
    leida:          bool
    creada_en:      str


class RestockSugerencia(BaseModel):
    """Sugerencia de reorden basada en pronóstico vs stock actual."""
    producto_id:        str
    producto_nombre:    str
    sucursal_id:        str
    sucursal_nombre:    Optional[str] = None
    stock_actual:       float
    demanda_proyectada: float          # próximos N días
    dias_cobertura:     Optional[float]  # cuántos días alcanza el stock
    cantidad_sugerida:  float          # cuánto pedir para llegar a target
    urgencia:           str            # "baja" | "media" | "alta" | "critica"


class TrainResultOut(BaseModel):
    """Resultado del entrenamiento de modelos para un tenant."""
    tenant_id:           int
    productos_evaluados: int
    modelos_entrenados:  int
    modelos_omitidos:    int           # por falta de datos
    forecasts_generados: int
    alertas_creadas:     int
    duracion_segundos:   float
    modelo_tipo:         str
