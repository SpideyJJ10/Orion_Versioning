# Contributing to Orion POS

Thanks for taking the time to contribute. This document is the source of truth for **branching**, **commit style**, **PR workflow** and **release rules**. The architectural reference is [`docs/MASTER_GUIDE.md`](docs/MASTER_GUIDE.md).

---

## 1. Branch model — GitFlow simplified

```
main      protected, prod-deployed via Render on every merge
   ▲
develop   staging, auto-deployed via Render on every push
   ▲
feat/*    new user-visible capability
fix/*     bug fix
chore/*   tooling / deps / infra
refactor/*no behaviour change
docs/*    documentation only
test/*    only tests
```

**Rules of thumb:**

- Open a PR to `develop`, never to `main` directly.
- Keep branches short-lived (≤ 1 week). Long-lived branches are a smell.
- Squash-merge when in doubt; preserve history when the commits tell a story.
- Tag each `main` merge with a semver tag: `git tag -a v3.x.y -m "…"`.

---

## 2. Commit style — Conventional Commits

```
<type>(<scope>): <imperative summary>

[optional body — what and why, not how]

[optional footer — Closes #, Refs #, BREAKING CHANGE: …]
```

Types: `feat`, `fix`, `chore`, `refactor`, `docs`, `test`, `perf`, `style`, `build`, `ci`.

**Examples:**

```
feat(ml): add restock suggestion endpoint
fix(auth): lowercase email on login
chore(deps): bump fastapi 0.100 → 0.115
docs: link MASTER_GUIDE from README
refactor(routes): drop auth v2 imports
test(ordenes): cover stock-restore on cancel
```

`BREAKING CHANGE:` in the footer triggers a major version bump.

---

## 3. Pull-request checklist

The PR template (`.github/PULL_REQUEST_TEMPLATE.md`) is auto-applied. Every box must be ticked before merge:

- [ ] Tests added or updated and passing locally (`pytest -q` and/or `npm run typecheck`).
- [ ] Multi-tenant isolation considered (queries include `tenant_id`).
- [ ] No secrets, JWT or PII committed.
- [ ] DB migration is **idempotent and additive** (or none).
- [ ] `docs/MASTER_GUIDE.md` and/or `CHANGELOG.md` updated for user-facing changes.
- [ ] `.env.example` updated if new env vars introduced.

---

## 4. Branch protection rules (apply manually in GitHub Settings → Branches)

### `main`

- ✅ Require pull request before merging
- ✅ Require approvals: **1**
- ✅ Require status checks to pass: `CI / backend`, `CI / frontend`
- ✅ Require branches to be up to date before merging
- ✅ Require conversation resolution before merging
- ✅ Restrict who can push: **CODEOWNERS only**
- ❌ Allow force pushes
- ❌ Allow deletions

### `develop`

- ✅ Require status checks to pass: `CI / backend`, `CI / frontend`
- ✅ Require linear history (squash or rebase)
- ❌ Allow force pushes

These rules are enforced manually until [terraform/automation arrives — see ADR-008 (TBD)].

---

## 5. Release process

```
1. PR feat/* → develop          → CI green
2. Merge to develop              → Render auto-deploy to *-staging
3. QA smoke + manual checks      → see MASTER_GUIDE §7.5
4. PR develop → main             → 1 approval required
5. Merge to main                 → tag v3.x.y, push the tag
6. Render auto-deploys prod      → smoke /api/health, watch Sentry
7. Update CHANGELOG.md           → move [Unreleased] entries to v3.x.y
```

If you must hotfix prod:

1. `git switch -c fix/critical-x main`
2. PR direct to `main` with `[hotfix]` label.
3. Cherry-pick the merge commit back to `develop`.

---

## 6. Code style

### Python

- **Black** (line length 100)
- **isort** (`profile = "black"`)
- **Type hints** mandatory on public functions
- **Docstrings** in Spanish or English, but be consistent within a module
- Domain-language identifiers are OK (`crear_orden`, `verificar_sucursal`)

### TypeScript / React

- **Components** in PascalCase (`ProductCard`)
- **Hooks** prefixed with `use` (`useProductos`)
- **No `any`** without an inline justification comment
- Tailwind classes go through `cn()` from `@/lib/utils` for safe merge

---

## 7. Local environment

See [MASTER_GUIDE §5](docs/MASTER_GUIDE.md#5-local-development).

Key gotchas:

- `SECRET_KEY` must be ≥ 32 chars in prod. The app warns and auto-generates a temporary one in dev.
- `ENV=prod` activates strict CORS — the app will refuse to start with `CORS_ORIGINS=*`.
- The `tizon.db` SQLite file is gitignored on purpose; reset it with `Remove-Item tizon.db` and restart uvicorn.

---

## 8. Reporting security issues

**Do not open a public issue.** Email `security@orionpos.com` with a description and reproduction steps. We aim for:

- Critical vulnerabilities: < 24h initial response.
- High: < 72h.
- Medium: < 7d.

See [MASTER_GUIDE §8](docs/MASTER_GUIDE.md#8-security-hardening) for the full security model.

---

Thanks again — happy hacking 🐢.
