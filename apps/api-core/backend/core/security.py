"""
Capa de seguridad transversal: rate limiting, brute-force tracker, security headers,
políticas de CORS estrictas y helpers de rotación de tokens.

Diseñado para ser **opt-in**: importa `init_security(app)` desde `backend/main.py` para
activar todo. En desarrollo local puedes omitirlo y el sistema funciona igual.

Contexto: docs/SECURITY_HARDENING.md
"""
from __future__ import annotations

import os
import time
from collections import defaultdict, deque
from threading import Lock
from typing import Callable, Deque, Optional

from fastapi import FastAPI, HTTPException, Request, status
from fastapi.responses import JSONResponse
from starlette.middleware.base import BaseHTTPMiddleware

# slowapi es opcional. Si no está instalado, exponemos un limiter no-op.
try:
    from slowapi import Limiter
    from slowapi.errors import RateLimitExceeded
    from slowapi.util import get_remote_address
    SLOWAPI_OK = True
except ImportError:  # pragma: no cover
    SLOWAPI_OK = False


# ─────────────────────────────────────────────────────────────────────
# 1. Rate Limiter (slowapi)
# ─────────────────────────────────────────────────────────────────────
def _key_user_or_ip(request: Request) -> str:
    """Usa el id del usuario autenticado si existe; si no, la IP del cliente."""
    auth = request.headers.get("authorization", "")
    if auth.startswith("Bearer "):
        # Identificador opaco basado en el token (no decodificamos aquí).
        token = auth.removeprefix("Bearer ").strip()
        return f"tk:{hash(token) & 0xffffffff:x}"
    if SLOWAPI_OK:
        return get_remote_address(request)
    return request.client.host if request.client else "unknown"


# Límites por defecto, sobre-escribibles por env.
DEFAULT_LIMITS = [os.getenv("RATE_LIMIT_DEFAULT", "200/minute")]
LOGIN_LIMIT    = os.getenv("RATE_LIMIT_LOGIN",   "10/minute")
ASSISTANT_LIMIT = os.getenv("RATE_LIMIT_ASSISTANT", "100/day")

if SLOWAPI_OK:
    limiter = Limiter(key_func=_key_user_or_ip, default_limits=DEFAULT_LIMITS)
else:
    class _NoopLimiter:
        """Stub para que el código siga funcionando sin slowapi instalado."""
        def limit(self, *_args, **_kwargs):
            def deco(fn):
                return fn
            return deco
    limiter = _NoopLimiter()  # type: ignore[assignment]


# ─────────────────────────────────────────────────────────────────────
# 2. Brute-force tracker para login (in-memory + Redis ready)
# ─────────────────────────────────────────────────────────────────────
class BruteForceTracker:
    """Registra intentos fallidos y bloquea temporalmente.

    In-memory: válido para single-worker. Para multi-worker o multi-instancia
    reemplaza el storage por Redis (ver docs/SECURITY_HARDENING.md).

    Política por defecto:
        - 5 fallos en 5 minutos → bloqueo de 15 minutos
        - el contador se resetea al lograr login exitoso
    """

    def __init__(
        self,
        max_failures: int = 5,
        window_seconds: int = 300,
        lockout_seconds: int = 900,
    ) -> None:
        self.max_failures    = max_failures
        self.window_seconds  = window_seconds
        self.lockout_seconds = lockout_seconds
        self._failures: dict[str, Deque[float]] = defaultdict(deque)
        self._locked:   dict[str, float] = {}
        self._lock = Lock()

    def _purge_old(self, key: str, now: float) -> None:
        dq = self._failures[key]
        while dq and now - dq[0] > self.window_seconds:
            dq.popleft()

    def is_locked(self, key: str) -> tuple[bool, int]:
        """Retorna (bloqueado?, segundos_restantes)."""
        now = time.time()
        with self._lock:
            unlock_at = self._locked.get(key)
            if unlock_at and now < unlock_at:
                return True, int(unlock_at - now)
            if unlock_at and now >= unlock_at:
                self._locked.pop(key, None)
                self._failures[key].clear()
            return False, 0

    def record_failure(self, key: str) -> tuple[bool, int]:
        """Registra fallo. Retorna (bloqueado_ahora?, intentos_restantes)."""
        now = time.time()
        with self._lock:
            self._purge_old(key, now)
            self._failures[key].append(now)
            count = len(self._failures[key])
            if count >= self.max_failures:
                self._locked[key] = now + self.lockout_seconds
                return True, 0
            return False, self.max_failures - count

    def record_success(self, key: str) -> None:
        with self._lock:
            self._failures.pop(key, None)
            self._locked.pop(key, None)


# Singleton global
brute_force_tracker = BruteForceTracker(
    max_failures=int(os.getenv("LOGIN_MAX_FAILURES", "5")),
    window_seconds=int(os.getenv("LOGIN_WINDOW_SECONDS", "300")),
    lockout_seconds=int(os.getenv("LOGIN_LOCKOUT_SECONDS", "900")),
)


def assert_not_locked(identifier: str) -> None:
    """Helper para usar en el endpoint de login antes de validar credenciales."""
    locked, remaining = brute_force_tracker.is_locked(identifier)
    if locked:
        raise HTTPException(
            status_code=status.HTTP_429_TOO_MANY_REQUESTS,
            detail=(
                f"Demasiados intentos fallidos. Intenta de nuevo en "
                f"{remaining // 60 + 1} minutos."
            ),
            headers={"Retry-After": str(remaining)},
        )


# ─────────────────────────────────────────────────────────────────────
# 3. Security Headers Middleware
# ─────────────────────────────────────────────────────────────────────
class SecurityHeadersMiddleware(BaseHTTPMiddleware):
    """Inyecta headers de seguridad recomendados por OWASP en TODA respuesta.

    Headers:
        - Strict-Transport-Security  (HSTS, solo en prod)
        - X-Content-Type-Options
        - X-Frame-Options
        - Referrer-Policy
        - Permissions-Policy
        - Content-Security-Policy   (configurable por env CSP_POLICY)
    """

    DEFAULT_CSP = (
        "default-src 'self'; "
        "script-src 'self' 'unsafe-inline' https://cdn.jsdelivr.net https://unpkg.com; "
        "style-src 'self' 'unsafe-inline' https://fonts.googleapis.com; "
        "font-src 'self' https://fonts.gstatic.com data:; "
        "img-src 'self' data: blob: https:; "
        "connect-src 'self' https://api.openai.com; "
        "frame-ancestors 'none'; "
        "base-uri 'self'; "
        "form-action 'self'"
    )

    def __init__(self, app, csp: Optional[str] = None, hsts: bool = True) -> None:
        super().__init__(app)
        self.csp  = csp or os.getenv("CSP_POLICY", self.DEFAULT_CSP)
        self.hsts = hsts and os.getenv("ENV", "dev").lower() in {"prod", "production"}

    async def dispatch(self, request: Request, call_next: Callable):
        response = await call_next(request)
        response.headers.setdefault("X-Content-Type-Options", "nosniff")
        response.headers.setdefault("X-Frame-Options", "DENY")
        response.headers.setdefault("Referrer-Policy", "strict-origin-when-cross-origin")
        response.headers.setdefault(
            "Permissions-Policy",
            "camera=(), microphone=(), geolocation=(), interest-cohort=()",
        )
        response.headers.setdefault("Content-Security-Policy", self.csp)
        if self.hsts:
            response.headers.setdefault(
                "Strict-Transport-Security",
                "max-age=63072000; includeSubDomains; preload",
            )
        return response


# ─────────────────────────────────────────────────────────────────────
# 4. JWT Refresh Reuse Detection (anti-replay)
# ─────────────────────────────────────────────────────────────────────
class RefreshTokenRegistry:
    """Detecta reuso de refresh tokens (token theft detection).

    Almacena el JTI o hash del refresh token emitido por usuario. Cuando se usa
    para renovar, debe ser el último emitido; si se intenta usar uno antiguo,
    asumimos compromiso y revocamos toda la familia (forzamos logout).

    In-memory para single-worker. Para multi-worker, mover a tabla SQL o Redis.
    """

    def __init__(self) -> None:
        self._activos: dict[int, str] = {}      # usuario_id → jti vigente
        self._revocados: set[int] = set()       # usuarios forzados a re-login
        self._lock = Lock()

    def emitir(self, usuario_id: int, jti: str) -> None:
        with self._lock:
            self._activos[usuario_id] = jti
            self._revocados.discard(usuario_id)

    def consumir(self, usuario_id: int, jti: str) -> bool:
        """Retorna True si el jti es el vigente; False si hay reuso o revocado.

        En caso de reuso (False), también marca al usuario como revocado.
        """
        with self._lock:
            if usuario_id in self._revocados:
                return False
            vigente = self._activos.get(usuario_id)
            if vigente != jti:
                # ¡Token theft! revocamos toda la familia.
                self._revocados.add(usuario_id)
                self._activos.pop(usuario_id, None)
                return False
            return True

    def revocar(self, usuario_id: int) -> None:
        with self._lock:
            self._revocados.add(usuario_id)
            self._activos.pop(usuario_id, None)


refresh_registry = RefreshTokenRegistry()


# ─────────────────────────────────────────────────────────────────────
# 5. CORS estricto helper
# ─────────────────────────────────────────────────────────────────────
def strict_cors_origins() -> list[str]:
    """Lee CORS_ORIGINS del entorno. NO permite '*' en producción.

    Si ENV=prod y CORS_ORIGINS está vacío o '*', lanza error de configuración.
    """
    raw = os.getenv("CORS_ORIGINS", "").strip()
    env = os.getenv("ENV", "dev").lower()
    if env in {"prod", "production"}:
        if not raw or raw == "*":
            raise RuntimeError(
                "CORS_ORIGINS no puede ser '*' ni vacío en producción. "
                "Define una lista explícita en .env, ej.: "
                "CORS_ORIGINS=https://app.orionpos.com,https://orion-pos.onrender.com"
            )
    if not raw or raw == "*":
        return ["*"]   # solo dev
    return [o.strip().rstrip("/") for o in raw.split(",") if o.strip()]


# ─────────────────────────────────────────────────────────────────────
# 6. Bootstrap: init_security(app)
# ─────────────────────────────────────────────────────────────────────
def init_security(app: FastAPI) -> None:
    """Activa middlewares y handlers de seguridad. Llamar desde main.py.

    Uso:
        from backend.core.security import init_security
        init_security(app)
    """
    # Headers
    app.add_middleware(SecurityHeadersMiddleware)

    # Rate limit handler
    if SLOWAPI_OK:
        app.state.limiter = limiter

        @app.exception_handler(RateLimitExceeded)
        async def _rate_limit_handler(request: Request, exc: RateLimitExceeded):
            return JSONResponse(
                status_code=status.HTTP_429_TOO_MANY_REQUESTS,
                content={
                    "detail": f"Demasiadas solicitudes. Límite: {exc.detail}",
                    "tipo":   "rate_limit_exceeded",
                },
                headers={"Retry-After": "60"},
            )
