"""
passwords.py — bcrypt hashing helpers used across the auth layer.

These were previously in `backend/auth.py` (v2). Centralising them under
`auth_v3` removes the last hard dependency on the legacy module.
"""
from __future__ import annotations

import bcrypt


def hash_password(plain: str) -> str:
    """Returns a bcrypt hash (cost=12) suitable for storing in the DB."""
    return bcrypt.hashpw(plain.encode("utf-8"), bcrypt.gensalt()).decode("utf-8")


def verify_password(plain: str, hashed: str) -> bool:
    """Constant-time comparison. Returns False on malformed hashes instead of raising."""
    try:
        return bcrypt.checkpw(plain.encode("utf-8"), hashed.encode("utf-8"))
    except (ValueError, TypeError):
        return False
