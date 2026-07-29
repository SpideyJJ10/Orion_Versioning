"""
auth_v3 — Authentication v3 with granular roles + refresh tokens.

Single source of truth for authentication after the v2 (`backend/auth.py`) removal.
Exports:
  - Rol (Enum with hierarchy)
  - requiere_rol(Rol) — FastAPI dependency factory
  - crear_access_token, crear_refresh_token, emitir_par_tokens
  - decodificar_token — JWT decoder/validator
  - get_current_usuario — extracts the authenticated user from the Bearer token
  - hash_password, verify_password — bcrypt helpers (moved from legacy auth.py)
"""
from backend.auth_v3.passwords import hash_password, verify_password
from backend.auth_v3.permissions import Rol, requiere_rol, requiere_tenant_activo
from backend.auth_v3.tokens import (
    crear_access_token,
    crear_refresh_token,
    decodificar_token,
    emitir_par_tokens,
    get_current_usuario,
)

__all__ = [
    "Rol",
    "requiere_rol",
    "requiere_tenant_activo",
    "crear_access_token",
    "crear_refresh_token",
    "decodificar_token",
    "emitir_par_tokens",
    "get_current_usuario",
    "hash_password",
    "verify_password",
]
