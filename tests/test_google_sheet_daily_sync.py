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
    with pytest.raises(SheetSyncError, match="no devolvió JSON"):
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


def test_apps_script_rejected_secret_has_specific_error(monkeypatch):
    import json
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
            return json.dumps({"ok": False, "error": "No autorizado"}).encode("utf-8")

    monkeypatch.setattr("urllib.request.urlopen", lambda request, timeout: Response())
    with pytest.raises(SheetSyncError, match="SHEET_SYNC_SECRET"):
        _read_sheet_apps_script(2026, 11)


def test_apps_script_read_only_probe_does_not_write_db(monkeypatch):
    from backend.services import v2_sheet_sync_service as sync
    monkeypatch.setattr(sync, "_read_sheet_apps_script", lambda year, month: [
        HEADERS,
        source_row(),
        source_row(ot="OT-15002-26", specialty="MEC", status="FINALIZADA"),
    ])
    monkeypatch.setattr(sync, "get_engine", lambda: (_ for _ in ()).throw(
        AssertionError("El diagnóstico no debe abrir conexión con Supabase")
    ))
    status = sync.probe_sheet_source(2026, 11)
    assert status["ok"] is True
    assert status["ots_unicas_validas"] == 2
    assert status["filas"] == 2
    assert status["conflictos"] == 0


def test_apps_script_403_has_permission_guidance(monkeypatch):
    from urllib.error import HTTPError
    from backend.services.v2_sheet_sync_service import _read_sheet_apps_script

    monkeypatch.setenv("SHEET_SYNC_SECRET", "S" * 48)
    monkeypatch.setenv(
        "APPS_SCRIPT_WEBAPP_URL",
        "https://script.google.com/macros/s/AKfycbMockDeploy/exec",
    )

    def forbidden(request, timeout):
        raise HTTPError(request.full_url, 403, "Forbidden", {}, None)

    monkeypatch.setattr("urllib.request.urlopen", forbidden)
    with pytest.raises(SheetSyncError, match="Cualquier persona"):
        _read_sheet_apps_script(2026, 11)


def test_apps_script_missing_property_reports_configuration(monkeypatch):
    import json
    from backend.services.v2_sheet_sync_service import _read_sheet_apps_script

    monkeypatch.setenv("SHEET_SYNC_SECRET", "S" * 48)
    monkeypatch.setenv(
        "APPS_SCRIPT_WEBAPP_URL",
        "https://script.google.com/macros/s/AKfycbMockDeploy/exec",
    )

    class Response:
        def __enter__(self): return self
        def __exit__(self, *args): return False
        def read(self, size):
            return json.dumps({"ok": False, "code": "MISSING_SECRET"}).encode("utf-8")

    monkeypatch.setattr("urllib.request.urlopen", lambda request, timeout: Response())
    with pytest.raises(SheetSyncError, match="no tiene SHEET_SYNC_SECRET"):
        _read_sheet_apps_script(2026, 11)


def test_apps_script_old_generic_response_includes_configuration_hints(monkeypatch):
    import json
    from backend.services.v2_sheet_sync_service import _read_sheet_apps_script

    monkeypatch.setenv("SHEET_SYNC_SECRET", "S" * 48)
    monkeypatch.setenv(
        "APPS_SCRIPT_WEBAPP_URL",
        "https://script.google.com/macros/s/AKfycbMockDeploy/exec",
    )

    class Response:
        def __enter__(self): return self
        def __exit__(self, *args): return False
        def read(self, size):
            return json.dumps({
                "ok": False,
                "error": "Error al leer BASE DE DATOS. Revise las ejecuciones de Apps Script.",
            }).encode("utf-8")

    monkeypatch.setattr("urllib.request.urlopen", lambda request, timeout: Response())
    with pytest.raises(SheetSyncError, match="CEK_API_URL"):
        _read_sheet_apps_script(2026, 11)


def test_push_only_probe_uses_agent_without_google_or_writes(monkeypatch):
    from backend.services import v2_sheet_sync_service as service

    monkeypatch.setattr(service, "_period_today", lambda: date(2026, 11, 1))
    monkeypatch.setattr(service, "_agent_state", lambda conn, period: {
        "agente_activo": True, "fuente_verificada": True,
        "preflight_resumen": {
            "filas": 1320, "unicas": 1280, "repetidas": 40,
            "conflictos": 2, "operaciones": 150,
            "porEspecialidad": {"ELE": 400, "MEC": 400, "MET": 320, "SER": 200},
        },
    })
    monkeypatch.setattr(service, "_read_sheet_apps_script", lambda *args: (
        _ for _ in ()).throw(AssertionError("No se debe llamar Google Web App")
    ))

    class Engine:
        def connect(self):
            class Conn:
                def __enter__(self): return self
                def __exit__(self, *args): return False
                def execute(self, *args): raise AssertionError("Prueba no debe escribir SQL")
            return Conn()

    monkeypatch.setattr(service, "get_engine", lambda: Engine())
    result = service.probe_sheet_source(2026, 11)
    assert result["ok"] is True
    assert result["ots_unicas_validas"] == 1280
    assert result["conflictos"] == 2


def test_manual_sync_creates_pending_request_only_after_agent_check(monkeypatch):
    from backend.services import v2_sheet_sync_service as service

    monkeypatch.setattr(service, "_period_today", lambda: date(2026, 11, 1))
    monkeypatch.setattr(service, "_agent_state", lambda conn, period: {
        "agente_activo": True, "fuente_verificada": True,
    })

    commands = []
    class Result:
        def __init__(self, value): self.value = value
        def scalar(self): return self.value
        def scalar_one(self): return self.value

    class Engine:
        def begin(self):
            class Conn:
                def __enter__(self): return self
                def __exit__(self, *args): return False
                def execute(self, statement, params):
                    q = str(statement)
                    commands.append(q)
                    if "SELECT estado FROM programacion.cierre_mensual_v2" in q:
                        return Result(None)
                    if "INSERT INTO programacion.google_sheet_sync_request_v2" in q:
                        return Result(14)
                    raise AssertionError("SQL inesperado (podría modificar órdenes): " + q)
            return Conn()

    monkeypatch.setattr(service, "get_engine", lambda: Engine())
    result = service.queue_manual_sheet_sync(2026, 11)
    assert result["estado"] == "PENDIENTE"
    assert result["solicitud_id"] == 14
    assert not any("orden_mantenimiento" in q for q in commands)


def test_manual_sync_protects_closed_month_even_with_connected_agent(monkeypatch):
    from backend.services import v2_sheet_sync_service as service
    monkeypatch.setattr(service, "_period_today", lambda: date(2026, 11, 1))

    class Result:
        def scalar(self): return "CERRADO"

    class Engine:
        def begin(self):
            class Conn:
                def __enter__(self): return self
                def __exit__(self, *args): return False
                def execute(self, statement, params): return Result()
            return Conn()

    monkeypatch.setattr(service, "get_engine", lambda: Engine())
    with pytest.raises(SheetSyncError, match="cerrado"):
        service.queue_manual_sheet_sync(2026, 11)


def test_manual_sync_forbids_prior_month_even_if_agent_ready(monkeypatch):
    from backend.services import v2_sheet_sync_service as service
    monkeypatch.setattr(service, "_period_today", lambda: date(2026, 11, 1))
    with pytest.raises(SheetSyncError, match="mes actual"):
        service.queue_manual_sheet_sync(2026, 10)


def test_recently_ended_unclosed_week_is_eligible_for_sheet_tracking():
    """The 5–11 Nov week must remain eligible on 12 Nov until formally closed."""
    from backend.services.v2_sheet_sync_service import _week_snapshots

    seen = []

    class Results:
        def __init__(self, rows):
            self.rows = rows

        def scalars(self):
            return self

        def all(self):
            return self.rows

        def mappings(self):
            return self

    class FakeConn:
        def execute(self, sql, params):
            query = str(sql)
            seen.append((query, params))
            if "SELECT id FROM programacion.programacion_semanal_v2" in query:
                assert "semana_fin >= (:today - INTERVAL '7 days')" in query
                assert "estado <> 'CERRADA'" in query
                assert params["today"] == date(2026, 11, 12)
                return Results([49])
            if "FROM programacion.programacion_item_v2 pi" in query:
                assert params["week"] == 49
                return Results([])
            raise AssertionError("Unexpected query against the live database")

    # Empty programming items mean no snapshot write during this test.
    written = _week_snapshots(FakeConn(), date(2026, 11, 1),
                              date(2026, 11, 12), {}, "MANUAL")
    assert written == 0
    assert len(seen) == 2


def test_finalized_outside_monthly_programming_is_read_only(monkeypatch):
    from backend.services import v2_sheet_sync_service as service

    queries = []

    class FakeMappingResult:
        def mappings(self):
            return self

        def __iter__(self):
            return iter([
                {
                    "numero_ot": "OT-10810-26", "plan_trabajo": "RUTINA",
                    "activo_codigo": "BA-JB-001", "area_codigo": "JB",
                    "observado_en": None,
                    "periodo_origen": date(2026, 11, 1),
                    "backlog_id": None, "backlog_estado": None,
                    "total_fuera": 2,
                },
                {
                    "numero_ot": "OT-16027-25", "plan_trabajo": "PLAN HEREDADO",
                    "activo_codigo": "BA-JB-002", "area_codigo": "JB",
                    "observado_en": None,
                    "periodo_origen": date(2026, 9, 1),
                    "backlog_id": 15, "backlog_estado": "FINALIZADA",
                    "total_fuera": 2,
                },
            ])

    class Connection:
        def __enter__(self):
            return self

        def __exit__(self, *args):
            return False

        def execute(self, statement, params):
            sql = str(statement)
            queries.append(sql)
            assert "gs.estado='FINALIZADA' AND gs.es_operacion=false" in sql
            assert "NOT EXISTS" in sql
            assert "programacion.programacion_item_v2" in sql
            assert "SELECT" in sql and "UPDATE " not in sql and "INSERT " not in sql
            assert params == {"period": date(2026,11,1), "spec": "ELE"}
            return FakeMappingResult()

    class Engine:
        def connect(self):
            return Connection()

    monkeypatch.setattr(service, "get_engine", lambda: Engine())
    result = service.finalized_outside_monthly_programming(
        year=2026, month=11, specialty="ELE"
    )
    assert result["total"] == 2
    assert result["del_mes"] == 1
    assert result["arrastre"] == 1
    assert result["sin_maestro"] == 0
    assert result["rows"][1]["es_backlog"] is True
    assert result["rows"][1]["periodo_origen"] == "2026-09-01"
    assert result["recortado"] is False
    assert len(queries) == 1


def test_finalized_outside_monthly_programming_rejects_invalid_spec():
    from backend.services.v2_sheet_sync_service import (
        finalized_outside_monthly_programming,
    )
    with pytest.raises(SheetSyncError, match="Especialidad inválida"):
        finalized_outside_monthly_programming(year=2026,month=11,specialty="ALL")


def test_historical_finalized_matches_only_previous_month_equipment_plan():
    from backend.services.v2_sheet_sync_service import (
        _validate_historical_source, _compatible_historical_source,
    )
    historical = _validate_historical_source([
        {
            "numero_ot":"OT-12907-26", "especialidad":"ELE",
            "activo_codigo":"BA-SI-IG-AA28",
            "plan_trabajo":"48-RUTINA DE MANTENIMIENTO DE REFRIGERACION",
            "estado":"FINALIZADA","anio_fuente":2026,"mes_fuente":10,
        },
        {
            "numero_ot":"OT-12914-26", "especialidad":"ELE",
            "activo_codigo":"BA-SI-IG-AA38",
            "plan_trabajo":"48-RUTINA DE MANTENIMIENTO DE REFRIGERACION",
            "estado":"FINALIZADA","anio_fuente":2026,"mes_fuente":10,
        },
        {
            "numero_ot":"OT-8232-26", "especialidad":"ELE",
            "activo_codigo":"BA-SI-EC-CL04",
            "plan_trabajo":"135-RUTINA TRIMESTRAL PREVENTIVA (REALIZADO POR CONTRATISTA BOSCH)",
            "estado":"FINALIZADA","anio_fuente":2026,"mes_fuente":10,
        },
        {
            "numero_ot":"OT-13187-26","especialidad":"ELE",
            "activo_codigo":"BA-SI-IG-MO01",
            "plan_trabajo":"44-OPERACIÓN - RUTINA ELÉCTRICA SEMESTRAL MOTOR",
            "estado":"FINALIZADA","anio_fuente":2026,"mes_fuente":10,
        },
        {
            "numero_ot":"OT-50000-26","especialidad":"ELE",
            "activo_codigo":"BA-SI-IG-AA50",
            "plan_trabajo":"48-RUTINA DE MANTENIMIENTO DE REFRIGERACION",
            "estado":"FINALIZADA","anio_fuente":2026,"mes_fuente":11,
        },
    ], date(2026,11,1))
    assert set(historical) == {
        "OT-12907-26", "OT-12914-26", "OT-8232-26",
    }
    item = {
        "order_period":date(2026,10,1),
        "plan_operation":False,
        "specialty":"ELE",
        "activo_codigo":"BA-SI-IG-AA28",
        "plan_clave_software":"48-RUTINA DE MANTENIMIENTO DE REFRIGERACION",
    }
    assert _compatible_historical_source(item,historical["OT-12907-26"],date(2026,11,1))
    assert not _compatible_historical_source({**item,"activo_codigo":"BA-SI-IG-AA99"},historical["OT-12907-26"],date(2026,11,1))
    assert not _compatible_historical_source({**item,"order_period":date(2026,11,1)},historical["OT-12907-26"],date(2026,11,1))
    assert not _compatible_historical_source({**item,"plan_operation":True},historical["OT-12907-26"],date(2026,11,1))


def test_historical_source_counts_in_open_week_without_changing_closed_orders():
    from backend.services.v2_sheet_sync_service import (
        _validate_historical_source,_week_snapshots,
    )
    prior = _validate_historical_source([{
        "numero_ot":"OT-12907-26", "especialidad":"ELE",
        "activo_codigo":"BA-SI-IG-AA28",
        "plan_trabajo":"48-RUTINA DE MANTENIMIENTO DE REFRIGERACION",
        "estado":"FINALIZADA","anio_fuente":2026,"mes_fuente":10,
    }],date(2026,11,1))
    submitted = []
    queries = []

    class Result:
        def __init__(self,rows=None,scalar_value=None):
            self.rows=rows or []
            self.value=scalar_value
        def scalars(self): return self
        def mappings(self): return self
        def all(self): return self.rows
        def first(self): return self.rows[0] if self.rows else None
        def scalar_one(self): return self.value
        def __iter__(self): return iter(self.rows)

    class FakeConn:
        def execute(self,statement,params=None):
            sql=str(statement)
            queries.append(sql)
            if "SELECT id FROM programacion.programacion_semanal_v2" in sql:
                assert "estado <> 'CERRADA'" in sql
                return Result(rows=[50])
            if "FROM programacion.programacion_item_v2 pi" in sql:
                return Result(rows=[{
                    "item_id":4728,"orden_mantenimiento_id":5483,
                    "hh_programadas":2.0,"numero_ot":"OT-12907-26",
                    "order_period":date(2026,10,1),"specialty":"ELE",
                    "activo_codigo":"BA-SI-IG-AA28",
                    "plan_clave_software":"48-RUTINA DE MANTENIMIENTO DE REFRIGERACION",
                    "plan_operation":False,
                    "area_codigo":"SI","area_nombre":"SERVICIO",
                    "manual_status":None,
                }])
            if "SELECT id,archivo_nombre" in sql:
                return Result(rows=[])
            if "SELECT DISTINCT si.orden_mantenimiento_id" in sql:
                return Result(rows=[])
            if "INSERT INTO programacion.seguimiento_semanal_v2" in sql:
                assert params["done"] == 1
                assert params["hh_done"] == 2.0
                return Result(scalar_value=88)
            if "INSERT INTO programacion.seguimiento_semanal_item_v2" in sql:
                submitted.extend(params)
                return Result()
            raise AssertionError("Unexpected SQL: "+sql[:150])

    assert _week_snapshots(FakeConn(),date(2026,11,1),
                           date(2026,11,12),{}, "MANUAL",prior) == 1
    assert len(submitted)==1
    assert submitted[0]["status"]=="FINALIZADA"
    assert submitted[0]["final"] is True
    assert submitted[0]["match"]=="GOOGLE_SHEETS_HISTORICO"
    assert not any("UPDATE programacion.orden_mantenimiento" in q for q in queries)
    assert not any("UPDATE programacion.programacion_item_v2" in q for q in queries)
    assert not any("UPDATE programacion.cierre_mensual_v2" in q for q in queries)


def test_current_month_source_takes_precedence_over_historical_status():
    from backend.services.v2_sheet_sync_service import (
        _validate_historical_source, _week_snapshots,
    )
    prior=_validate_historical_source([{
        "numero_ot":"OT-12907-26","especialidad":"ELE",
        "activo_codigo":"BA-SI-IG-AA28",
        "plan_trabajo":"48-RUTINA DE MANTENIMIENTO DE REFRIGERACION",
        "estado":"FINALIZADA","anio_fuente":2026,"mes_fuente":10,
    }],date(2026,11,1))
    class Result:
        def __init__(self,rows=None): self.rows=rows or []
        def scalars(self): return self
        def mappings(self): return self
        def all(self): return self.rows
        def first(self): return self.rows[0] if self.rows else None
        def __iter__(self): return iter(self.rows)
    class Conn:
        def __init__(self): self.values=[]
        def execute(self,sql,params=None):
            q=str(sql)
            if "SELECT id FROM programacion.programacion_semanal_v2" in q:
                return Result(rows=[50])
            if "FROM programacion.programacion_item_v2 pi" in q:
                return Result(rows=[{
                    "item_id":1,"orden_mantenimiento_id":2,"hh_programadas":1,
                    "numero_ot":"OT-12907-26","order_period":date(2026,10,1),
                    "specialty":"ELE","activo_codigo":"BA-SI-IG-AA28",
                    "plan_clave_software":"48-RUTINA DE MANTENIMIENTO DE REFRIGERACION",
                    "plan_operation":False,"area_codigo":"SI",
                    "area_nombre":"SERVICIO","manual_status":None,
                }])
            if "SELECT id,archivo_nombre" in q: return Result(rows=[])
            if "SELECT DISTINCT si.orden_mantenimiento_id" in q: return Result(rows=[])
            if "INSERT INTO programacion.seguimiento_semanal_v2" in q:
                assert params["done"]==0
                assert params["pending"]==1
                return type("R",(),{"scalar_one":lambda _:7})()
            if "INSERT INTO programacion.seguimiento_semanal_item_v2" in q:
                self.values.extend(params)
                return Result()
            raise AssertionError("Unexpected SQL")
    conn=Conn()
    _week_snapshots(conn,date(2026,11,1),date(2026,11,12),{
       "OT-12907-26":{"estado":"PENDIENTE","operation":False}
    },"MANUAL",prior)
    assert conn.values[0]["status"]=="PENDIENTE"
    assert conn.values[0]["final"] is False
    assert conn.values[0]["match"]=="GOOGLE_SHEETS_BASE_DE_DATOS"
