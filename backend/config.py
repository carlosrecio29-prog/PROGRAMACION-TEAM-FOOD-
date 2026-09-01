from __future__ import annotations

import os

DATABASE_URL = os.getenv("DATABASE_URL", "")
APP_ENV = os.getenv("APP_ENV", "development")
MAX_UPLOAD_BYTES = int(os.getenv("MAX_UPLOAD_BYTES", str(8 * 1024 * 1024)))


def require_database_url() -> str:
    if not DATABASE_URL:
        raise RuntimeError("DATABASE_URL no está configurada")
    return DATABASE_URL
