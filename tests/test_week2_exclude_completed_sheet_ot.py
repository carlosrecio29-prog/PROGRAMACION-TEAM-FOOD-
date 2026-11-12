from datetime import date

import pytest

from backend.services import v2_programming_runtime as service
from backend.services.v2_programming_service import V2ProgrammingError


class Result:
    def __init__(self, one=None, rows=None):
        self.one = one
        self.rows = rows or []
    def mappings(self):
        return self
    def scalars(self):
        return self
    def first(self):
        return self.one
    def all(self):
        return self.rows


def test_week2_reconciliation_counts_finalized_outside_sheets(monkeypatch):
    """A closed prior week enables a source-based off-program count.

    This is a current-month observation, not a retroactive weekly execution.
    """
    class FakeConn:
        def execute(self, sql, params):
            query=str(sql)
            assert "programacion.google_sheet_ot_estado_v2 gs" in query
            assert "gs.estado='FINALIZADA'" in query
            assert "gs.es_operacion=false" in query
            assert "upper(btrim(gs.activo_codigo))=upper(btrim(a.codigo))" in query
            assert "upper(btrim(gs.plan_trabajo))=upper(btrim(o.plan_clave_software))" in query
            assert "prior_week.estado='CERRADA'" in query
            assert "NOT EXISTS" in query
            assert "scheduled_week.especialidad=:specialty" in query
            assert params == {"week_start":date(2026,11,12),"specialty":"ELE"}
            return Result(one={
                "initial_count":460,"finalized_programmed_count":33,
                "annulled_count":0,"finalized_unplanned_count":161,
                "remaining_count":266,"external_executed_count":2,
            })
    result=service._reconcile_weekly_pending(FakeConn(),date(2026,11,12),"ELE")
    assert result["finalized_unplanned_count"]==161
    assert result["remaining_count"]==266
    assert result["initial_count"]==460


def test_week2_saving_already_finalized_source_order_is_blocked(monkeypatch):
    """UI filtering must not be bypassable by submitting the order ID."""
    executed = []

    class FakeConnection:
        def execute(self, sql, params=None):
            query=str(sql)
            executed.append(query)
            if "SELECT id,estado FROM programacion.programacion_semanal_v2" in query:
                return Result(one=None)
            if "SELECT DISTINCT o.numero_ot" in query and "google_sheet_ot_estado_v2 gs" in query:
                if "LEFT JOIN programacion.plan_trabajo p" in query:
                    return Result(rows=[])
                assert "gs.estado='FINALIZADA'" in query
                assert "gs.es_operacion=false" in query
                assert "prior_week.estado='CERRADA'" in query
                assert "upper(btrim(gs.activo_codigo))=upper(btrim(a.codigo))" in query
                assert "upper(btrim(gs.plan_trabajo))=upper(btrim(o.plan_clave_software))" in query
                assert params["ids"] == [10005]
                return Result(rows=["OT-15000-26"])
            raise AssertionError("Blocked order must not reach any write: "+query[:130])
        def __enter__(self):
            return self
        def __exit__(self, *_):
            return False

    class Engine:
        def begin(self):
            return FakeConnection()

    monkeypatch.setattr(service,"get_engine",Engine)
    monkeypatch.setattr(service,"_capacity",lambda *_:{"target":150})
    with pytest.raises(V2ProgrammingError,match="OT-15000-26.*FINALIZADA"):
        service.save_week_programming(
            date_from=date(2026,11,12),
            date_to=date(2026,11,18),
            specialty="ELE",
            order_ids=[10005],
        )
    assert len(executed)==3
    assert not any("INSERT INTO programacion." in x or "UPDATE programacion." in x for x in executed)
