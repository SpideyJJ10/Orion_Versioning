/**
 * Tipos TypeScript del API de Orion POS.
 * Mantener sincronizado con `backend/schemas/api.py`.
 *
 * Convenciones:
 *  - IDs son strings (UUID) salvo `tenant_id` y `usuario_id` (Integer).
 *  - Cantidades son `number` (Float) — POS soporta ventas decimales (kg, lt, gr, ml).
 *  - Fechas vienen como ISO o "YYYY-MM-DD HH:MM:SS" desde el backend (ver formatters).
 */

// ─────────────────────────────────────────────────────────────────────────
// Auth
// ─────────────────────────────────────────────────────────────────────────
export type Rol = "super_admin" | "owner" | "manager" | "inventario" | "cajero";

export interface UsuarioPublico {
  id:          number;
  email:       string;
  nombre:      string;
  rol:         Rol;
  tenant_id:   number;
  sucursal_id: string | null;
}

/** Respuesta estándar de /api/v3/auth/{login,register,refresh,login-pin}. */
export interface TokenPair {
  access_token:  string;
  refresh_token: string;
  token_type:    string;        // "bearer"
  expires_in:    number;        // segundos
  usuario:       UsuarioPublico;
}

export interface LoginRequest {
  email:    string;
  password: string;
}

export interface LoginPinRequest {
  tenant_id: number;
  pin:       string;
}

export type Nicho = "restaurante" | "retail" | "farmacia" | "servicio" | "otro";

export interface RegisterRequest {
  email:              string;
  password:           string;
  nombre_comercial:   string;
  nombre_propietario: string;
  telefono?:          string;
  nicho:              Nicho;
}

export interface CrearUsuarioRequest {
  email:        string;
  password:     string;
  nombre:       string;
  rol:          Exclude<Rol, "owner" | "super_admin">;
  sucursal_id?: string | null;
  pin?:         string | null;
}

// ─────────────────────────────────────────────────────────────────────────
// Sucursales y Categorías
// ─────────────────────────────────────────────────────────────────────────
export interface Sucursal {
  id:     string;
  nombre: string;
  activo: boolean;
}

export interface Categoria {
  id:          string;
  nombre:      string;
  activo:      boolean;
  sucursal_id: string | null;
}

// ─────────────────────────────────────────────────────────────────────────
// Productos
// ─────────────────────────────────────────────────────────────────────────
export type UnidadMedida =
  | "unidad" | "kg" | "lt" | "gr" | "ml"
  | "pack"   | "caja" | "docena";

export interface Producto {
  id:             string;
  nombre:         string;
  precio:         number;
  costo:          number;
  insumos:        string;
  descripcion:    string | null;
  sku:            string | null;
  imagen_url:     string | null;
  categoria:      string;          // nombre legible
  activo:         boolean;
  sucursal_id:    string | null;
  stock:          number;
  stock_minimo:   number;
  unidad_medida:  UnidadMedida | string;
}

/** Body para POST /api/productos. */
export interface ProductoCrearRequest {
  nombre:         string;
  precio:         number;
  costo?:         number;
  insumos?:       string;
  descripcion?:   string | null;
  sku?:           string | null;
  imagen_url?:    string | null;
  categoria?:     string;          // nombre (back-end resuelve a categoria_id)
  sucursal_id:    string;
  stock?:         number;
  stock_minimo?:  number;
  unidad_medida?: UnidadMedida | string;
}

/** Body para PUT /api/productos/{id}. Todos opcionales. */
export type ProductoActualizarRequest = Partial<ProductoCrearRequest> & {
  activo?: boolean;
};

// ─────────────────────────────────────────────────────────────────────────
// Inventario
// ─────────────────────────────────────────────────────────────────────────
export type TipoMovimiento =
  | "entrada" | "salida" | "ajuste" | "venta" | "merma" | "devolucion";

export interface MovimientoInventario {
  id:            string;
  tenant_id:     number;
  sucursal_id:   string | null;
  producto_id:   string;
  tipo:          TipoMovimiento | string;
  cantidad:      number;       // signed: positivo entra, negativo sale
  stock_antes:   number;
  stock_despues: number;
  motivo:        string | null;
  referencia_id: string | null;
  usuario_id:    number | null;
  fecha:         string;
}

export interface AjusteStockRequest {
  cantidad:     number;        // signed
  motivo?:      string;
  // Backend usa endpoint /api/productos/{id}/ajuste-stock
}

export type SeveridadStock = "warning" | "critical" | "agotado";

export interface AlertaStock {
  producto_id:     string;
  producto_nombre: string;
  sucursal_id:     string | null;
  sucursal_nombre: string | null;
  stock:           number;
  stock_minimo:    number;
  unidad_medida:   string;
  severidad:       SeveridadStock;
}

export interface InventarioSummary {
  total_productos:        number;
  total_unidades:         number;
  valor_inventario:       number;
  productos_sin_stock:    number;
  productos_stock_bajo:   number;
  movimientos_ultimos_7d: number;
}

// ─────────────────────────────────────────────────────────────────────────
// Órdenes / POS
// ─────────────────────────────────────────────────────────────────────────
export type MetodoPago =
  | "Efectivo" | "Nequi" | "Daviplata" | "Tarjeta" | "Transferencia" | "Mixto";

export interface OrdenItem {
  id:              string;
  producto_id:     string;
  producto_nombre: string;
  cantidad:        number;
  precio_unitario: number;
  total:           number;
}

export interface OrdenItemInput {
  producto_id:      string;
  producto_nombre?: string;
  precio_unitario?: number;
  cantidad:         number;
}

export interface PagoMixto {
  metodo: MetodoPago;
  monto:  number;
}

export interface Orden {
  id:                string;
  fecha:             string;
  sucursal_id:       string | null;
  metodo_pago:       MetodoPago | string;
  subtotal:          number;
  descuento:         number;
  domicilio:         number;
  total:             number;
  efectivo_recibido: number | null;
  cambio:            number | null;
  cliente_nombre:    string | null;
  notas:             string | null;
  metodo_pago_extra: string | null;     // JSON string con PagoMixto[]
  anulada:           boolean;
  items:             OrdenItem[];
}

export interface OrdenListItem {
  id:          string;
  fecha:       string;
  metodo_pago: string;
  total:       number;
  anulada:     boolean;
  num_items:   number;
}

export interface CrearOrdenRequest {
  sucursal_id:        string;
  metodo_pago:        MetodoPago;
  domicilio?:         number;
  descuento?:         number;
  cliente_nombre?:    string | null;
  notas?:             string | null;
  efectivo_recibido?: number | null;
  pagos_mixtos?:      PagoMixto[];
  items:              OrdenItemInput[];
}

/** Respuesta de GET /api/ordenes/{id}/recibo (datos para imprimir el ticket). */
export interface ReciboData {
  orden:   Orden;
  negocio: {
    nombre_comercial: string;
    logo_url:         string | null;
    color_primary:    string;
    sucursal:         string | null;
    telefono:         string | null;
  };
  pago: {
    metodo:            string;
    efectivo_recibido: number | null;
    cambio:            number | null;
    pagos_mixtos:      PagoMixto[];
  };
}

// ─────────────────────────────────────────────────────────────────────────
// Reportes
// ─────────────────────────────────────────────────────────────────────────
export interface TopProducto {
  producto_id: string | null;
  nombre:      string;
  cantidad:    number;
  total:       number;
}

/** GET /api/reportes/diario — KPIs del dashboard. */
export interface ReporteDiario {
  fecha:           string;
  sucursal_id:     string | null;
  total_ventas:    number;
  total_ordenes:   number;
  ticket_promedio: number;
  total_items:     number;
  por_metodo_pago: Record<string, number>;
  top_productos:   TopProducto[];
}

export interface SerieDiariaPunto {
  fecha:         string;
  total_ventas:  number;
  total_ordenes: number;
}

/** GET /api/reportes/rango — KPIs agregados + serie diaria. */
export interface ReporteRango {
  desde:           string;
  hasta:           string;
  sucursal_id:     string | null;
  total_ventas:    number;
  total_ordenes:   number;
  ticket_promedio: number;
  total_items:     number;
  por_metodo_pago: Record<string, number>;
  top_productos:   TopProducto[];
  serie_diaria:    SerieDiariaPunto[];
}

/** Cierre de caja legacy (GET /api/reportes/dia). */
export interface ResumenCaja {
  total_dia:     number;
  efectivo:      number;
  nequi:         number;
  daviplata:     number;
  tarjeta:       number;
  transferencia: number;
}

export interface ReporteDia {
  fecha:        string;
  sucursal_id:  string;
  productos: {
    producto_id?:    string | null;
    producto_nombre: string;
    cantidad_total:  number;
    total_ingresos:  number;
  }[];
  resumen_caja: ResumenCaja;
}

// ─────────────────────────────────────────────────────────────────────────
// ML
// ─────────────────────────────────────────────────────────────────────────
export interface ForecastPunto {
  fecha:         string;
  demanda:       number;
  intervalo_inf: number;
  intervalo_sup: number;
}

export interface ForecastResponse {
  producto_id:     string;
  producto_nombre: string;
  sucursal_id:     string;
  modelo_tipo:     "baseline" | "prophet";
  horizonte_dias:  number;
  demanda_total:   number;
  rmse:            number | null;
  entrenado_en:    string | null;
  puntos:          ForecastPunto[];
}

export type AlertaSeveridad = "info" | "warning" | "critical";

export type AlertaTipo =
  | "stockout_riesgo"
  | "sobrestock"
  | "producto_estrella"
  | "demanda_anomala";

export interface MlAlerta {
  id:            number;
  tipo:          AlertaTipo;
  severidad:     AlertaSeveridad;
  titulo:        string;
  mensaje:       string;
  recomendacion: string | null;
  producto_id:   string | null;
  sucursal_id:   string | null;
  metadata:      Record<string, unknown> | null;
  leida:         boolean;
  creada_en:     string;
}

export interface RestockSuggestion {
  producto_id:        string;
  producto_nombre:    string;
  sucursal_id:        string;
  sucursal_nombre:    string;
  stock_actual:       number;
  demanda_proyectada: number;
  dias_cobertura:     number;
  cantidad_sugerida:  number;
  urgencia:           "critica" | "alta" | "media" | "baja";
}

export interface MlStatus {
  prophet_disponible:    boolean;
  modelos_entrenados:    number;
  forecasts_persistidos: number;
  alertas_no_leidas:     number;
  ultimo_entrenamiento:  string | null;
  rmse_promedio:         number | null;
  mape_promedio:         number | null;
}

export interface MlTrainResult {
  tenant_id:           number;
  productos_evaluados: number;
  modelos_entrenados:  number;
  modelos_omitidos:    number;
  forecasts_generados: number;
  alertas_creadas:     number;
  duracion_segundos:   number;
  modelo_tipo:         string;
}

// ─────────────────────────────────────────────────────────────────────────
// Branding (alineado con backend: TenantBranding ORM)
// ─────────────────────────────────────────────────────────────────────────
export type BrandingTema = "dark" | "light" | "warm";

export interface Branding {
  nombre_comercial:    string;
  nicho:               Nicho | string;
  logo_url:            string | null;
  color_primary:       string;        // hex #rrggbb
  color_secondary:     string;
  color_accent:        string;
  tema:                BrandingTema;
  tipografia:          string;
  categorias_default:  string[];
  actualizado_en?:     string;
}

export interface BrandingUpdateRequest {
  nombre_comercial?:   string;
  nicho?:              Nicho | string;
  logo_url?:           string | null;
  color_primary?:      string;
  color_secondary?:    string;
  color_accent?:       string;
  tema?:               BrandingTema;
  tipografia?:         string;
  categorias_default?: string[];
}

// ─────────────────────────────────────────────────────────────────────────
// Onboarding
// ─────────────────────────────────────────────────────────────────────────
export interface OnboardingProgress {
  perfil_configurado: boolean;
  primer_producto:    boolean;
  primera_venta:      boolean;
  saltado:            boolean;
  porcentaje:         number;
}
