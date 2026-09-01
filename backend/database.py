from __future__ import annotations

from functools import lru_cache

from sqlalchemy import create_engine
from sqlalchemy.engine import Engine
from sqlalchemy.pool import NullPool

from backend.config import require_database_url


@lru_cache(maxsize=1)
def get_engine() -> Engine:
    return create_engine(
        require_database_url(),
        poolclass=NullPool,
        pool_pre_ping=True,
        future=True,
    )
