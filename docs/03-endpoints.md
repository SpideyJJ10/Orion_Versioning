# 03-endpoints.md — Mapa de API REST (Endpoints)

> **Servidor Base**: `http://localhost:8000` (Desarrollo) / `https://orion-pos.onrender.com` (Producción)
> **Formato**: JSON (Pydantic v2)
> **Autenticación**: Header `Authorization: Bearer <access_token>`

---

## 1. Autenticación y Usuarios (Auth v3)

| Método | Ruta | Descripción | Auth | Respuesta |
|--------|------|-------------|------|-----------|
| `POST` | `/api/v3/auth/register` | Registro de un nuevo Tenant + Usuario Owner | Pública | `TokenPair` (access, refresh, usuario) |
| `POST` | `/api/v3/auth/login` | Inicio de sesión con Email + Password | Pública | `TokenPair` |
| `POST` | `/api/v3/auth/login-pin` | Login rápido de cajeros con Tenant ID + PIN | Pública | `TokenPair` |
| `POST` | `/api/v3/auth/refresh` | Renovación de access_token expirado | Pública | `TokenPair` |
| `GET`  | `/api/v3/auth/me` | Obtiene el perfil del usuario autenticado | Bearer | `UsuarioPublico` |
| `GET`  | `/api/v3/usuarios` | Lista los usuarios del tenant actual | Owner/Manager | `List[UsuarioResponse]` |
| `POST` | `/api/v3/usuarios` | Crea un nuevo empleado (cajero/manager) | Owner/Manager | `UsuarioResponse` |
| `DELETE` | `/api/v3/usuarios/{id}` | Desactiva a un usuario del tenant | Owner | `{ "message": "..." }` |

---

## 2. Orion IA (OIA) & Onboarding Conversacional

| Método | Ruta | Descripción | Auth | Respuesta |
|--------|------|-------------|------|-----------|
| `GET`  | `/api/oai/templates` | Lista plantillas por industria (restaurante, barbería, etc.) | Pública | `List[TemplateOut]` |
| `POST` | `/api/oai/chat` | Chat conversacional con el asistente de creación OIA | Pública | `OIAChatResponse` (reply, extracted, ready_to_provision) |
| `POST` | `/api/oai/provision` | Aprovisiona el tenant completo en 7 pasos atómicos | Pública | `ProvisionResponse` (tokens, tenant_id, checklist) |
| `GET`  | `/api/v3/onboarding` | Estado del progreso del tutorial | Bearer | `OnboardingProgressResponse` |
| `PATCH`| `/api/v3/onboarding` | Actualiza un paso completado del tutorial | Bearer | `OnboardingProgressResponse` |

---

## 3. Productos y Categorías

| Método | Ruta | Descripción | Auth | Respuesta |
|--------|------|-------------|------|-----------|
| `GET`  | `/api/productos` | Lista catálogo de productos (filtra por sucursal_id) | Bearer | `List[ProductoOut]` |
| `POST` | `/api/productos` | Crea un nuevo producto (con movimiento de stock inicial) | Bearer | `ProductoOut` |
| `GET`  | `/api/productos/{id}` | Obtiene detalle de un producto | Bearer | `ProductoOut` |
| `PUT`  | `/api/productos/{id}` | Modifica datos del producto (precio, nombre, min) | Bearer | `ProductoOut` |
| `DELETE` | `/api/productos/{id}` | Soft-delete de un producto | Bearer | `{ "message": "..." }` |
| `POST` | `/api/productos/{id}/ajuste-stock` | Registra ajuste manual de stock (+ entrada / - salida) | Bearer | `ProductoOut` |
| `GET`  | `/api/categorias` | Lista categorías de productos | Bearer | `List[CategoriaOut]` |
| `POST` | `/api/categorias` | Crea una nueva categoría | Bearer | `CategoriaOut` |

---

## 4. Órdenes y POS

| Método | Ruta | Descripción | Auth | Respuesta |
|--------|------|-------------|------|-----------|
| `GET`  | `/api/ordenes` | Lista órdenes registradas (filtra por fecha/sucursal) | Bearer | `List[OrdenOut]` |
| `POST` | `/api/ordenes` | Registra una orden atómica (descuenta stock, crea ledger) | Bearer | `OrdenOut` |
| `POST` | `/api/ordenes/{id}/anular` | Anula una orden (requiere PIN autorizador, restaura stock) | Bearer | `{ "message": "..." }` |
| `GET`  | `/api/ordenes/{id}/recibo` | Trae datos formateados para impresión de tirilla/ticket | Bearer | `ReciboOrdenOut` |

---

## 5. Mesas (Restaurante / Cafetería)

| Método | Ruta | Descripción | Auth | Respuesta |
|--------|------|-------------|------|-----------|
| `GET`  | `/api/sucursales/{sucursal_id}/mesas` | Lista mapa de mesas y su estado en tiempo real | Bearer | `List[MesaOut]` |
| `POST` | `/api/sucursales/{sucursal_id}/mesas` | Crea una mesa individual | Bearer | `MesaOut` |
| `PATCH`| `/api/mesas/{id}/estado` | Cambia estado de la mesa (libre, ocupada, cuenta_pedida) | Bearer | `MesaOut` |
| `POST` | `/api/mesas/{id}/vincular-orden` | Asocia una orden activa a la mesa | Bearer | `MesaOut` |

---

## 6. Inventario y Cierres de Caja

| Método | Ruta | Descripción | Auth | Respuesta |
|--------|------|-------------|------|-----------|
| `GET`  | `/api/inventario/summary` | KPIs de stock total, valor del inventario y alertas | Bearer | `InventarioSummaryOut` |
| `GET`  | `/api/inventario/alertas` | Productos por debajo de stock mínimo | Bearer | `List[ProductoAlertOut]` |
| `GET`  | `/api/inventario/movimientos` | Historial / Ledger de movimientos de stock | Bearer | `List[MovimientoInventarioOut]` |
| `POST` | `/api/reportes/cierre` | Registra el cierre diario de caja y descuadres | Bearer | `CierreCajaOut` |
| `GET`  | `/api/reportes/rango` | Reporte acumulado de ventas por rango de fechas | Bearer | `ReporteRangoOut` |

---

## 7. Branding, Pagos y Meta

| Método | Ruta | Descripción | Auth | Respuesta |
|--------|------|-------------|------|-----------|
| `GET`  | `/api/v3/branding` | Obtiene el branding visual del tenant | Bearer | `BrandingResponse` |
| `PUT`  | `/api/v3/branding` | Actualiza la paleta de colores, tema y nicho | Bearer | `BrandingResponse` |
| `POST` | `/api/v3/payments/create-checkout-session` | Crea URL de pago Stripe Checkout para suscripción | Owner | `{ "checkout_url": "..." }` |
| `POST` | `/api/v3/payments/webhook` | Recibe webhooks de Stripe sobre suscripciones | Firma Stripe | `{ "status": "success" }` |
| `GET`  | `/api/health` | Probe de salud de API y conexión a DB | Pública | `{ "status": "ok", "service": "orion" }` |
