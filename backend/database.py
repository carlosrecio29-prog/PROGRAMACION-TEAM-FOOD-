from __future__ import annotations

from functools import lru_cache

from sqlalchemy import create_engine, event
from sqlalchemy.engine import Engine
from sqlalchemy.pool import NullPool

from backend.config import require_database_url


SEARCH_PATH="programacion,sistema,public"


@lru_cache(maxsize=1)
def get_engine() -> Engine:
    url = require_database_url()
    connect_args = {}
    # Supavisor Transaction Pooler no admite prepared statements persistentes.
    if ".pooler.supabase.com:6543" in url:
        connect_args["prepare_threshold"] = None

    engine=create_engine(
        url,
        poolclass=NullPool,
        pool_pre_ping=True,
        future=True,
        connect_args=connect_args,
    )

    @event.listens_for(engine,"connect")
    def _set_search_path(dbapi_connection,connection_record):
        with dbapi_connection.cursor() as cursor:
            cursor.execute(f"SET search_path TO {SEARCH_PATH}")

    return engine
