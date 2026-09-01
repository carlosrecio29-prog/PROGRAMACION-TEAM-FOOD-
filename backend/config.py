from __future__ import annotations

import os
from urllib.parse import quote, unquote

DATABASE_URL = os.getenv("DATABASE_URL", "")
APP_ENV = os.getenv("APP_ENV", "development")
MAX_UPLOAD_BYTES = int(os.getenv("MAX_UPLOAD_BYTES", str(8 * 1024 * 1024)))


def normalize_database_url(value: str) -> str:
    """
    Normaliza la URL para SQLAlchemy + psycopg v3.

    - Acepta postgres:// y postgresql://.
    - Fuerza el driver psycopg instalado en requirements.txt.
    - Re-codifica user/password para soportar caracteres reservados
      que hayan sido pegados sin URL-encoding en variables de entorno.
    """
    value = (value or "").strip()
    if not value:
        return ""

    if value.startswith("postgres://"):
        value = "postgresql://" + value[len("postgres://"):]

    if value.startswith("postgresql://"):
        value = "postgresql+psycopg://" + value[len("postgresql://"):]

    if not value.startswith("postgresql+psycopg://"):
        return value

    scheme, rest = value.split("://", 1)
    authority, slash, tail = rest.partition("/")

    if "@" in authority:
        userinfo, hostpart = authority.rsplit("@", 1)
        if ":" in userinfo:
            username, password = userinfo.split(":", 1)
            username = quote(unquote(username), safe="")
            password = quote(unquote(password), safe="")
            authority = f"{username}:{password}@{hostpart}"

    return f"{scheme}://{authority}{slash}{tail}"


def require_database_url() -> str:
    url = normalize_database_url(DATABASE_URL)
    if not url:
        raise RuntimeError("DATABASE_URL no está configurada")
    return url
