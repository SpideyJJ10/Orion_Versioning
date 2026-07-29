#!/usr/bin/env bash
# ──────────────────────────────────────────────────────────────────────
# Orion POS — post-deploy smoke test
# ──────────────────────────────────────────────────────────────────────
# Ejecutado por:
#   - .github/workflows/deploy-production.yml (después del deploy)
#   - .github/workflows/deploy-staging.yml    (idem)
#   - manualmente:    bash scripts/smoke_test.sh
#
# Variables requeridas (env o args):
#   API_URL          base del backend (sin slash final)
#   SMOKE_EMAIL      email de un usuario de prueba (idealmente "smoke@…")
#   SMOKE_PASSWORD   contraseña del usuario de prueba
#
# Se considera el deploy sano si todas las verificaciones pasan.
# Cualquier fallo retorna exit code != 0 → el workflow falla y se notifica.
# ──────────────────────────────────────────────────────────────────────

set -euo pipefail

API_URL="${API_URL:-${1:-}}"
SMOKE_EMAIL="${SMOKE_EMAIL:-}"
SMOKE_PASSWORD="${SMOKE_PASSWORD:-}"

if [[ -z "$API_URL" ]]; then
  echo "❌ API_URL is required (env or first arg)" >&2
  exit 2
fi

API_URL="${API_URL%/}"   # strip trailing slash

echo "▶ Smoke testing $API_URL"

# 1) Health check — debe ser 200 con ok=true
echo -n "  · /api/health … "
HEALTH_BODY="$(curl -fsSL --max-time 10 "$API_URL/api/health")"
if echo "$HEALTH_BODY" | grep -q '"ok":true'; then
  echo "✓"
else
  echo "✗"
  echo "$HEALTH_BODY" >&2
  exit 1
fi

# 2) OpenAPI — debe responder 200 (verifica que la app arrancó)
echo -n "  · /openapi.json … "
curl -fsSL --max-time 10 "$API_URL/openapi.json" > /dev/null
echo "✓"

# 3) Login + /me (opcional — solo si hay credenciales)
if [[ -n "$SMOKE_EMAIL" && -n "$SMOKE_PASSWORD" ]]; then
  echo -n "  · POST /api/v3/auth/login … "
  LOGIN_RESP="$(curl -fsSL --max-time 10 -X POST "$API_URL/api/v3/auth/login" \
    -H "Content-Type: application/json" \
    -d "{\"email\":\"$SMOKE_EMAIL\",\"password\":\"$SMOKE_PASSWORD\"}")"
  TOKEN="$(echo "$LOGIN_RESP" | python3 -c "import json,sys; print(json.load(sys.stdin)['access_token'])")"
  if [[ -z "$TOKEN" ]]; then
    echo "✗ no token returned"
    exit 1
  fi
  echo "✓"

  echo -n "  · GET /api/v3/auth/me … "
  curl -fsSL --max-time 10 "$API_URL/api/v3/auth/me" \
    -H "Authorization: Bearer $TOKEN" > /dev/null
  echo "✓"
else
  echo "  · auth flow skipped (SMOKE_EMAIL/SMOKE_PASSWORD not set)"
fi

echo "✅ Smoke test passed"
