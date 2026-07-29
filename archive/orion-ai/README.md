# Orion POS v3

> White-label, multi-tenant point-of-sale for restaurants and retail.
> FastAPI backend on Render · Next.js 14 frontend on Vercel · PostgreSQL · ML alerts.

[![CI](https://github.com/oriontech-JG/Tizon_MVP_Version_2/actions/workflows/ci.yml/badge.svg)](https://github.com/oriontech-JG/Tizon_MVP_Version_2/actions/workflows/ci.yml)
[![Deploy Production](https://github.com/oriontech-JG/Tizon_MVP_Version_2/actions/workflows/deploy-production.yml/badge.svg)](https://github.com/oriontech-JG/Tizon_MVP_Version_2/actions/workflows/deploy-production.yml)
![Python 3.11](https://img.shields.io/badge/python-3.11-blue)
![Node 20](https://img.shields.io/badge/node-20-green)
![License](https://img.shields.io/badge/license-Proprietary-red)

---

## ✦ At a glance

- **Multi-tenant** isolation enforced at every query (`tenant_id` filter mandatory).
- **Roles**: `owner`, `manager`, `cashier`, `inventory`, `super_admin`.
- **Branding** per tenant — logo, color, niche, theme, live preview editor.
- **Multi-branch** inventory and sales.
- **JWT** with refresh-token rotation + reuse detection.
- **POS Pro** UI: categories, discounts, mixed payments, receipt print (`@media print`), stock validation, keyboard shortcuts.
- **Reports**: line/bar/pie charts, top products, payment-method breakdown, cashier close, CSV export.
- **ML** baseline forecast + Prophet (optional) + alert engine, with admin UI to train, review and act on alerts.
- **AI extras** (opt-in): stockout forecast, invoice OCR, NLP assistant.
- **Onboarding wizard** for new tenants (profile → first product → first sale).
- **Production-ready**: Sentry, BetterStack uptime, daily Postgres backups, smoke tests post-deploy, full runbooks.

The detailed reference for everything below is **[`docs/MASTER_GUIDE.md`](docs/MASTER_GUIDE.md)**.

---

## ✦ Quickstart (5 commands)

```powershell
git clone https://github.com/oriontech-JG/Tizon_MVP_Version_2.git
cd Tizon_MVP_Version_2

py -3 -m venv .venv && .\.venv\Scripts\Activate.ps1
pip install -r requirements.txt
copy .env.example .env       # then edit SECRET_KEY, ADMIN_*

alembic upgrade head
uvicorn backend.main:app --reload --reload-dir backend --port 8000
```

In another terminal:

```powershell
cd web
npm install
npm run dev
# → http://localhost:3000
```

Smoke test:

```powershell
curl http://localhost:8000/api/health
pytest -q
```

---

## ✦ Repository layout

```
backend/        FastAPI app (auth_v3, ai/, ml/, routes/, schemas/, models/, core/sentry.py)
web/            Next.js 14 + Tailwind + shadcn/ui + TanStack Query + Zustand
  ├─ src/components/{onboarding,usuarios,productos,brand,…}
  └─ sentry.{client,server,edge}.config.ts
tests/          pytest suite (92 integration tests)
migrations/     Alembic
scripts/        seed_demo, train_models, smoke_test.sh
docs/           MASTER_GUIDE.md · DEPLOYMENT.md · runbooks/ · adr/ · es/
infra/          render.yaml — Render Blueprint (backend + Postgres)
.github/
  └─ workflows/ ci.yml · deploy-staging.yml · deploy-production.yml
```

Full breakdown in [`docs/MASTER_GUIDE.md §4`](docs/MASTER_GUIDE.md#4-repository-layout).

---

## ✦ Documentation map

| What you want to know | Where |
|---|---|
| **Deploy your own instance (one-pager)** | [`docs/DEPLOYMENT.md`](docs/DEPLOYMENT.md) |
| Architecture diagrams, design decisions | [MASTER_GUIDE §2-3](docs/MASTER_GUIDE.md#2-system-overview--architecture) |
| Local dev | [§5](docs/MASTER_GUIDE.md#5-local-development) |
| Production deployment (Vercel + Render) | [§6](docs/MASTER_GUIDE.md#6-production-deployment) |
| Tests + coverage thresholds | [§7](docs/MASTER_GUIDE.md#7-testing-protocol) |
| OWASP Top 10 status, rate limit, JWT rotation | [§8](docs/MASTER_GUIDE.md#8-security-hardening) |
| AI modules (forecast, OCR, NLP) | [§9](docs/MASTER_GUIDE.md#9-ai-modules-lightweight) |
| ML production module (baseline, Prophet, alerts) | [§10](docs/MASTER_GUIDE.md#10-ml-module-production) |
| Market benchmark + 6-month roadmap | [§11](docs/MASTER_GUIDE.md#11-market-benchmark) |
| Git workflow + branch protection | [§12](docs/MASTER_GUIDE.md#12-git-workflow--branching) and [`CONTRIBUTING.md`](CONTRIBUTING.md) |
| Day-2 ops (rollback, backups, incidents, secrets, uptime) | [`docs/runbooks/`](docs/runbooks/) |
| Spanish-language references | [`docs/es/`](docs/es/) |
| ADRs | [`docs/adr/`](docs/adr/) |

---

## ✦ Deploy your own

One-line summary: **frontend on Vercel, backend on Render, ~$15/month**.

[![Deploy to Render](https://render.com/images/deploy-to-render-button.svg)](https://render.com/deploy?repo=https://github.com/oriontech-JG/Tizon_MVP_Version_2)
[![Deploy to Vercel](https://vercel.com/button)](https://vercel.com/new/clone?repository-url=https%3A%2F%2Fgithub.com%2Foriontech-JG%2FTizon_MVP_Version_2&root-directory=web)

Full step-by-step in **[`docs/DEPLOYMENT.md`](docs/DEPLOYMENT.md)**.

---

## ✦ Key URLs

- App (production): https://orion-pos.vercel.app
- API (production): https://orion-pos.onrender.com
- API health: https://orion-pos.onrender.com/api/health
- API OpenAPI docs: https://orion-pos.onrender.com/docs
- Repo: https://github.com/oriontech-JG/Tizon_MVP_Version_2

---

## ✦ Contributing

See [`CONTRIBUTING.md`](CONTRIBUTING.md). TL;DR: branch off `develop`, follow Conventional Commits, keep PRs small, update `CHANGELOG.md` for user-facing changes.

---

## ✦ License

Proprietary © **OrionTech**. All rights reserved. See [`LICENSE`](LICENSE).
