from pathlib import Path

from backend.parsers.common import is_operation_plan
from backend.services.v2_import_service import _parse_plans
from backend.services.v2_monthly_calendar_import import _build_plan_lookups, _resolve_plan

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
    assert 'is_operation_plan(row["plan_clave_software"])' in source
    assert "excluded_plan_keys" in source
    assert "es_operacion=EXCLUDED.es_operacion" in source


def test_monthly_import_never_deletes_existing_programming():
    source = (ROOT / "backend/services/v2_monthly_calendar_import.py").read_text()
    assert "ON CONFLICT(source_key) DO UPDATE" in source
    assert "DELETE FROM programacion.orden_mantenimiento" not in source
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


def test_operation_prefix_accepts_missing_space_after_separator():
    assert is_operation_plan("27-OPERACIÓN -RUTINA ELÉCTRICA SEMESTRAL MOTOR MEDICION DE RESISTENCIA")


def test_monthly_plan_resolves_exact_master_description_only_when_unique():
    rows = [
        {
            "id": 1,
            "grupo": "200",
            "plan_trabajo": "MANTENIMIENTO",
            "descripcion_plan_trabajo": "Mantenimiento y Limpieza de Equipos Retráctiles",
            "es_operacion": False,
        },
        {
            "id": 2,
            "grupo": "200",
            "plan_trabajo": "OTRO PLAN",
            "descripcion_plan_trabajo": "Otra descripción",
            "es_operacion": False,
        },
    ]
    primary, descriptions = _build_plan_lookups(rows)
    plan, match_type = _resolve_plan(
        "200-Mantenimiento y Limpieza de Equipos Retráctiles",
        primary,
        descriptions,
    )
    assert plan["id"] == 1
    assert match_type == "DESCRIPCION_EXACTA"


def test_monthly_plan_does_not_guess_ambiguous_description():
    rows = [
        {
            "id": 1,
            "grupo": "90",
            "plan_trabajo": "PLAN A",
            "descripcion_plan_trabajo": "RUTINA SEMANAL",
            "es_operacion": False,
        },
        {
            "id": 2,
            "grupo": "90",
            "plan_trabajo": "PLAN B",
            "descripcion_plan_trabajo": "RUTINA SEMANAL",
            "es_operacion": False,
        },
    ]
    primary, descriptions = _build_plan_lookups(rows)
    plan, match_type = _resolve_plan("90-RUTINA SEMANAL", primary, descriptions)
    assert plan is None
    assert match_type == "DESCRIPCION_AMBIGUA"


def test_plan_parser_classifies_operation_from_description_too():
    source = (ROOT / "backend/services/v2_import_service.py").read_text()
    assert "is_operation_plan(plan) or is_operation_plan(description)" in source


def test_monthly_import_persists_equipment_level_operation_exclusions():
    source = (ROOT / "backend/services/v2_monthly_calendar_import.py").read_text()
    assert "operacion_exclusion_detalle_v2" in source
    assert '"activo_codigo": _scalar(row.get("activo_codigo"))' in source
    assert '"fila_origen": int(row["fila_origen"])' in source
