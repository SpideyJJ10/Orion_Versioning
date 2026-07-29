# 00-alcance.md — Alcance y Límites de Orion v1

> **Visión General**: Orion es una plataforma SaaS B2B adaptable e inteligente de gestión operativa y punto de venta para microempresas gastronómicas y comerciales colombianas (restaurantes, asaderos, barberías, retail).

---

## 1. Problema #1 que Resuelve

**Pérdida incontrolada de dinero y descuadres de caja por falta de sincronización operativa.**

En las microempresas gastronómicas y comerciales tradicionales:
- Se pierde hasta un 15% de ingresos por ventas no registradas o errores de meseros/cajeros.
- Existe fuga de inventario por falta de auditoría atómica entre la venta y el stock.
- Los cierres de jornada toman horas y generan fricciones operativas diarias entre dueños y empleados.

Orion resuelve este problema garantizando que **toda transacción quede registrada atómicamente, descuente inventario en tiempo real (online u offline) y genere cierres de caja transparentes sin fricción**.

---

## 2. Qué NO Hace la v1 (Lista Explícita)

Para mantener el foco en la agilidad operativa y evitar la sobre-ingeniería en la v1:

1. **NO realiza cobro con tarjeta física directamente embebido en POS**:
   - v1 gestiona cobros en Efectivo, Nequi, Daviplata, Transferencia o pagos de suscripción SaaS vía Stripe Checkout. No integra datáfonos físicos (POS hardware) por API en v1.
2. **NO es un ERP contable complejo de gran corporación**:
   - No maneja nómina electrónica, liquidación de prestaciones ni contabilidad NIIF completa. Se enfoca exclusivamente en la operación comercial, ventas, caja e inventario.
3. **NO emite facturación electrónica DIAN directa sin proveedor externo**:
   - La v1 incluye el modelo de datos y el adaptador de servicios (`dian.py`), pero opera por defecto en modo documento equivalente / tirilla POS sin transmitir facturas electrónicas a la DIAN hasta activar un proveedor certificado.
4. **NO maneja multi-moneda en la misma transacción**:
   - Se opera en la moneda nativa configurada por el negocio (por defecto COP - Peso Colombiano).
5. **NO ejecuta modelos de Machine Learning pesados en el dispositivo cliente**:
   - El PWA cliente opera de forma ligera y offline; las predicciones de demanda y forecasting por ML se calculan en el servidor o workers en segundo plano.

---

## 3. Criterio de "Terminado" (Definition of Done v1)

La versión v1 de Orion se considera **lista para el mercado** cuando cumple estrictamente con los siguientes criterios:

- [x] **Onboarding Autónomo < 2 min**: Un dueño de negocio puede registrarse vía el asistente conversacional (Orion IA) o formulario y tener su tienda lista con categorías y mesas generadas.
- [x] **PWA Offline-First Funcional**: El POS puede realizar ventas, consultar productos/categorías y guardar órdenes en cola local (IndexedDB / Dexie) sin conexión a internet, sincronizando automáticamente al reconectarse.
- [x] **Gestión de Mesas y Comandas en Tiempo Real**: Cambio de estado de mesas (libre, ocupada, cuenta pedida) y registro de pedidos por mesero sin caídas de sesión.
- [x] **Control Atómico de Inventario y Cierre de Caja**: Descuento de stock en tiempo real con ledger de auditoría (`movimientos_inventario`) y generación de reporte de cierre de caja (`cierre_caja`).
- [x] **Seguridad y Aislamiento Multi-tenant**: 100% de aislamiento de datos por `tenant_id` tanto en la capa de API (FastAPI) como en base de datos PostgreSQL (Row Level Security).
- [x] **Pruebas Automatizadas 100% Verificadas**: Suite de backend con 100/100 tests pasando sin errores en `pytest`.
