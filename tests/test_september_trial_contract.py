from pathlib import Path
import re

ROOT = Path(__file__).resolve().parents[1]


def test_monthly_initial_import_is_non_destructive_and_guarded():
    source = (ROOT / "backend/services/v2_monthly_calendar_import.py").read_text(encoding="utf-8")
    assert "programmed_count" in source
    assert "Ya existen OT de este mes en programación semanal" in source
    # The monthly import refreshes only its derived exclusion lists for one
    # period. Maintenance orders, assignments and closures must survive.
    deletions = re.findall(r"DELETE\s+FROM\s+([\w.]+)\s+WHERE\s+periodo=:period", source)
    assert set(deletions) == {"programacion.operacion_exclusion_detalle_v2",
                              "programacion.operacion_exclusion_periodo_v2"}
    assert len(re.findall(r"DELETE\s+FROM", source)) == len(deletions)
    assert "ON CONFLICT(source_key) DO UPDATE" in source
    assert "TRUNCATE" not in source
    assert "pmp_abiertos_archivo" in source
    assert "registros_previos_no_en_archivo" in source


def test_weekly_close_does_not_duplicate_assignment_or_overwrite_closed_week():
    source = (ROOT / "backend/services/v2_closure_service.py").read_text(encoding="utf-8")
    assert "ultimo_cierre_en=now(),\n                  ultimo_cierre_en=now()" not in source
    assert 'if programming["estado"] == "CERRADA"' in source


def test_weekly_views_use_one_shared_calendar_cut():
    for path in [
        "frontend/src/components/WeeklyProgramming.jsx",
        "frontend/src/components/WeeklyClosure.jsx",
    ]:
        source = (ROOT / path).read_text(encoding="utf-8")
        assert "from '../features/planning/monthWeeks.js'" in source or 'from "../features/planning/monthWeeks.js"' in source
        assert "function monthWeeks(" not in source
