from __future__ import annotations

import os
import re
from urllib.parse import quote, unquote

DATABASE_URL = os.getenv("DATABASE_URL", "")
APP_ENV = os.getenv("APP_ENV", "development")
MAX_UPLOAD_BYTES = int(os.getenv("MAX_UPLOAD_BYTES", str(8 * 1024 * 1024)))
SUPABASE_REGION = os.getenv("SUPABASE_REGION", "us-west-2")


def normalize_database_url(value: str) -> str:
    """
    Normaliza la URL para SQLAlchemy + psycopg v3.

    Si Vercel recibe la conexión directa de Supabase:
      db.<project-ref>.supabase.co:5432
    la convierte automáticamente al Session Pooler IPv4:
      aws-0-<region>.pooler.supabase.com:5432

    Esto evita fallos de red IPv6 en entornos serverless.
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

    username = ""
    password = ""
    hostpart = authority

    if "@" in authority:
        userinfo, hostpart = authority.rsplit("@", 1)
        if ":" in userinfo:
            username, password = userinfo.split(":", 1)
        else:
            username = userinfo

    host = hostpart.split(":", 1)[0]
    direct_match = re.fullmatch(r"db\.([a-z0-9]+)\.supabase\.co", host, re.I)

    if direct_match:
        project_ref = direct_match.group(1)
        username = f"postgres.{project_ref}"
        hostpart = f"aws-0-{SUPABASE_REGION}.pooler.supabase.com:5432"

    if username:
        username = quote(unquote(username), safe="")
    if password:
        password = quote(unquote(password), safe="")

    if username:
        authority = f"{username}:{password}@{hostpart}" if password else f"{username}@{hostpart}"
    else:
        authority = hostpart

    url = f"{scheme}://{authority}{slash}{tail}"

    if direct_match and "sslmode=" not in url:
        url += ("&" if "?" in url else "?") + "sslmode=require"

    return url


def require_database_url() -> str:
    url = normalize_database_url(DATABASE_URL)
    if not url:
        raise RuntimeError("DATABASE_URL no está configurada")
    return url


def database_url_diagnostics() -> dict:
    raw = (DATABASE_URL or "").strip()
    if not raw:
        return {
            "configured": False,
            "driver": None,
            "host": None,
            "port": None,
            "pooler": None,
        }

    normalized = normalize_database_url(raw)
    try:
        _, rest = normalized.split("://", 1)
        authority = rest.split("/", 1)[0]
        hostpart = authority.rsplit("@", 1)[-1]
        if ":" in hostpart:
            host, port = hostpart.rsplit(":", 1)
        else:
            host, port = hostpart, None
    except Exception:
        host, port = None, None

    pooler = None
    if host:
        if "pooler.supabase.com" in host:
            pooler = "transaction" if str(port) == "6543" else "session"
        elif host.startswith("db.") and host.endswith(".supabase.co"):
            pooler = "direct"

    return {
        "configured": True,
        "driver": normalized.split("://", 1)[0] if "://" in normalized else None,
        "host": host,
        "port": port,
        "pooler": pooler,
    }
