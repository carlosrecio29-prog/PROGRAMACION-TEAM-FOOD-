from __future__ import annotations

import hashlib
import json
import os
import pathlib
import sys
import urllib.error
import urllib.request

PROJECT_REF = os.environ["SUPABASE_PROJECT_ID"]
ACCESS_TOKEN = os.environ["SUPABASE_ACCESS_TOKEN"]
BASE_URL = f"https://api.supabase.com/v1/projects/{PROJECT_REF}/database/query"
MIGRATIONS_DIR = pathlib.Path("supabase/migrations_v2")


def api_query(sql: str):
    body = json.dumps({"query": sql}).encode("utf-8")
    req = urllib.request.Request(
        BASE_URL,
        data=body,
        method="POST",
        headers={
            "Authorization": f"Bearer {ACCESS_TOKEN}",
            "Content-Type": "application/json",
            "Accept": "application/json",
            "User-Agent": "GitHub-Actions-Programacion-Team-Food/1.0",
        },
    )
    try:
        with urllib.request.urlopen(req, timeout=180) as response:
            raw = response.read().decode("utf-8")
            return json.loads(raw) if raw else None
    except urllib.error.HTTPError as exc:
        raw = exc.read().decode("utf-8", errors="replace")
        raise RuntimeError(f"Supabase Management API {exc.code}: {raw}") from exc


def sql_literal(value: str) -> str:
    return "'" + value.replace("'", "''") + "'"


def main() -> int:
    if not MIGRATIONS_DIR.exists():
        print("No existe supabase/migrations_v2; no hay migraciones V2 que aplicar.")
        return 0

    files = sorted(MIGRATIONS_DIR.glob("*.sql"))
    if not files:
        print("No hay archivos .sql en supabase/migrations_v2.")
        return 0

    api_query("""
    CREATE SCHEMA IF NOT EXISTS sistema;
    DO $$
    BEGIN
      IF to_regclass('sistema.app_migration_history') IS NULL
         AND EXISTS (
           SELECT 1
           FROM pg_class c
           JOIN pg_namespace n ON n.oid=c.relnamespace
           WHERE n.nspname='mantenimiento'
             AND c.relname='app_migration_history'
             AND c.relkind='r'
         )
      THEN
        ALTER TABLE mantenimiento.app_migration_history SET SCHEMA sistema;
      END IF;
    END $$;
    CREATE TABLE IF NOT EXISTS sistema.app_migration_history (
        version text PRIMARY KEY,
        name text NOT NULL,
        checksum char(64) NOT NULL,
        applied_at timestamptz NOT NULL DEFAULT now()
    );
    """)

    existing_rows = api_query(
        "SELECT version, checksum FROM sistema.app_migration_history ORDER BY version;"
    ) or []
    existing = {
        str(row["version"]): str(row["checksum"])
        for row in existing_rows
        if isinstance(row, dict) and "version" in row
    }
    native_rows = api_query(
        "SELECT version FROM supabase_migrations.schema_migrations ORDER BY version;"
    ) or []
    native = {
        str(row["version"])
        for row in native_rows
        if isinstance(row, dict) and "version" in row
    }

    applied = 0
    for path in files:
        stem = path.stem
        version, _, name = stem.partition("_")
        sql = path.read_text(encoding="utf-8")
        checksum = hashlib.sha256(sql.encode("utf-8")).hexdigest()

        if version in native:
            print(f"SKIP {path.name} (ya registrada por Supabase)")
            continue

        if version in existing:
            if existing[version] != checksum:
                raise RuntimeError(
                    f"La migración {version} ya fue aplicada pero su checksum cambió. "
                    "No edites migraciones históricas; crea una nueva."
                )
            print(f"SKIP {path.name} (ya aplicada por el pipeline)")
            continue

        print(f"APPLY {path.name}")
        wrapped = f"""
        BEGIN;
        {sql}
        INSERT INTO sistema.app_migration_history(version, name, checksum)
        VALUES (
            {sql_literal(version)},
            {sql_literal(name or stem)},
            {sql_literal(checksum)}
        );
        COMMIT;
        """
        api_query(wrapped)
        applied += 1

    print(f"Migraciones nuevas aplicadas: {applied}")
    return 0


if __name__ == "__main__":
    try:
        raise SystemExit(main())
    except Exception as exc:
        print(f"ERROR: {exc}", file=sys.stderr)
        raise
