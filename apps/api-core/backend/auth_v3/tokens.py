"""
tokens.py — Emisión y validación de JWT (access + refresh).
"""
import uuid
from datetime import datetime, timedelta, timezone
from typing import Optional

from fastapi import Depends, HTTPException, status
from fastapi.security import HTTPAuthorizationCredentials, HTTPBearer
from jose import JWTError, jwt

from backend.core.config import SECRET_KEY
from backend.core.security import refresh_registry

ALGORITHM              = "HS256"
ACCESS_TOKEN_MINUTES   = 60 * 8    # 8 horas (jornada laboral)
REFRESH_TOKEN_DAYS     = 30

bearer_scheme = HTTPBearer(auto_error=False)


# ── Emisión ──────────────────────────────────────────────────────────────
def crear_access_token(
    *,
    usuario_id:   int,
    tenant_id:    int,
    rol:          str,
    email:        str,
    sucursal_id:  Optional[str] = None,
) -> str:
    """JWT de corta duración con todos los claims necesarios para autorización."""
    payload = {
        "sub":         str(usuario_id),
        "tenant_id":   tenant_id,
        "rol":         rol,
        "email":       email,
        "sucursal_id": sucursal_id,
        "type":        "access",
        "exp":         datetime.now(timezone.utc) + timedelta(minutes=ACCESS_TOKEN_MINUTES),
        "iat":         datetime.now(timezone.utc),
    }
    return jwt.encode(payload, SECRET_KEY, algorithm=ALGORITHM)


def crear_refresh_token(*, usuario_id: int) -> str:
    """JWT de larga duración para renovar access tokens sin volver a loguear."""
    jti = uuid.uuid4().hex
    payload = {
        "sub":  str(usuario_id),
        "type": "refresh",
        "jti":  jti,
        "exp":  datetime.now(timezone.utc) + timedelta(days=REFRESH_TOKEN_DAYS),
        "iat":  datetime.now(timezone.utc),
    }
    refresh_registry.emitir(usuario_id, jti)
    return jwt.encode(payload, SECRET_KEY, algorithm=ALGORITHM)


def emitir_par_tokens(usuario) -> dict:
    """Genera access + refresh para un Usuario ORM."""
    return {
        "access_token":  crear_access_token(
            usuario_id  = usuario.id,
            tenant_id   = usuario.tenant_id,
            rol         = usuario.rol,
            email       = usuario.email,
            sucursal_id = usuario.sucursal_id,
        ),
        "refresh_token": crear_refresh_token(usuario_id=usuario.id),
        "token_type":    "bearer",
        "expires_in":    ACCESS_TOKEN_MINUTES * 60,  # segundos
        "usuario": {
            "id":          usuario.id,
            "email":       usuario.email,
            "nombre":      usuario.nombre,
            "rol":         usuario.rol,
            "tenant_id":   usuario.tenant_id,
            "sucursal_id": usuario.sucursal_id,
        },
    }


# ── Decodificación ───────────────────────────────────────────────────────
def decodificar_token(token: str, tipo_esperado: str = "access") -> dict:
    """Decodifica y valida un JWT. Lanza HTTPException si falla."""
    try:
        payload = jwt.decode(token, SECRET_KEY, algorithms=[ALGORITHM])
    except JWTError as e:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail=f"Token inválido: {str(e)}",
            headers={"WWW-Authenticate": "Bearer"},
        )
    if payload.get("type") != tipo_esperado:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail=f"Tipo de token incorrecto (esperado: {tipo_esperado}).",
        )
    return payload


# ── Dependency FastAPI ───────────────────────────────────────────────────
def get_current_usuario(
    credentials: Optional[HTTPAuthorizationCredentials] = Depends(bearer_scheme),
) -> dict:
    """Extrae y valida el JWT del header Authorization. Retorna dict con claims.

    Retorna:
        {
            "usuario_id": int,
            "tenant_id":  int,
            "rol":        str,
            "email":      str,
            "sucursal_id": str | None,
        }
    """
    if credentials is None:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Se requiere autenticación.",
            headers={"WWW-Authenticate": "Bearer"},
        )

    payload = decodificar_token(credentials.credentials, tipo_esperado="access")

    try:
        return {
            "usuario_id":  int(payload["sub"]),
            "tenant_id":   int(payload["tenant_id"]),
            "rol":         payload["rol"],
            "email":       payload["email"],
            "sucursal_id": payload.get("sucursal_id"),
            # Compat con código v2 que espera "es_admin"
            "es_admin":    payload["rol"] == "super_admin",
        }
    except (KeyError, ValueError, TypeError):
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Token con estructura inválida. Inicia sesión nuevamente.",
        )
