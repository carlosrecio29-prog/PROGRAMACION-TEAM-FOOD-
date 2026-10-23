from datetime import date
from pathlib import Path

import pytest

from backend.services.v2_backlog_service import _build_backlog_filters
from backend.services.v2_closure_service import _is_finalized
from backend.services.v2_programming_service import _validate_week


PROGRAMMING = Path("backend/services/v2_programming_runtime.py").read_text(encoding="utf-8")
CLOSURE = Path("backend/services/v2_closure_service.py").read_text(encoding="utf-8")
BACKLOG = Path("backend/services/v2_backlog_service.py").read_text(encoding="utf-8")


def test_backlog_filters_cover_state_specialty_area_age_text_and_order_context():
    where, params = _build_backlog_filters(
        specialty="mec", area="ENV", state="pendiente_disponible",
        search="OT-100", order_id=42, age_min=7, age_max=30,
    )
    assert params == {
        "specialty": "MEC", "area": "ENV", "state": "PENDIENTE_DISPONIBLE",
        "search": "%OT-100%", "order_id": 42, "age_min": 7, "age_max": 30,
    }
    for fragment in (":specialty", ":area", ":state", ":search", ":order_id", ":age_min", ":age_max"):
        assert fragment in where


def test_backlog_defaults_to_active_rows_and_rejects_unknown_state():
    where, _ = _build_backlog_filters()
    assert "b.estado_seguimiento IN ('PENDIENTE_DISPONIBLE','PENDIENTE_PROGRAMADA')" in where
    assert "NOT LIKE 'ANUL%'" in where
    assert "NOT LIKE 'FINALIZ%'" in where
    with pytest.raises(ValueError, match="Estado de backlog inválido"):
        _build_backlog_filters(state="BORRADA")


def test_pending_reprogrammed_pending_finalized_lifecycle_is_encoded_transactionally():
    assert "with get_engine().begin()" in PROGRAMMING
    assert "estado_seguimiento='PENDIENTE_PROGRAMADA'" in PROGRAMMING
    assert "reprogramaciones=reprogramaciones+1" in PROGRAMMING
    assert "DELETE FROM programacion.backlog_v2" not in PROGRAMMING
    assert "estado_seguimiento='PENDIENTE_DISPONIBLE'" in CLOSURE
    assert "ultimo_resultado_cierre='NO_ENCONTRADA'" in CLOSURE
    assert "estado_seguimiento='FINALIZADA'" in CLOSURE
    assert "finalizado_en=now()" in CLOSURE


def test_first_origin_and_duplicate_assignment_guards_are_preserved():
    assert "COALESCE(primera_semana_origen_inicio,semana_origen_inicio)" in PROGRAMMING
    assert "COALESCE(primera_semana_origen_inicio,semana_origen_inicio)" in CLOSURE
    assert "other_program.estado<>'CERRADA'" in PROGRAMMING
    assert "ya está programada" in PROGRAMMING


def test_external_finalization_variants_are_canonicalized():
    assert _is_finalized("FINALIZADA")
    assert _is_finalized("FINALIZADO")
    assert not _is_finalized("PENDIENTE")


def test_mechanical_week_is_valid_and_confirmed_previous_results_are_excluded():
    assert _validate_week(date(2026, 9, 1), date(2026, 9, 7), "mec") == "MEC"
    assert "o.especialidad=:specialty" in PROGRAMMING
    # The weekly universe is historical: a source completion does not erase
    # first-week demand. Only confirmed earlier closures resolve that demand.
    block = PROGRAMMING.split("resolved_before_week AS (", 1)[1].split("moved_to_backlog_before_week AS (", 1)[0]
    assert "ps.estado='CERRADA'" in block
    assert "ps.semana_fin < :date_from" in block
    assert "COALESCE(pi.finalizado,false)=true" in block
    assert "COALESCE(pi.anulado,false)=true" in block
    assert "FROM resolved_before_week r" in PROGRAMMING
    assert "r.orden_mantenimiento_id=o.id" in PROGRAMMING


def test_hh_capacity_and_closure_indicators_remain_backend_authoritative():
    assert "def _capacity" in Path("backend/services/v2_programming_service.py").read_text(encoding="utf-8")
    assert "hh_programadas" in CLOSURE
    assert "hh_finalized" not in BACKLOG
    assert "round(COALESCE(o.tiempo_planeado_min,p.tiempo_ejecucion_min)/60.0" in PROGRAMMING
