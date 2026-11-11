from datetime import date
import pytest

from backend.services.v2_sheet_sync_service import (
    SheetSyncError, _operation, _parse_rows, _status, _minutes,
)

HEADERS = [
    "MES", "ÁREA", "# DE ORDEN", "ESPECIALIDAD", "CÓDIGO",
    "DESCRIPCIÓN", "OBSERVACIÓN", "ESTADO", "FECHA PROG",
    "CRITICIDAD", "AÑO", "TIEMPO", "PLAN DE TRABAJO "
]


def source_row(ot="OT-15001-26", status="PENDIENTE",
               plan="44-RUTINA ELÉCTRICA ANUAL MOTOR",
               specialty="ELE", month="NOVIEMBRE"):
    return [
        month, "JABONERÍA", ot, specialty, "BA-JB-XY-010",
        "MOTOR", "RUTINA", status, "03-nov.-26", "A", "2026", "25", plan
    ]


def test_operation_exclusion_uses_plan_prefix_after_group_code():
    assert _operation("44-OPERACIÓN - RUTINA ELÉCTRICA SEMESTRAL") is True
    assert _operation("126-OPERACION TRIMESTRAL") is True
    assert _operation("44-RUTINA DE OPERACIÓN EXTERIOR") is False
    assert _operation("27-RUTINA MEDICION DE RESISTENCIA") is False


def test_source_states_are_canonical_and_zero_time_is_valid():
    assert _status("FINALIZADA") == "FINALIZADA"
    assert _status("FINALIZADO") == "FINALIZADA"
    assert _status("ANULADA") == "ANULADA"
    assert _status("PENDIENTE") == "PENDIENTE"
    assert _minutes("0") == 0


def test_base_de_datos_filters_month_and_deduplicates_identical_ot():
    rows = [
        HEADERS,
        source_row(),
        source_row(),
        source_row(ot="OT-15002-26", status="FINALIZADA",
                   plan="126-OPERACIÓN - LIMPIEZA"),
        source_row(month="OCTUBRE", ot="OT-14666-26"),
    ]
    selected, warnings, scan = _parse_rows(rows, date(2026,11,1))
    assert set(selected) == {"OT-15001-26","OT-15002-26"}
    assert selected["OT-15002-26"]["operation"] is True
    assert selected["OT-15002-26"]["estado"] == "FINALIZADA"
    assert scan["filas_repetidas"] == 1
    assert scan["ots_unicas_validas"] == 2
    assert not warnings


def test_conflicting_duplicate_is_never_applied():
    selected,warnings,scan = _parse_rows([
        HEADERS,
        source_row(),
        source_row(status="FINALIZADA"),
    ], date(2026,11,1))
    assert selected == {}
    assert scan["duplicados_conflictivos"] == 1
    assert any("OT-15001-26" in error for error in warnings)


def test_incomplete_status_does_not_turn_into_pending():
    selected,warnings,scan = _parse_rows([
        HEADERS,source_row(status="SIN CLASIFICAR")
    ], date(2026,11,1))
    assert not selected
    assert len(warnings) == 1


def test_empty_period_aborts_without_modifying_database():
    with pytest.raises(SheetSyncError, match="No hay OT"):
        _parse_rows([HEADERS,source_row(month="OCTUBRE")], date(2026,11,1))


def test_transport_preserves_original_base_de_datos_row_number():
    selected, _, _ = _parse_rows([
        HEADERS + ["__ORIGINAL_ROW"],
        source_row() + ["14937"],
    ], date(2026, 11, 1))
    assert selected["OT-15001-26"]["row"] == 14937


def test_apps_script_pull_uses_private_post(monkeypatch):
    import json
    from backend.services.v2_sheet_sync_service import _read_sheet_apps_script

    monkeypatch.setenv("SHEET_SYNC_SECRET", "S" * 48)
    monkeypatch.setenv(
        "APPS_SCRIPT_WEBAPP_URL",
        "https://script.google.com/macros/s/AKfycbMockDeploy/exec",
    )
    captured = {}

    class Response:
        def __enter__(self):
            return self

        def __exit__(self, *args):
            return False

        def read(self, size):
            return json.dumps({
                "ok": True, "year": 2026, "month": 11,
                "values": [HEADERS, source_row()],
            }).encode("utf-8")

    def fake_urlopen(request, timeout):
        captured.update({
            "url": request.full_url,
            "method": request.get_method(),
            "payload": json.loads(request.data),
            "content_type": request.get_header("Content-type"),
            "timeout": timeout,
        })
        return Response()

    monkeypatch.setattr("urllib.request.urlopen", fake_urlopen)
    rows = _read_sheet_apps_script(2026, 11)
    assert len(rows) == 2
    assert captured["method"] == "POST"
    assert captured["content_type"] == "application/json"
    assert "S" * 48 not in captured["url"]
    assert captured["payload"]["secret"] == "S" * 48
    assert captured["payload"]["action"] == "snapshot"


def test_apps_script_pull_fails_safely_on_invalid_json(monkeypatch):
    from backend.services.v2_sheet_sync_service import _read_sheet_apps_script

    monkeypatch.setenv("SHEET_SYNC_SECRET", "S" * 48)
    monkeypatch.setenv(
        "APPS_SCRIPT_WEBAPP_URL",
        "https://script.google.com/macros/s/AKfycbMockDeploy/exec",
    )

    class Response:
        def __enter__(self):
            return self

        def __exit__(self, *args):
            return False

        def read(self, size):
            return b"<html>Authorization required</html>"

    monkeypatch.setattr("urllib.request.urlopen", lambda request, timeout: Response())
    with pytest.raises(SheetSyncError, match="Apps Script no respond"):
        _read_sheet_apps_script(2026, 11)

def test_apps_script_pull_fails_closed_without_secret(monkeypatch):
    from backend.services.v2_sheet_sync_service import _read_sheet_apps_script
    monkeypatch.delenv("SHEET_SYNC_SECRET", raising=False)
    monkeypatch.setenv(
        "APPS_SCRIPT_WEBAPP_URL",
        "https://script.google.com/macros/s/AKfycbMockDeploy/exec",
    )
    with pytest.raises(SheetSyncError, match="SHEET_SYNC_SECRET"):
        _read_sheet_apps_script(2026, 11)


def test_apps_script_pull_rejects_unsafe_urls(monkeypatch):
    from backend.services.v2_sheet_sync_service import _read_sheet_apps_script
    monkeypatch.setenv("SHEET_SYNC_SECRET", "A" * 48)
    monkeypatch.setenv("APPS_SCRIPT_WEBAPP_URL", "https://evil.invalid/macros/s/foo/exec")
    with pytest.raises(SheetSyncError, match="URL"):
        _read_sheet_apps_script(2026, 11)
