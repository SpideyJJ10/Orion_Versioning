# 01-arquitectura.md — Arquitectura de Orion

## 1. Diagrama del Stack Tecnológico

```
┌─────────────────────────────────────────────────────────────────────────┐
│                           CLIENTES (Navegador / PWA)                   │
│  React 18 · Next.js 14 (App Router) · Tailwind CSS · Dexie (IndexedDB)  │
└────────────────────────────────────┬────────────────────────────────────┘
                                     │  HTTPS / REST API (JSON) + JWT
                                     ▼
┌─────────────────────────────────────────────────────────────────────────┐
│                      BACKEND API CORE (FastAPI / Render)                │
│  Python 3.11+ · Pydantic v2 · SQLAlchemy 2.0 ORM · JWT Auth v3 (Jose)   │
│  - Middleware: CORS, GZip, Rate Limiting (slowapi), Sentry Observability│
└──────┬─────────────────────────────┬─────────────────────────────┬──────┘
       │                             │                             │
       │ SQLAlchemy                  │ HTTP / OpenAI SDK           │ REST
       ▼                             ▼                             ▼
┌──────────────┐             ┌──────────────┐              ┌──────────────┐
│  DATABASE    │             │  AI / LLM    │              │   PAGOS      │
│  PostgreSQL  │             │  OpenAI /    │              │   Stripe     │
│  (Supabase / │             │  LM Studio   │              │  Billing     │
│  SQLite dev) │             │  Local       │              │  Webhooks    │
└──────────────┘             └──────────────┘              └──────────────┘
```

---

## 2. Componentes Principales y Conexiones

### 2.1. Frontend Web App (`apps/web-app`)
- **Framework**: Next.js 14 (App Router) + React 18 + TypeScript.
- **Estilos y UI**: Tailwind CSS + Radix UI / shadcn/ui + Framer Motion.
- **Gestión de Estado**: Zustand (Store de Auth `useAuthStore`, Store de Branding `useBrandingStore`).
- **Data Fetching y Caché**: TanStack React Query v5 + Cliente Axios/Fetch centralizado con interceptor de auto-refresh de JWT token.
- **Capa Offline-First**: Dexie.js (IndexedDB `Orion_OfflineDB`) que almacena productos, categorías, sucursales y encola órdenes en la tabla `offlineOrders` con reconexión automática mediante `SyncManager`.
- **Despliegue**: Vercel.

### 2.2. Backend API Core (`apps/api-core`)
- **Framework**: FastAPI (Python 3.11+) asíncrono con servidor ASGI Uvicorn.
- **Autenticación y Seguridad**: JWT dual v3 (Access Token de 8h + Refresh Token persistente) + PIN rápido de 4-6 dígitos para cajeros + hashing de contraseñas bcrypt.
- **ORM y Persistencia**: SQLAlchemy 2.0 con motor de sesiones asíncrono/sincrónico de alto rendimiento.
- **AI Modules**:
  - `backend/routes/oai.py`: Engine conversacional y aprovisionamiento automático de negocios.
  - `backend/ai/nlp_assistant.py`: Asistente de lenguaje natural para consultas operativas (OpenAI GPT-4o-mini o LM Studio local `http://localhost:1234/v1`).
  - `backend/ml/`: Algoritmos de predicción de demanda (Baseline Media Móvil / Prophet) y generación de alertas inteligentes de sobrestock/stockout.
- **Despliegue**: Render Web Service.

### 2.3. Base de Datos (`PostgreSQL` / `SQLite`)
- **Desarrollo**: SQLite 3 (`tizon.db`).
- **Producción**: PostgreSQL en Supabase con Row Level Security (RLS) activo vía el script `deploy/supabase_rls_policies.sql`.
- **Aislamiento Multi-tenant**: Todas las consultas filtran obligatoriamente por `tenant_id`.

---

## 3. Dónde Vive Cada Cosa (Estructura del Proyecto)

```
OrionV2/
├── apps/
│   ├── api-core/               # Backend FastAPI
│   │   ├── backend/
│   │   │   ├── ai/             # Módulos de IA (NLP, OCR, Stockout)
│   │   │   ├── auth_v3/        # Autenticación JWT y contraseñas
│   │   │   ├── core/           # Configuración, logger, seguridad
│   │   │   ├── db/             # Conexión SQLAlchemy y sesiones
│   │   │   ├── ml/             # Motor de forecasting y alertas
│   │   │   ├── models/         # Modelos SQLAlchemy (orm.py)
│   │   │   ├── routes/         # Endpoints FastAPI por módulo
│   │   │   └── schemas/        # Esquemas Pydantic v2 (api.py)
│   │   ├── tests/              # Suite de pruebas Pytest (100 tests)
│   │   └── requirements.txt
│   ├── web-app/                # Frontend Next.js PWA
│   │   ├── src/
│   │   │   ├── app/            # App Router (pages, dashboard, oai, login)
│   │   │   ├── components/     # Componentes UI (shadcn, brand, layout)
│   │   │   ├── lib/            # Cliente API, Dexie DB, SyncManager, Hooks
│   │   └── package.json
│   └── landing/                # Sitio web comercial e informativo
├── deploy/                     # Manifests de infraestructura, Docker, RLS SQL
└── docs/                       # Documentación técnica v1
```
