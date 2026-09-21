from pathlib import Path

from backend.parsers.common import is_operation_plan
from backend.services.v2_import_service import _parse_plans

ROOT = Path(__file__).resolve().parents[1]


def test_operation_prefix_accepts_accents_codes_and_spacing():
    assert is_operation_plan("12-OPERACIÓN - RUTINA MECÁNICA SEMESTRAL TANQUE")
    assert is_operation_plan("28-OPERACION - RUTINA MECANICA SEMESTRAL BOMBA")
    assert is_operation_plan("OPERACIÓN - RUTINA ELÉCTRICA")
    assert is_operation_plan("  12 - OPERACIÓN: TANQUE  ")


def test_operation_prefix_does_not_match_elsewhere_or_as_word_part():
    assert not is_operation_plan("RUTINA DE OPERACIÓN TANQUE")
    assert not is_operation_plan("OPERACIONAL - TANQUE")
    assert not is_operation_plan("MANTENIMIENTO - OPERACIÓN")
    assert not is_operation_plan("")


def test_v2_reader_uses_operation_master_flag():
    source = (ROOT / "backend/services/v2_maintenance_import_service.py").read_text()
    assert "pmp_excluidos_operacion" in source
    assert 'if normalize_text(row["plan_clave_software"]) in excluded_plan_keys' in source
    assert "es_operacion=EXCLUDED.es_operacion" in source


def test_monthly_import_never_deletes_existing_programming():
    source = (ROOT / "backend/services/v2_monthly_calendar_import.py").read_text()
    assert "ON CONFLICT(source_key) DO UPDATE" in source
    assert "DELETE FROM" not in source
    assert "TRUNCATE" not in source


def test_operation_orders_are_hidden_and_cannot_be_saved():
    for path in [
        "backend/services/v2_query_service.py",
        "backend/services/v2_programming_runtime.py",
        "backend/services/v2_backlog_service.py",
    ]:
        source = (ROOT / path).read_text()
        assert "es_operacion" in source


def test_old_zero_stop_rule_remains_independent():
    source = (ROOT / "backend/services/v2_import_service.py").read_text()
    assert '"tiempo_parada_min":_number(cell_by_header(row,m,"TiempoParada"))' in source
