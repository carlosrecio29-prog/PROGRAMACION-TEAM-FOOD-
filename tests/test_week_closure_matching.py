from pathlib import Path

from backend.services.v2_closure_service import (
    _index_calendar, _match_calendar_item, _is_finalized, _is_annulled,
    _effective_closure_state,
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
    exact, by_ot = _index_calendar([row, sample_calendar("ABIERTO")])
    result, reason = _match_calendar_item(sample_item(), exact, by_ot)
    assert result is None
    assert reason == "DUPLICADA_EN_CALENDARIO"


def test_frontend_shares_week_label_and_previews_before_close():
    source = (ROOT / "frontend/src/components/WeeklyClosure.jsx").read_text()
    assert 'item.transition ? "Transición" : `Semana ${item.weekNumber}`' in source
    assert "previewV2WeekClosure" in source
    assert "Confirmar cierre semanal" in source


def test_calendar_requires_expected_columns_and_does_not_silently_close():
    import io
    from openpyxl import Workbook
    import pytest
    from backend.services.v2_closure_service import _parse_calendar, V2ClosureError

    book = Workbook()
    sheet = book.active
    sheet.append(["Orden", "Activo", "PlanTrabajo", "OTRO ESTADO"])
    sheet.append(["OT-12119-26", "BA-FR-FC-FL01-FT01", "33-ANÁLISIS DE ACEITE", "FINALIZADO"])
    data = io.BytesIO()
    book.save(data)
    with pytest.raises(V2ClosureError, match="Orden, Activo, PlanTrabajo y Estado"):
        _parse_calendar(data.getvalue())


def test_close_rejects_conflicts_in_backend_before_commit():
    source = (ROOT / "backend/services/v2_closure_service.py").read_text()
    assert 'if match_reason in {' in source
    assert "Revisa el archivo en la vista previa antes de cerrar." in source


def test_identical_repeat_in_export_is_not_ambiguous():
    row = sample_calendar()
    exact, by_ot = _index_calendar([row, row])
    match, reason = _match_calendar_item(sample_item(), exact, by_ot)
    assert reason == "OT_EQUIPO_PLAN"
    assert match["estado"] == "FINALIZADO"


def test_different_statuses_on_same_ot_are_not_silently_merged():
    exact, by_ot = _index_calendar([
        sample_calendar("ABIERTO"), sample_calendar("FINALIZADO"),
    ])
    match, reason = _match_calendar_item(sample_item(), exact, by_ot)
    assert match is None
    assert reason == "DUPLICADA_EN_CALENDARIO"


def test_preview_separates_real_absences_from_conflicts():
    source = (ROOT / "backend/services/v2_closure_service.py").read_text()
    for field in ('"missing"', '"conflicts"', '"blank_states"', '"alternativas_en_excel"'):
        assert field in source
    frontend = (ROOT / "frontend/src/components/WeeklyClosure.jsx").read_text()
    assert "missingRows" in frontend
    assert "conflictingRows" in frontend
    assert "closureBlocked" in frontend


def test_activity_without_ot_is_never_closed_automatically():
    item = {
        "numero_ot": None,
        "especialidad": "MEC",
        "activo_codigo": "BA-EM-E3-LL02",
        "plan_clave_software": "59-MANTENIMIENTO MECÁNICO SEMESTRAL LLENADORA DE BIDONES",
    }
    row = {
        "numero_ot": "",
        "activo": "BA-EM-E3-LL02",
        "plan": "59-MANTENIMIENTO MECÁNICO SEMESTRAL LLENADORA DE BIDONES",
        "estado": "FINALIZADO",
    }
    exact, by_ot = _index_calendar([row])
    match, reason = _match_calendar_item(item, exact, by_ot)
    assert match is None
    assert reason == "SIN_NUMERO_OT"


def test_no_ot_rule_applies_equally_to_all_specialties():
    for specialty in ("MEC", "ELE", "SER", "MET"):
        item = {
            "numero_ot": None,
            "especialidad": specialty,
            "activo_codigo": "EQ-01",
            "plan_clave_software": "10-RUTINA",
        }
        exact, by_ot = _index_calendar([])
        match, reason = _match_calendar_item(item, exact, by_ot)
        assert match is None
        assert reason == "SIN_NUMERO_OT"


def test_backend_requires_explicit_resolution_for_no_ot_before_close():
    source = (ROOT / "backend/services/v2_closure_service.py").read_text()
    assert "manual_resolutions" in source
    assert "debes asignar una OT o definir manualmente" in source
    assert "ESTADO_MANUAL_SIN_OT" in source
    assert "La OT {assigned_ot}" in source


def test_frontend_blocks_close_until_no_ot_rows_are_resolved():
    source = (ROOT / "frontend/src/components/WeeklyClosure.jsx").read_text()
    assert "unresolvedNoOtRows" in source
    assert "Asignar OT" in source
    assert "FINALIZADA" in source
    assert "PENDIENTE" in source


def test_annulled_status_is_terminal_not_finalized():
    assert _is_annulled("ANULADA")
    assert _is_annulled("anulado")
    assert not _is_finalized("ANULADA")


def test_frontend_supports_annulment_comment_and_compact_selectors():
    source = (ROOT / "frontend/src/components/WeeklyClosure.jsx").read_text()
    assert '<option value="ANULADA">ANULADA</option>' in source
    assert "comentario" in source
    assert "Motivo obligatorio si anulas" in source
    assert "tf-program-selectors" in source
    assert "Ver resultado del cierre" in source


def test_closure_honors_saved_manual_status_when_ot_missing_in_excel():
    decision = _effective_closure_state(
        None, "NO_ENCONTRADA", {"estado": "FINALIZADA", "comentario": "Verificado por mantenimiento"}
    )
    assert decision["state"] == "FINALIZADA"
    assert decision["reason"] == "SEGUIMIENTO_MANUAL"
    assert decision["matched"] == {"estado": "FINALIZADA"}
    assert decision["excel_reason"] == "NO_ENCONTRADA"
    assert decision["comment"] == "Verificado por mantenimiento"


def test_closure_preserves_manual_pending_when_excel_has_no_match():
    decision = _effective_closure_state(
        None, "NO_ENCONTRADA", {"estado": "PENDIENTE", "comentario": None}
    )
    assert decision["state"] == "PENDIENTE"
    assert decision["reason"] == "SEGUIMIENTO_MANUAL"
    assert decision["discrepancy"] is False


def test_closure_manual_annulled_overrides_automatically_finalized():
    decision = _effective_closure_state(
        sample_calendar("FINALIZADO"), "OT_EQUIPO_PLAN",
        {"estado": "ANULADA", "comentario": "Cancelada por supervisión"},
    )
    assert decision["state"] == "ANULADA"
    assert decision["excel_state"] == "FINALIZADO"
    assert decision["discrepancy"] is True
    assert _is_annulled(decision["matched"]["estado"])


def test_closure_matches_equivalent_manual_and_excel_finalized_states():
    decision = _effective_closure_state(
        sample_calendar("Finalizado"), "OT_EQUIPO_PLAN",
        {"estado": "FINALIZADA"},
    )
    assert decision["discrepancy"] is False
    assert decision["excel_reason"] == "OT_EQUIPO_PLAN"


def test_closure_uses_excel_if_no_manual_decision():
    decision = _effective_closure_state(
        sample_calendar("ABIERTO"), "OT_EQUIPO_PLAN", None
    )
    assert decision["state"] == "ABIERTO"
    assert decision["manual"] is None
    assert decision["reason"] == "OT_EQUIPO_PLAN"


def test_closure_manual_status_is_loaded_at_preview_and_at_commit():
    source = (ROOT / "backend/services/v2_closure_service.py").read_text()
    assert source.count("manual_states = _load_manual_tracking_states(conn, programming_id)") == 2
    assert 'f"{filename} · SEGUIMIENTO MANUAL"' in source
    frontend = (ROOT / "frontend/src/components/WeeklyClosure.jsx").read_text()
    assert "IDENTIFICADA MANUALMENTE" in frontend
    assert "Estado aplicado" in frontend
