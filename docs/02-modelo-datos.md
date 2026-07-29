# 02-modelo-datos.md — Esquema de Base de Datos y Modelo Entidad-Relación

## 1. Visión General del Modelo

El modelo de datos de Orion está diseñado bajo el principio de **Multi-tenancy nativo atómico**. Cada entidad operativa pertenece estrictamente a un `tenant_id`, lo que garantiza el aislamiento total de datos entre negocios.

---

## 2. Esquema de Tablas y Relaciones

### `tenants`
Representa a la empresa o negocio suscrito al SaaS.
- `id` (INT, PK, Autoincrement): ID único del tenant.
- `email` (VARCHAR, Unique, Index): Correo electrónico del propietario.
- `password_hash` (VARCHAR): Hash bcrypt de la contraseña.
- `nombre` (VARCHAR): Nombre del negocio.
- `propietario` (VARCHAR, Nullable): Nombre del dueño.
- `telefono` (VARCHAR, Nullable): Teléfono de contacto.
- `plan` (VARCHAR, Default 'starter'): Plan de suscripción (starter|pro|business).
- `activo` (BOOL, Default True): Estado de la cuenta.
- `plan_activo` (BOOL, Default True): Estado de cobrabilidad del plan.
- `fecha_vencimiento` (DATETIME, Nullable): Fecha límite del plan.
- `metodos_pago` (JSON, Nullable): Configuración de métodos de pago aceptados.
- `stripe_customer_id` (VARCHAR, Nullable, Index): ID cliente Stripe.
- `stripe_subscription_id` (VARCHAR, Nullable, Index): ID suscripción Stripe.
- `subscription_status` (VARCHAR, Nullable): Estado en Stripe (active|canceled).
- `creado_en` (DATETIME, Default UTC): Fecha de creación.

---

### `sucursales`
Locales o puntos de venta pertenecientes a un tenant.
- `id` (VARCHAR, PK, UUID): Identificador de la sucursal.
- `tenant_id` (INT, FK -> tenants.id, CASCADE, Index): ID del tenant.
- `nombre` (VARCHAR): Nombre del local (ej. "Sede Principal").
- `activo` (BOOL, Default True).

---

### `usuarios`
Empleados y operadores del sistema.
- `id` (INT, PK, Autoincrement): ID del usuario.
- `tenant_id` (INT, FK -> tenants.id, CASCADE, Index): ID del tenant.
- `email` (VARCHAR, Index): Email de ingreso.
- `password_hash` (VARCHAR): Hash bcrypt de la contraseña.
- `nombre` (VARCHAR): Nombre completo del empleado.
- `rol` (VARCHAR): Rol operativo (`owner`, `manager`, `cajero`, `inventario`).
- `sucursal_id` (VARCHAR, FK -> sucursales.id, SET NULL, Nullable, Index).
- `pin` (VARCHAR(6), Nullable, Index): PIN numérico de ingreso rápido en POS.
- `activo` (BOOL, Default True).
- `creado_en` / `ultimo_login` (DATETIME).
- *Constraint*: `UniqueConstraint("tenant_id", "email")`.

---

### `productos`
Catálogo de productos vendidos por sucursal.
- `id` (VARCHAR, PK, UUID).
- `tenant_id` (INT, FK -> tenants.id, CASCADE, Index).
- `sucursal_id` (VARCHAR, FK -> sucursales.id, CASCADE, Nullable, Index).
- `nombre` (VARCHAR): Nombre comercial del producto.
- `precio` (FLOAT): Precio de venta al público.
- `costo` (FLOAT, Default 0.0): Costo unitario para cálculo de margen.
- `insumos` (TEXT, Default ""): Receta / ingredientes (opcional).
- `descripcion` (TEXT, Nullable).
- `sku` (VARCHAR, Nullable, Index): Código de barras.
- `categoria` (VARCHAR, Default 'General'): Nombre de la categoría.
- `categoria_id` (VARCHAR, FK -> categorias.id, Nullable, Index).
- `stock` (FLOAT, Default 0.0): Cantidad disponible en inventario.
- `stock_minimo` (FLOAT, Default 0.0): Umbral para alerta de reabastecimiento.
- `unidad_medida` (VARCHAR, Default 'unidad'): unidad|kg|lt|gr|ml|pack.
- `activo` (BOOL, Default True).

---

### `categorias`
Categorías de productos.
- `id` (VARCHAR, PK, UUID).
- `tenant_id` (INT, FK -> tenants.id, CASCADE, Index).
- `sucursal_id` (VARCHAR, FK -> sucursales.id, CASCADE, Nullable, Index).
- `nombre` (VARCHAR): Nombre de la categoría.
- `activo` (BOOL, Default True).

---

### `mesas`
Control de mesas físicas para restaurantes.
- `id` (VARCHAR, PK, UUID).
- `tenant_id` (INT, FK -> tenants.id, CASCADE, Index).
- `sucursal_id` (VARCHAR, FK -> sucursales.id, CASCADE, Index).
- `numero` (INT): Número visible en el mapa de mesas.
- `nombre` (VARCHAR, Nullable): Nombre descriptivo (ej. "Terraza 1").
- `capacidad` (INT, Default 4).
- `estado` (VARCHAR, Default 'libre', Index): libre|ocupada|reservada|cuenta_pedida.
- `orden_id` (VARCHAR, FK -> ordenes.id, SET NULL, Nullable): Orden activa asociada.
- `notas` (VARCHAR, Nullable).

---

### `ordenes`
Transacciones atómicas completas de venta.
- `id` (VARCHAR, PK, UUID).
- `tenant_id` (INT, FK -> tenants.id, CASCADE, Index).
- `sucursal_id` (VARCHAR, FK -> sucursales.id, CASCADE, Index).
- `fecha` (DATETIME, Index).
- `metodo_pago` (VARCHAR): Efectivo|Tarjeta|Nequi|Daviplata|Transferencia|Mixto.
- `subtotal` / `descuento` / `domicilio` / `total` (FLOAT).
- `efectivo_recibido` (FLOAT, Nullable).
- `metodo_pago_extra` (VARCHAR, Nullable): JSON con detalle en pago mixto.
- `cliente_nombre` (VARCHAR, Nullable).
- `notas` (TEXT, Nullable).
- `usuario_id` (INT, FK -> usuarios.id, SET NULL, Nullable).
- `anulada` (BOOL, Default False).
- `dian_status` (VARCHAR, Default 'no_aplica'): no_aplica|pending|issued|failed.
- `dian_cufe` (VARCHAR, Nullable).

---

### `orden_items`
Líneas de detalle dentro de una orden.
- `id` (VARCHAR, PK, UUID).
- `orden_id` (VARCHAR, FK -> ordenes.id, CASCADE, Index).
- `producto_id` (VARCHAR): ID del producto.
- `producto_nombre` (VARCHAR): Nombre en el momento de la venta.
- `cantidad` (FLOAT).
- `precio_unitario` (FLOAT).
- `total` (FLOAT).

---

### `movimientos_inventario`
Ledger histórico de movimientos de stock.
- `id` (VARCHAR, PK, UUID).
- `tenant_id` (INT, FK -> tenants.id, CASCADE, Index).
- `sucursal_id` (VARCHAR, FK -> sucursales.id, CASCADE, Nullable, Index).
- `producto_id` (VARCHAR, FK -> productos.id, CASCADE, Index).
- `tipo` (VARCHAR, Index): entrada|salida|ajuste|venta|merma|devolucion.
- `cantidad` (FLOAT): Con signo (positivo entra, negativo sale).
- `stock_antes` / `stock_despues` (FLOAT).
- `motivo` (VARCHAR, Nullable).
- `referencia_id` (VARCHAR, Nullable, Index): ej. orden_id.
- `usuario_id` (INT, FK -> usuarios.id, SET NULL, Nullable).
- `fecha` (DATETIME, Index).

---

### `cierre_caja`
Cierres diarios de turno y control de descuadres.
- `id` (INT, PK, Autoincrement).
- `tenant_id` (INT, FK -> tenants.id, CASCADE, Index).
- `sucursal_id` (VARCHAR, FK -> sucursales.id, CASCADE, Index).
- `fecha_cierre` (DATETIME, Default UTC, Index).
- `total_teorico` (FLOAT): Suma de ventas en sistema.
- `total_real` (FLOAT): Dinero contado en caja física.
- `diferencia` (FLOAT): `total_real - total_teorico` (descuadre).
- `notas` (TEXT, Nullable).

---

### `tenant_branding`
Branding e identidad visual por tenant (1:1).
- `tenant_id` (INT, FK -> tenants.id, CASCADE, PK).
- `color_primary` / `color_secondary` / `color_accent` (VARCHAR(7)).
- `nombre_comercial` (VARCHAR).
- `logo_url` (VARCHAR, Nullable).
- `nicho` (VARCHAR, Default 'restaurante').
- `tema` (VARCHAR, Default 'dark').
- `tipografia` (VARCHAR, Default 'Inter').
- `categorias_default` (JSON).

---

### `onboarding_progress`
Progreso del tutorial interactivo (1:1).
- `tenant_id` (INT, FK -> tenants.id, CASCADE, PK).
- `perfil_configurado` / `primer_producto` / `primera_venta` / `saltado` (BOOL).

---

### Tablas de Inteligencia ML (`ml_model_metadata`, `forecast_series`, `ml_alerts`)
- Persisten parámetros de modelos predictivos, estimaciones de demanda futura (`fecha_target`, `demanda`, `intervalo_inf`, `intervalo_sup`) y alertas automáticas de reabastecimiento.

---

## 3. Gaps Identificados y Resueltos

1. **Garantía Multi-Tenant (`tenant_id`)**:
   - Resuelto: Todas las consultas y llaves foráneas incluyen `tenant_id` con índices dedicados. Además, se habilitó Supabase RLS SQL en producción.
2. **Atomicidad de Ventas e Inventario**:
   - Resuelto: Reemplazado el modelo plano de ventas por `ordenes` + `orden_items` + `movimientos_inventario` en una sola transacción SQL.
3. **Control de Descuadres de Caja (`cierre_caja`)**:
   - Resuelto: Fila explícita para registrar cierres de turno, calcular descuadres (`total_real - total_teorico`) y dejar constancia de auditoría.
