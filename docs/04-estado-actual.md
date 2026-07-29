# 04-estado-actual.md — Estado Actual del Proyecto

> **Última Actualización**: 29 de Julio, 2026
> **Estado General**: ✅ v1 Producción Lista — 100/100 Tests en Verde, Servidores Activos

---

## 1. Servidores Activos (Dev Local)

| Servicio       | URL                        | Estado                         |
|---------------|----------------------------|--------------------------------|
| Backend API   | http://localhost:8000      | ✅ UP — `200 OK` en `/api/health` |
| Frontend Web  | http://localhost:3000      | ✅ UP — Next.js 14.2.35         |
| API Docs      | http://localhost:8000/docs | ✅ Swagger UI disponible        |

---

## 2. Lo que está HECHO (100% Funcional y Probado)

### Backend API Core (`apps/api-core`)
- [x] **Arquitectura Multi-tenant**: Aislamiento total de datos por `tenant_id` en todas las consultas y relaciones SQLAlchemy.
- [x] **Autenticación v3**:
  - Emisión y verificación de pares JWT (Access token de 8h + Refresh token de 30 días).
  - PIN de 4 a 6 dígitos para ingreso ultra-rápido de cajeros en POS.
  - Granularidad de roles (`owner`, `manager`, `cajero`, `inventario`).
  - Hashing seguro con `bcrypt` y protección brute-force / rate-limiting (`slowapi`).
- [x] **Punto de Venta (POS) & Mesas**:
  - Registro de Órdenes atómicas con cálculo de subtotal, descuentos y domicilios.
  - Gestión de mesas en tiempo real (`libre`, `ocupada`, `reservada`, `cuenta_pedida`).
  - Generación de Recibo / Tirilla para impresión.
- [x] **Control de Inventario y Cierres**:
  - Ledger histórico de auditoría (`movimientos_inventario`).
  - Descuento de stock en tiempo real e incremento al anular órdenes.
  - Registro de Cierres de Caja (`cierre_caja`) con cálculo de descuadres.
- [x] **Orion IA (OIA) & Onboarding**:
  - Chat conversacional en `/api/oai/chat` para captura de perfiles de negocio.
  - Soporte dual LLM: OpenAI GPT-4o-mini (Cloud) o **LM Studio local** (`http://localhost:1234/v1`).
  - Endpoint de aprovisionamiento `/api/oai/provision` que genera Tenant, Sucursal, Branding, Usuario y Mesas en una sola transacción.
- [x] **Módulo ML Predictivo**:
  - Modelos Baseline (Media Móvil + Estacionalidad Semanal) y Prophet para previsión de demanda.
  - Generación automática de alertas inteligentes de sobrestock y riesgo de agotamiento (`ml_alerts`).
- [x] **Pagos Stripe**:
  - Checkout sessions para planes `starter`, `pro`, `business`.
  - Webhook handler para `checkout.session.completed` y `customer.subscription.deleted`.
  - Bug del variable `plan_tier` vs `plan` **corregido** (Julio 2026).
- [x] **Suite de Pruebas**:
  - **100/100 Pruebas automatizadas en verde** — Python 3.14.4, pytest 9.1.0.

---

### Frontend Web App (`apps/web-app`)
- [x] **PWA Offline-First**:
  - Integración de Dexie (IndexedDB `Orion_OfflineDB`) con versión 2 de esquema.
  - Caché local automático para Productos, Categorías y Sucursales.
  - Caída transparente a base de datos local en React Query ante pérdidas de red.
  - Cola local `offlineOrders` con sincronización en segundo plano mediante `SyncManager`.
- [x] **UI/UX Adaptativa & White-Label**:
  - Inyección dinámica de branding (`color_primary`, `color_secondary`, `logo_url`) en Next.js.
  - Remoción completa de marcas legacy "Orion POS" en favor de la marca limpia "Orion".
  - Pantallas adaptativas por nicho (Restaurante, Barbería, Farmacia, Retail, Servicios).
- [x] **TypeScript**: 0 errores de compilación (`tsc --noEmit` limpio).
- [x] **Sentry Next.js 14+**: Migrado a `instrumentation.ts` + `global-error.tsx` (sin warnings).

---

## 3. Lo que está A MEDIAS / EN PROGRESO

- [ ] **Integración DIAN con Proveedor Autorizado Certificado**:
  - El backend cuenta con el modelo `dian_status`, `dian_cufe` y la interfaz `dian.py` que soporta llamadas HTTP asíncronas. Actualmente funciona en modo `disabled` / `mock` para demos sin enviar facturas reales a la DIAN hasta conectar credenciales de Siigo o Facturatech.
- [ ] **App Móvil Nativa "Aura"**:
  - Proyecto Flutter en planificación para visualización rápida de KPIs desde celulares iOS/Android.

---

## 4. Lo que FALTA / Próximos Pasos (Hoja de Ruta Inmediata)

1. **Despliegue a Producción**:
   - Ejecutar la migración PostgreSQL RLS en la instancia de Supabase de producción mediante `deploy/supabase_rls_policies.sql`.
   - Ajustar variables de entorno de producción en Render (`DATABASE_URL`, `SECRET_KEY`, `CORS_ORIGINS`, `ADMIN_PIN`).
2. **Telemetría y Métricas de Uso**:
   - Conectar PostHog en el frontend para análisis de funnels de conversión en el onboarding de OIA.
3. **Campaña de Lanzamiento Piloto**:
   - Embarcar a los primeros 10 negocios de prueba en el modelo de suscripción Billing de Stripe.
4. **Suprimir warning httpx2 en tests**:
   - Actualizar `httpx` → `httpx2` o añadir el filtro a `pytest.ini` para silenciar el `StarletteDeprecationWarning`.
