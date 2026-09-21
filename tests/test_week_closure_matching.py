from pathlib import Path

from backend.services.v2_closure_service import (
    _index_calendar, _match_calendar_item, _is_finalized,
)

ROOT = Path(__file__).resolve().parents[1]


def sample_item():
    return {
        "numero_ot": "OT-12119-26",
        "activo_codigo": "BA-FR-FC-FL01-FT01",
        "plan_clave_software": "33-ANÁLISIS DE ACEITE",
    }


def sample_calendar(state="FINALIZADO"):
    return {
        "numero_ot": "OT-12119-26",
        "activo": "BA-FR-FC-FL01-FT01",
        "plan": "33-ANÁLISIS DE ACEITE",
        "estado": state,
    }


def test_exact_matching_accepts_accents_and_finalized_status():
    exact, by_ot = _index_calendar([sample_calendar()])
    row, mode = _match_calendar_item(sample_item(), exact, by_ot)
    assert mode == "OT_EQUIPO_PLAN"
    assert _is_finalized(row["estado"])


def test_open_order_keeps_pending_status():
    exact, by_ot = _index_calendar([sample_calendar("ABIERTO")])
    row, _ = _match_calendar_item(sample_item(), exact, by_ot)
    assert not _is_finalized(row["estado"])


def test_wrong_asset_or_plan_must_not_be_matched_just_by_ot():
    row = sample_calendar()
    row["activo"] = "OTRO-ACTIVO"
    exact, by_ot = _index_calendar([row])
    result, reason = _match_calendar_item(sample_item(), exact, by_ot)
    assert result is None
    assert reason == "EQUIPO_NO_COINCIDE"
    row["activo"] = sample_item()["activo_codigo"]
    row["plan"] = "PLAN DISTINTO"
    exact, by_ot = _index_calendar([row])
    result, reason = _match_calendar_item(sample_item(), exact, by_ot)
    assert result is None
    assert reason == "PLAN_NO_COINCIDE"


def test_duplicate_calendar_entries_are_ambiguous_not_finalized():
    row = sample_calendar()
    exact, by_ot = _index_calendar([row, row])
    result, reason = _match_calendar_item(sample_item(), exact, by_ot)
    assert result is None
    assert reason == "DUPLICADA_EN_CALENDARIO"


def test_frontend_shares_week_label_and_previews_before_close():
    source = (ROOT / "frontend/src/components/WeeklyClosure.jsx").read_text()
    assert "w.transition ? 'Transición' : `Semana ${w.weekNumber}`" in source
    assert "previewV2WeekClosure" in source
    assert "Confirmar cierre semanal" in source
