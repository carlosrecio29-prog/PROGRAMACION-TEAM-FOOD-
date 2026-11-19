"""Regression: the monthly KPI includes validated Google FINALIZADA
without rewriting previously closed weeks or historical orders.
"""
from backend.services import v2_progress_service as service


class _Result:
    def __init__(self, rows=None, scalar=None):
        self.rows = rows or []
        self.value = scalar

    def mappings(self):
        return self

    def __iter__(self):
        return iter(self.rows)

    def scalar_one(self):
        return self.value


def test_monthly_completed_uses_current_verified_google_status_and_historical_protection(monkeypatch):
    queries = []
    monthly = [
        {
            "especialidad": "MEC", "name": "Mecánica",
            "total_ot": 187, "total_hh": 895.89,
            "completed_ot": 89, "completed_hh": 78.88,
            "scheduled_completed": 79, "unplanned_completed": 0,
            "source_completed": 10,
            "scheduled_unique": 135, "scheduled_assignments": 143,
        },
        {
            "especialidad": "SER", "name": "Servicios",
            "total_ot": 73, "total_hh": 184.11,
            "completed_ot": 40, "completed_hh": 76.21,
            "scheduled_completed": 17, "unplanned_completed": 0,
            "source_completed": 23,
            "scheduled_unique": 25, "scheduled_assignments": 25,
        },
    ]

    class FakeConnection:
        def __enter__(self):
            return self

        def __exit__(self, *_):
            return False

        def execute(self, statement, params):
            sql = str(statement)
            queries.append(sql)
            assert "INSERT INTO " not in sql
            assert "UPDATE programacion." not in sql
            if "WITH specs(code,name) AS" in sql:
                assert "source_observed_completed AS" in sql
                assert "gs.estado='FINALIZADA'" in sql
                assert "gs.es_operacion=false" in sql
                assert "upper(btrim(gs.activo_codigo))=upper(btrim(a.codigo))" in sql
                assert "upper(btrim(gs.plan_trabajo))=upper(btrim(o.plan_clave_software))" in sql
                assert "candidate.periodo<=:begin" in sql
                assert ":begin >= DATE '2026-11-01'" in sql
                assert "pi.anulado,false" in sql
                assert "SELECT * FROM source_observed_completed" in sql
                assert "'ESTADO_ORIGEN'::text AS fuente" in sql
                return _Result(rows=monthly)
            if "SELECT count(*) FROM programacion.orden_mantenimiento" in sql:
                return _Result(scalar=0)
            return _Result(rows=[])

    class FakeEngine:
        def connect(self):
            return FakeConnection()

    monkeypatch.setattr(service, "get_engine", FakeEngine)
    output = service.get_progress(2026, 11)
    rows = {item["especialidad"]: item for item in output["monthly_progress_by_specialty"]}
    assert rows["MEC"]["completed_ot"] == 89
    assert rows["MEC"]["source_completed"] == 10
    assert rows["SER"]["total_ot"] == 73
    assert rows["SER"]["completed_ot"] == 40
    assert rows["SER"]["source_completed"] == 23
    assert rows["SER"]["completed_hh"] == 76.21
    assert len(queries) == 5
