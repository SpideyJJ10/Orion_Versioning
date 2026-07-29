# 05-decisiones.md — Registro de Decisiones de Arquitectura (ADRs)

Este documento registra las decisiones técnicas clave tomadas durante el desarrollo de Orion, explicando el contexto, las alternativas consideradas y la justificación de cada elección para evitar discusiones repetitivas en el futuro.

---

## ADR-001: Separación de Arquitectura en FastAPI (Backend) y Next.js 14 (Frontend PWA)

- **Fecha**: Abril 2026
- **Estado**: Aprobado e Implementado
- **Contexto**: Se necesitaba un frontend extremadamente rápido e instalable en cualquier dispositivo (celular, tablet, PC) y una API asíncrona robusta.
- **Decisión**: Usar FastAPI (Python 3.11+) para la API REST y Next.js 14 (React 18 + App Router) para la PWA web.
- **Justificación**: FastAPI ofrece tipado estricto con Pydantic, excelente rendimiento asíncrono y facilidades para integrar módulos de IA/ML en Python. Next.js 14 permite empaquetar un PWA standalone con instalabilidad nativa y renderizado ultrarrápido.

---

## ADR-002: Multi-Tenancy Nivel Fila (`tenant_id`) con Supabase Postgres RLS

- **Fecha**: Mayo 2026
- **Estado**: Aprobado e Implementado
- **Contexto**: Se requería aislar datos entre cientos de negocios sin la complejidad de crear esquemas o bases de datos PostgreSQL separadas por cliente.
- **Decisión**: Mantener una base de datos relacional única donde todas las tablas operativas contienen una columna `tenant_id` indexada, complementado con *Row Level Security* (RLS) en Postgres.
- **Justificación**: Maximiza la eficiencia de recursos, simplifica las migraciones con Alembic y garantiza que ni un fallo en el código de la aplicación pueda filtrar datos entre clientes gracias a la validación en el motor SQL.

---

## ADR-003: Motor Offline-First con Dexie.js (IndexedDB) + React Query

- **Fecha**: Junio 2026
- **Estado**: Aprobado e Implementado
- **Contexto**: Las microempresas colombianas sufren micro-cortes de internet en sus locales. El sistema no puede dejar de facturar por falta de red.
- **Decisión**: Implementar Dexie.js para manejar una IndexedDB local (`Orion_OfflineDB`) en el navegador, sincronizada vía un `SyncManager` y desacoplada con TanStack React Query.
- **Justificación**: Cuando falla la conexión, la app no muestra pantallas de error; lee el catálogo de productos/categorías desde IndexedDB y guarda las órdenes en una cola local que se despacha automáticamente al restaurar internet.

---

## ADR-004: Sistema de Autenticación JWT v3 con PIN Numérico Rápido

- **Fecha**: Mayo 2026
- **Estado**: Aprobado e Implementado
- **Contexto**: Los cajeros y meseros comparten tablets en el local y no pueden digitar correos y contraseñas complejas en cada venta.
- **Decisión**: Implementar tokens JWT duales (Access Token + Refresh Token) combinados con un endpoint `/api/v3/auth/login-pin` que valida un PIN numérico de 4 a 6 dígitos vinculado al `tenant_id`.
- **Justificación**: Proporciona agilidad operativa en punto de venta (1 segundo para cambiar de cajero) manteniendo la seguridad y auditoría individual de quién realizó cada venta.

---

## ADR-005: Soporte Dual LLM: OpenAI Cloud / LM Studio Local

- **Fecha**: Julio 2026
- **Estado**: Aprobado e Implementado
- **Contexto**: Para el asistente conversacional Orion IA (OIA) y el chat contextual, era necesario permitir pruebas y operación local sin depender obligatoriamente de claves pagadas de OpenAI en desarrollo.
- **Decisión**: Diseñar los clientes LLM (`oai.py` y `nlp_assistant.py`) para detectar `OPENAI_BASE_URL` o `LM_STUDIO_URL` (`http://localhost:1234/v1`). Si no hay API Key de OpenAI, se conecta automáticamente a LM Studio local con tolerancia a bloques markdown JSON.
- **Justificación**: Permite a los desarrolladores y usuarios avanzados ejecutar modelos de lenguaje locales (ej. Qwen, Llama, Mistral) de forma gratuita y privada, manteniendo total compatibilidad con OpenAI GPT-4o-mini en producción.

---

## ADR-006: Modelo de Suscripción Fija con Stripe Billing (Sin Stripe Connect)

- **Fecha**: Junio 2026
- **Estado**: Aprobado e Implementado
- **Contexto**: Se evaluó si procesar los pagos de tarjeta de los clientes finales reteniendo una comisión por transacción (Stripe Connect Express) o cobrar una suscripción SaaS mensual fija.
- **Decisión**: Mantener la facturación SaaS por suscripción fija mensual (Stripe Billing Checkout) sin procesar cobros de terceros.
- **Justificación**: El mercado objetivo (microempresas en Colombia) prefiere cobrar en efectivo/Nequi sin pagar comisiones bancarias del 2-3% por venta. Una suscripción fija de $29/mes ofrece previsibilidad financiera al cliente y simplifica la estructura legal y administrativa de Orion.
