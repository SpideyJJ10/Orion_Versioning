# Orion POS — CHANGELOG

Todos los cambios notables en este proyecto se documentan aquí.
Formato: [Keep a Changelog](https://keepachangelog.com/es/1.1.0/) · Versionado: [Semantic Versioning](https://semver.org/lang/es/).

---

## [Unreleased]

### Añadido — Deployment & Operations

#### Topología híbrida Vercel + Render
- **Frontend en Vercel** con preview deploys automáticos por PR, CDN global y CI integrado.
  - `web/vercel.json`: headers de seguridad (HSTS, X-Frame-Options, Permissions-Policy), caching inmutable para `_next/static`.
  - `web/.env.example` actualizado con `NEXT_PUBLIC_API_URL` por entorno y variables Sentry.
- **Backend en Render** con migraciones automáticas pre-deploy.
  - `infra/render.yaml` define `orion-pos-staging` (free) + `orion-postgres-staging` con `preDeployCommand: alembic upgrade head`.
  - Producción (`orion-pos`) sigue bajo control manual.

#### Observabilidad
- **Sentry backend** (`backend/core/sentry.py`): inicialización opt-in vía `SENTRY_DSN`, integración FastAPI + Starlette, soporte para `release` y sample rates configurables.
- **Sentry frontend**: `sentry.{client,server,edge}.config.ts` + `withSentryConfig` wrapper en `next.config.mjs` (defensive import — no-op si la dependencia no está).
- `requirements.txt` añade `sentry-sdk[fastapi]>=2.0`.
- `web/package.json` añade `@sentry/nextjs@^8.40`.
- **BetterStack uptime**: documentación completa en `docs/runbooks/uptime.md` con config de monitor y escalation policy.

#### Healthcheck enriquecido
- `/api/health` ahora devuelve `{ok, status, service, version, env, db, ts}` y retorna `503` si Postgres no responde.
- Compatible con `healthCheckPath` de Render, monitores BetterStack y el smoke test.

#### CORS dinámico para Vercel
- Nueva variable `CORS_ORIGIN_REGEX` en `backend/core/config.py` que permite previews Vercel sin reconfigurar manualmente.
- Ejemplo: `^https://orion-pos-.*\.vercel\.app$`.

#### CI/CD
- **`.github/workflows/ci.yml` reforzado**: `bandit` bloqueante (`-ll -iii`), `lint` bloqueante, nuevo job `alembic-check` (upgrade head + check), `build-check` añadido al frontend.
- **Nuevo `.github/workflows/deploy-production.yml`**: hook Render → wait-for-health (6 min max) → `smoke_test.sh` → Sentry release tracking → step summary.
- **`.github/workflows/deploy-staging.yml` modernizado**: usa el mismo smoke test post-deploy.
- **Nuevo `scripts/smoke_test.sh`**: health + openapi + login + `/me`. Reusable entre staging y prod.

#### Runbooks
Nueva carpeta `docs/runbooks/` con playbooks operacionales:
- `rollback.md` — backend (Render) y frontend (Vercel) en <5 min, manejo de migraciones rotas.
- `backups.md` — política diaria, restore drill trimestral, RTO/RPO targets.
- `incident-response.md` — SEV1/2/3, plantillas de comunicación, template de postmortem blameless.
- `secrets.md` — inventario, rotación de `SECRET_KEY` con grace period, respuesta a leaks.
- `uptime.md` — config BetterStack, alert routing, escalation, status page.
- `README.md` — índice maestro.

#### Documentación
- **Nuevo `docs/DEPLOYMENT.md`**: one-pager de fork → deploy en ~25 min, con tabla de variables, troubleshooting y estimación de costos (~$15/mes).
- **`docs/MASTER_GUIDE.md §6` reescrito**: nueva arquitectura híbrida, env vars, pipeline CI/CD, observabilidad, links a runbooks.
- **`README.md`**: badges de Deploy Production, sección "Deploy your own" con botones de Render + Vercel, layout actualizado, Key URLs corregidas.
- **`.env.example`**: documentación de `CORS_ORIGIN_REGEX` y variables Sentry.

### Cambiado
- `backend/main.py`: `APP_VERSION` ahora es constante (3.1.0), `init_sentry()` se llama antes de crear la `FastAPI` instance, CORS middleware acepta `allow_origin_regex`.
- `infra/render.yaml`: removidas las secciones `orion-web` y `orion-web-staging` (ahora viven en Vercel).

---

## [3.1.0] — 2026-05-10

### Añadido — Frontend

#### Páginas completamente implementadas
- **`/ml` — Inteligencia Artificial**: Dashboard ML con 4 KPIs de estado (Prophet, modelos, alertas, RMSE), pestañas para alertas activas (con acuse de recibo), sugerencias de reabastecimiento por urgencia y pronóstico de demanda por producto con gráfica AreaChart de intervalos de confianza.
- **`/usuarios` — Gestión de equipo**: Tabla CRUD completa con avatares, badges de rol coloreados, asignación de sucursal y soporte de PIN rápido. Permisos por rol (solo owner/manager pueden ver; solo owner puede crear/eliminar).
- **`/branding` — Editor de identidad**: Formulario con color pickers nativos, selector de tema (dark/light/warm), tipografía, nicho y URL de logo; preview en vivo que refleja cambios en tiempo real sin guardar.

#### Flujo de autenticación
- **`/login`**: Rediseñado en español (es-CO). Logo Orion centrado con gradiente. Tab dual: email+contraseña (con toggle de visibilidad) y PIN rápido (tenant_id + PIN numérico). Footer con copyright.
- **`/register`**: Rediseñado en español. Logo Orion visible. Labels y CTAs en español. Validación de contraseña mínimo 8 caracteres.

#### Onboarding Wizard
- Componente `<OnboardingWizard>` modal con 3 pasos (Branding → Productos → POS).
- Barra de progreso animada y estado checkmark por paso completado.
- Botón "Omitir tutorial" llama a `POST /api/v3/onboarding/skip`.
- Integrado en `<AuthGuard>`: carga el progreso en cada sesión y lo muestra si no está completo ni saltado.

#### Dashboard
- Traducido al español (es-CO) con labels, fechas y montos en COP.
- Sección **"Top productos hoy"** con rankings numerados.
- Sección **"Ingresos por método de pago"** con grid de tarjetas.
- Acciones rápidas directas a POS, Productos, Inventario y Reportes.

#### Componentes nuevos
- `web/src/components/usuarios/usuario-form-dialog.tsx` — diálogo crear/editar usuario con validación, rol, sucursal y PIN.
- `web/src/components/onboarding/wizard.tsx` — wizard modal de onboarding 3-pasos.

### Corregido

- **TypeScript 0 errores**: Limpieza de todos los imports sin usar (`X`, `useRef`, `LineChart`, `Line`, `useBrandingQuery`, `useAuthStore`, `useSucursales`, `CardDescription`, `CardHeader`, `CardTitle`, índice `index` no usado).
- **`usuario-form-dialog.tsx`**: Tipo `Omit<CrearUsuarioRequest, "password"> & { password?: string }` para permitir edición sin password.
- **`test_health.py`**: Removido prefijo `/api/auth` obsoleto (v1/v2); todas las rutas de auth ahora son `/api/v3/auth/*`.

### Tests
- **92/92 tests pasando** — suite completa: admin, auth_v3, branding, health, inventario, ml, onboarding, ordenes_stock, productos_stock, reportes, usuarios.

---

## [3.0.0] — 2025-05-09

### Añadido

#### Backend
- Migración a Float en campos `cantidad` de `OrdenItem`, `MovimientoInventario` y `Producto.stock` / `stock_minimo` para soporte de cantidades decimales (kg, lt, gr, ml).
- Nuevos modelos ORM: `TenantBranding`, `OnboardingProgress`, `Usuario`, `Sucursal`, `MlForecast`, `MlAlerta`.
- Routers completos: `auth_v3`, `usuarios`, `branding`, `onboarding`, `sucursales`, `productos`, `categorias`, `ventas`, `ordenes`, `reportes`, `inventario`, `ml`, `admin`.
- Motor ML: baseline lineal + Prophet (opcional). Endpoints `/api/v3/ml/*`.
- Alembic migrations: `0004_decimal_quantities`, `0005_producto_meta`.
- Backfill automático en startup (`_backfill_tenants_v3`).

#### Frontend
- Stack: Next.js 14 App Router, Tailwind CSS, Zustand, TanStack Query, Recharts.
- Tema dinámico: `prefers-color-scheme` con toggle persistido en localStorage.
- Sidebar con RBAC, topbar con alertas ML en tiempo real.
- POS: catálogo filtrado, carrito con validación de stock, checkout multi-pago, receipt dialog con impresión térmica 80mm.
- Inventario: KPIs, alertas de stock bajo, bitácora de movimientos con cantidades decimales.
- Reportes: gráfica de líneas (ventas/día), pie de métodos de pago, top productos, cierre de caja.
- Productos: tabla CRUD + `ProductoFormDialog` + `AjusteStockDialog` (entradas/salidas decimales).

---

## [2.0.0] — 2025-04-20 (MVP)

- Base del sistema: Login/Register, dashboard básico, productos, POS simplificado.
- SQLite local como base de datos de desarrollo.
