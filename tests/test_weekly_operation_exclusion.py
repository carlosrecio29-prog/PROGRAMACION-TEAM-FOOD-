from datetime import date

import pytest

from backend.services import v2_programming_runtime as runtime
from backend.services.v2_programming_service import V2ProgrammingError


class _Result:
    def __init__(self, row=None, orders=None):
        self.row = row
        self.orders = orders or []

    def mappings(self):
        return self

    def first(self):
        return self.row

    def scalars(self):
        return self

    def all(self):
        return self.orders


def test_operation_from_google_is_rejected_on_week_save(monkeypatch):
    """Master may say non-OPERACIÓN, but current source is authoritative."""
    calls = []

    class FakeConnection:
        def execute(self, sql, params=None):
            query = str(sql)
            calls.append(query)
            if "SELECT id,estado FROM programacion.programacion_semanal_v2" in query:
                return _Result(row={"id": 50, "estado": "GUARDADA"})
            if "SELECT DISTINCT o.numero_ot" in query:
                assert "google_sheet_ot_estado_v2" in query
                assert "operacion_exclusion_detalle_v2" in query
                assert "gs.es_operacion=true" in query
                assert "ex.motivo='OPERACION'" in query
                assert params["ids"] == [5985]
                return _Result(orders=["OT-13187-26"])
            raise AssertionError("Guard should stop any further write, got: " + query[:140])

        def __enter__(self):
            return self

        def __exit__(self, exc_type, exc, tb):
            return False

    class FakeEngine:
        def begin(self):
            return FakeConnection()

    monkeypatch.setattr(runtime, "get_engine", FakeEngine)
    monkeypatch.setattr(runtime, "_capacity", lambda *_: {"target": 20})
    with pytest.raises(V2ProgrammingError, match="OT-13187-26.*OPERACIÓN"):
        runtime.save_week_programming(
            date_from=date(2026, 11, 5),
            date_to=date(2026, 11, 11),
            specialty="ELE",
            order_ids=[5985],
        )
    assert len(calls) == 2
    assert not any("UPDATE programacion." in q or "INSERT INTO programacion." in q for q in calls)


def test_closed_week_stays_immutable_before_operation_check(monkeypatch):
    """Already-approved closures must never be resaved or altered."""

    class FakeConnection:
        def execute(self, sql, params=None):
            query = str(sql)
            if "SELECT id,estado FROM programacion.programacion_semanal_v2" in query:
                return _Result(row={"id": 48, "estado": "CERRADA"})
            raise AssertionError("Closed-week check should stop all remaining queries")

        def __enter__(self):
            return self

        def __exit__(self, exc_type, exc, tb):
            return False

    class FakeEngine:
        def begin(self):
            return FakeConnection()

    monkeypatch.setattr(runtime, "get_engine", FakeEngine)
    monkeypatch.setattr(runtime, "_capacity", lambda *_: {"target": 20})
    with pytest.raises(V2ProgrammingError, match="ya fue cerrada"):
        runtime.save_week_programming(
            date_from=date(2026, 10, 29),
            date_to=date(2026, 11, 4),
            specialty="ELE",
            order_ids=[5985],
        )
