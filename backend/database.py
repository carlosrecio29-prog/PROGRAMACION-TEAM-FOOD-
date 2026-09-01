from __future__ import annotations

from functools import lru_cache

from sqlalchemy import create_engine
from sqlalchemy.engine import Engine
from sqlalchemy.pool import NullPool

from backend.config import require_database_url


@lru_cache(maxsize=1)
def get_engine() -> Engine:
    url = require_database_url()
    connect_args = {}
    # Supavisor Transaction Pooler no admite prepared statements persistentes.
    if ".pooler.supabase.com:6543" in url:
        connect_args["prepare_threshold"] = None
    return create_engine(
        url,
        poolclass=NullPool,
        pool_pre_ping=True,
        future=True,
        connect_args=connect_args,
    )
