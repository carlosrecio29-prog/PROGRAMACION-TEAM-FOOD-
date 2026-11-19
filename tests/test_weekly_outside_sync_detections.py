from datetime import date, datetime, timezone

import pytest

from backend.services import v2_sheet_sync_service as service


class Result:
    def __init__(self, rows):
        self.rows = rows

    def mappings(self):
        return self

    def __iter__(self):
        return iter(self.rows)


def test_weekly_outside_programming_counts_unique_first_detection(monkeypatch):
    """Count detection week, not a physical execution date or monthly closure."""
    seen = []
    at = datetime(2026, 11, 12, 19, 40, tzinfo=timezone.utc)

    class Connection:
        def execute(self, sql, params):
            query = str(sql)
            seen.append(query)
            assert "DISTINCT ON (c.numero_ot)" in query
            assert "c.accion='OBSERVACION_ORIGEN'" in query
            assert "c.estado_nuevo='FINALIZADA'" in query
            assert "gs.es_operacion=FALSE" in query
            assert "WHERE NOT programada_esta_semana" in query
            assert "MIN(ps.semana_inicio) AS primera_semana_programada" in query
            assert "COALESCE(r.terminado_en,r.iniciado_en)" in query
            assert "AT TIME ZONE 'America/Bogota'" in query
            assert "semana_responsable" in query
            assert "cierre_formal_en" in query
            assert "w.estado <> 'CERRADA'" in query
            assert "UPDATE " not in query and "INSERT " not in query
            assert params == {
                "period": date(2026, 11, 1),
                "spec": "ELE",
                "week_start": date(2026, 11, 12),
                "week_end": date(2026, 11, 18),
            }
            return Result([
                {
                    "numero_ot": "OT-14822-26",
                    "detectado_en": at,
                    "estado_anterior": "PENDIENTE",
                    "sincronizacion_id": 6,
                    "plan_trabajo": "48-RUTINA",
                    "activo_codigo": "BA-SI-SB-AA01",
                    "periodo_origen": date(2026, 11, 1),
                    "area_codigo": "SI",
                    "programada_en_el_mes": False,
                    "primera_semana_programada": None,
                    "total_fuera_semana": 2,
                },
                {
                    "numero_ot": "OT-12898-26",
                    "detectado_en": at,
                    "estado_anterior": "PENDIENTE",
                    "sincronizacion_id": 6,
                    "plan_trabajo": "48-RUTINA",
                    "activo_codigo": "BA-SI-IG-AA25",
                    "periodo_origen": date(2026, 10, 1),
                    "area_codigo": "SI",
                    "programada_en_el_mes": True,
                    "primera_semana_programada": date(2026,11,5),
                    "total_fuera_semana": 2,
                },
            ])

        def __enter__(self):
            return self

        def __exit__(self, *_):
            return False

    class Engine:
        def connect(self):
            return Connection()

    monkeypatch.setattr(service, "get_engine", lambda: Engine())
    result = service.weekly_finalized_outside_programming(
        year=2026, month=11, specialty="ELE",
        week_start=date(2026, 11, 12),
        week_end=date(2026, 11, 18),
    )
    assert result["total"] == 2
    assert result["fuera_del_mes"] == 1
    assert result["programadas_otra_semana"] == 1
    assert result["linea_base"] == 0
    assert result["posteriores_al_corte"] == 0
    assert result["rows"][0]["clasificacion"] == "FUERA_PROGRAMACION_MES"
    assert result["rows"][1]["clasificacion"] == "PROGRAMADA_OTRA_SEMANA"
    assert result["rows"][0]["detectado_en"] == at.isoformat()
    assert result["rows"][0]["programada_alguna_vez"] is False
    assert result["rows"][0]["primera_semana_programada"] is None
    assert result["rows"][1]["programada_alguna_vez"] is True
    assert result["rows"][1]["primera_semana_programada"] == "2026-11-05"
    assert len(seen) == 1


def test_weekly_outside_source_rejects_invalid_week_or_specialty():
    with pytest.raises(service.SheetSyncError, match="rango"):
        service.weekly_finalized_outside_programming(
            year=2026, month=11, specialty="ELE",
            week_start=date(2026, 11, 12),
            week_end=date(2026, 11, 20),
        )
    with pytest.raises(service.SheetSyncError, match="Especialidad"):
        service.weekly_finalized_outside_programming(
            year=2026, month=11, specialty="ALL",
            week_start=date(2026, 11, 12),
            week_end=date(2026, 11, 18),
        )


def test_weekly_outside_old_month_has_no_audit_baseline():
    data = service.weekly_finalized_outside_programming(
        year=2026, month=10, specialty="ELE",
        week_start=date(2026, 10, 8),
        week_end=date(2026, 10, 14),
    )
    assert data["total"] == 0
    assert data["fuente"] == "SIN_HISTORIAL"


def test_weekly_outside_includes_next_day_before_formal_close(monkeypatch):
    """The Nov 19 morning sync belongs to Nov 12-18 while week 2 is open."""
    at = datetime(2026, 11, 19, 11, 4, tzinfo=timezone.utc)

    class Connection:
        def execute(self, sql, params):
            query = str(sql)
            assert "semana_responsable.semana_inicio=:week_start" in query
            assert "w.estado <> 'CERRADA'" in query
            assert "pf.detectado_en <= w.cierre_formal_en" in query
            assert "ORDER BY w.semana_inicio,w.id" in query
            assert params["week_start"] == date(2026, 11, 12)
            assert params["week_end"] == date(2026, 11, 18)
            return Result([{
                "numero_ot": "OT-15151-26",
                "detectado_en": at,
                "estado_anterior": "PENDIENTE",
                "sincronizacion_id": 18,
                "plan_trabajo": "SERVICIO",
                "activo_codigo": "BA-SER-X",
                "periodo_origen": date(2026, 11, 1),
                "area_codigo": "SER",
                "programada_en_el_mes": False,
                "primera_semana_programada": None,
                "posterior_al_corte": True,
                "total_fuera_semana": 1,
            }])

        def __enter__(self):
            return self

        def __exit__(self, *_):
            return False

    class Engine:
        def connect(self):
            return Connection()

    monkeypatch.setattr(service, "get_engine", lambda: Engine())
    result = service.weekly_finalized_outside_programming(
        year=2026, month=11, specialty="SER",
        week_start=date(2026, 11, 12),
        week_end=date(2026, 11, 18),
    )
    assert result["total"] == 1
    assert result["posteriores_al_corte"] == 1
    assert result["fuera_del_mes"] == 1
    assert result["rows"][0]["numero_ot"] == "OT-15151-26"
    assert result["rows"][0]["programada_alguna_vez"] is False
