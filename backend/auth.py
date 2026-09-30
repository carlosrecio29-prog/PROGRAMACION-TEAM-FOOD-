from __future__ import annotations

import base64
import hashlib
import hmac
import secrets
from datetime import datetime, timedelta, timezone

from fastapi import Request
from fastapi.responses import JSONResponse
from sqlalchemy import text

from backend.database import get_engine


COOKIE_NAME = "team_food_admin"
SESSION_HOURS = 12
SAFE_METHODS = {"GET", "HEAD", "OPTIONS"}
AUTH_WRITE_PATHS = {"/api/auth/login", "/api/auth/logout"}


def _token_hash(token: str) -> str:
    return hashlib.sha256(token.encode("utf-8")).hexdigest()


def verify_admin_password(password: str) -> bool:
    if not password or len(password) > 256:
        return False

    with get_engine().connect() as conn:
        row = conn.execute(
            text(
                """
                SELECT password_salt, password_hash, iterations
                FROM programacion.app_admin_auth
                WHERE id = 1
                """
            )
        ).mappings().first()

    if not row:
        return False

    try:
        salt = base64.urlsafe_b64decode(row["password_salt"])
        expected = base64.urlsafe_b64decode(row["password_hash"])
        candidate = hashlib.pbkdf2_hmac(
            "sha256",
            password.encode("utf-8"),
            salt,
            int(row["iterations"]),
        )
    except Exception:
        return False

    return hmac.compare_digest(candidate, expected)


def create_admin_session() -> tuple[str, datetime]:
    token = secrets.token_urlsafe(48)
    token_digest = _token_hash(token)
    expires_at = datetime.now(timezone.utc) + timedelta(hours=SESSION_HOURS)

    with get_engine().begin() as conn:
        conn.execute(
            text(
                """
                DELETE FROM programacion.app_admin_session
                WHERE expires_at <= now() OR revoked_at IS NOT NULL
                """
            )
        )
        conn.execute(
            text(
                """
                INSERT INTO programacion.app_admin_session(
                    token_hash, created_at, expires_at, revoked_at
                )
                VALUES (:token_hash, now(), :expires_at, NULL)
                """
            ),
            {"token_hash": token_digest, "expires_at": expires_at},
        )

    return token, expires_at


def revoke_admin_session(token: str | None) -> None:
    if not token:
        return
    with get_engine().begin() as conn:
        conn.execute(
            text(
                """
                UPDATE programacion.app_admin_session
                SET revoked_at = now()
                WHERE token_hash = :token_hash
                  AND revoked_at IS NULL
                """
            ),
            {"token_hash": _token_hash(token)},
        )


def is_admin_token(token: str | None) -> bool:
    if not token:
        return False
    with get_engine().connect() as conn:
        row = conn.execute(
            text(
                """
                SELECT 1
                FROM programacion.app_admin_session
                WHERE token_hash = :token_hash
                  AND revoked_at IS NULL
                  AND expires_at > now()
                LIMIT 1
                """
            ),
            {"token_hash": _token_hash(token)},
        ).first()
    return bool(row)


def request_is_admin(request: Request) -> bool:
    return is_admin_token(request.cookies.get(COOKIE_NAME))


async def admin_write_guard(request: Request, call_next):
    path = request.url.path
    method = request.method.upper()

    if method in SAFE_METHODS or path in AUTH_WRITE_PATHS:
        return await call_next(request)

    if request_is_admin(request):
        return await call_next(request)

    return JSONResponse(
        status_code=403,
        content={
            "detail": "Modo solo lectura. Inicia sesión como administrador para modificar información.",
            "role": "viewer",
        },
    )
