from pathlib import Path


MIGRATIONS = Path("supabase/migrations_v2")
BASE = (MIGRATIONS / "20260907144500_add_weekly_backlog_v2.sql").read_text(encoding="utf-8")
TRACKING = (MIGRATIONS / "20260913235500_add_accumulated_backlog_tracking_v2.sql").read_text(encoding="utf-8")


def test_backlog_has_one_tracking_row_per_order():
    assert "UNIQUE (orden_mantenimiento_id)" in BASE


def test_tracking_migration_restricts_lifecycle_and_counter():
    assert "PENDIENTE_DISPONIBLE" in TRACKING
    assert "PENDIENTE_PROGRAMADA" in TRACKING
    assert "FINALIZADA" in TRACKING
    assert "CHECK (reprogramaciones >= 0)" in TRACKING


def test_tracking_backfill_is_additive_and_preserves_first_origin():
    assert "ADD COLUMN IF NOT EXISTS" in TRACKING
    assert "COALESCE(primera_semana_origen_inicio,semana_origen_inicio)" in TRACKING
    assert "COALESCE(primera_semana_origen_fin,semana_origen_fin)" in TRACKING
    assert "TRUNCATE" not in TRACKING.upper()
    assert "DROP TABLE" not in TRACKING.upper()


def test_tracking_indexes_cover_active_queue_and_last_programming():
    assert "ix_backlog_v2_estado_especialidad" in TRACKING
    assert "ix_backlog_v2_ultima_programacion" in TRACKING
