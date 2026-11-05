from datetime import date

from backend.services.v2_progress_service import aggregate_progress, _period


def header(id, start, end, spec, state):
    return {
        "id": id, "semana_inicio": date.fromisoformat(start),
        "semana_fin": date.fromisoformat(end), "especialidad": spec,
        "estado": state,
    }


def item(week, oid, finished, hh=2, state="FINALIZADO", backlog=False):
    return {
        "programacion_id": week, "orden_mantenimiento_id": oid,
        "hh_programadas": hh, "finalizado": finished, "anulado": False,
        "estado_cierre": state if finished is not None else "NO_ENCONTRADA",
        "origen_backlog": backlog, "numero_ot": f"OT-{oid}",
        "activo_codigo": "BA-TEST", "plan_clave_software": "1-TEST",
        "especialidad": "MEC",
    }


def test_month_deduplicates_backlog_reprogramming_and_week_keeps_events():
    weeks = [
        header(1, "2026-09-03", "2026-09-09", "MEC", "CERRADA"),
        header(2, "2026-09-10", "2026-09-16", "MEC", "CERRADA"),
    ]
    rows = [
        item(1, 5, False, state="ABIERTO"),
        item(1, 6, True),
        item(2, 5, True, backlog=True),
        item(2, 7, False, state="ABIERTO"),
    ]
    data = aggregate_progress(weeks, rows, 10)
    assert data["weekly_totals"]["programmed"] == 4
    assert data["weekly_totals"]["finalized"] == 2
    assert data["monthly"]["programmed"] == 3
    assert data["monthly"]["finalized"] == 2
    assert data["monthly"]["pending"] == 1
    assert data["monthly"]["not_programmed"] == 7
    assert data["weeks"][1]["origin_backlog"] == 1
    assert data["monthly"]["all_weeks_closed"] is True
    assert [x["numero_ot"] for x in data["unresolved"]] == ["OT-7"]


def test_saved_week_does_not_create_false_finalized_or_pending_results():
    weeks = [header(4, "2026-09-17", "2026-09-23", "ELE", "GUARDADA")]
    rows = [item(4, 9, None, state="")]
    data = aggregate_progress(weeks, rows, 8)
    assert data["weeks"][0]["unchecked"] == 1
    assert data["weeks"][0]["progress_ot_pct"] is None
    assert data["monthly"]["unchecked"] == 1
    assert data["monthly"]["all_weeks_closed"] is False


def test_month_period_validation_and_december_transition():
    assert _period(2026, 12) == (date(2026, 12, 1), date(2027, 1, 1))


def test_annulled_activity_does_not_count_as_pending_or_reduce_compliance():
    weeks = [header(8, "2026-10-01", "2026-10-07", "MEC", "CERRADA")]
    done = item(8, 80, True, hh=2)
    annulled = item(8, 81, None, hh=3, state="ANULADA")
    annulled["anulado"] = True
    data = aggregate_progress(weeks, [done, annulled], 2)
    assert data["weeks"][0]["annulled"] == 1
    assert data["weeks"][0]["pending"] == 0
    assert data["weeks"][0]["not_found"] == 0
    assert data["weeks"][0]["progress_ot_pct"] == 100.0
    assert data["weeks"][0]["progress_hh_pct"] == 100.0
    assert data["weekly_totals"]["progress_ot_pct"] == 100.0
    assert data["weekly_totals"]["progress_hh_pct"] == 100.0
    assert data["monthly"]["annulled"] == 1
    assert data["monthly"]["progress_ot_pct"] == 100.0


def test_unique_scheduled_kpi_reconciles_monthly_and_weekly_counts(monkeypatch):
    """646 asignaciones semanales son 357 OT; cumplimiento programado = 298/357."""
    from backend.services import v2_progress_service as service

    class Result:
        def __init__(self, rows=None, scalar=None):
            self.rows, self.scalar = rows or [], scalar

        def mappings(self):
            return self.rows

        def scalar_one(self):
            return self.scalar

    class Connection:
        def __init__(self):
            self.queries = []

        def __enter__(self):
            return self

        def __exit__(self, exc_type, exc, tb):
            return False

        def execute(self, statement, params):
            sql = str(statement)
            self.queries.append(sql)
            if "monthly_specialty_rows" in sql:
                raise AssertionError("El nombre de la variable no forma parte de SQL")
            if "scheduled_summary AS" in sql:
                assert "COUNT(DISTINCT pi.orden_mantenimiento_id)" in sql
                assert "NOT COALESCE(p.es_operacion,false)" in sql
                return Result([{
                    "especialidad": "ELE", "name": "Eléctrica",
                    "total_ot": 479, "total_hh": 653.56,
                    "completed_ot": 410, "completed_hh": 382.77,
                    "scheduled_completed": 298, "unplanned_completed": 112,
                    "scheduled_unique": 357, "scheduled_assignments": 646,
                }])
            if "count(*) FROM programacion.orden_mantenimiento" in sql:
                return Result(scalar=479)
            return Result()

    conn = Connection()

    class Engine:
        def connect(self):
            return conn

    monkeypatch.setattr(service, "get_engine", lambda: Engine())
    progress = service.get_progress(2026, 10)
    row = progress["monthly_progress_by_specialty"][0]
    assert row["progress_ot_pct"] == 85.6
    assert row["scheduled_progress_ot_pct"] == 83.5
    assert row["completed_ot"] == 410
    assert row["total_ot"] == 479
    assert row["scheduled_completed"] == 298
    assert row["scheduled_unique"] == 357
    assert row["scheduled_assignments"] == 646
    assert row["scheduled_reprogrammed_assignments"] == 289


def test_november_source_status_updates_monthly_specialty_without_closure(monkeypatch):
    from backend.services import v2_progress_service as service

    class Result:
        def __init__(self, rows=None, scalar=None):
            self.rows = rows or []
            self.scalar = scalar

        def mappings(self):
            return self.rows

        def scalar_one(self):
            return self.scalar

    class Connection:
        def __init__(self):
            self.monthly_sql = None

        def __enter__(self):
            return self

        def __exit__(self, exc_type, exc, tb):
            return False

        def execute(self, statement, params):
            sql = str(statement)
            if "scheduled_summary AS" in sql:
                self.monthly_sql = sql
                return Result([{
                    "especialidad": "ELE",
                    "name": "Eléctrica",
                    "total_ot": 445,
                    "total_hh": 577.15,
                    "completed_ot": 71,
                    "completed_hh": 69.86,
                    "scheduled_completed": 0,
                    "unplanned_completed": 0,
                    "source_completed": 71,
                    "scheduled_unique": 0,
                    "scheduled_assignments": 0,
                }])
            if "count(*) FROM programacion.orden_mantenimiento" in sql:
                return Result(scalar=378)
            return Result()

    conn = Connection()

    class Engine:
        def connect(self):
            return conn

    monkeypatch.setattr(service, "get_engine", lambda: Engine())
    progress = service.get_progress(2026, 11)

    electric = progress["monthly_progress_by_specialty"][0]
    assert electric["completed_ot"] == 71
    assert electric["source_completed"] == 71
    assert electric["scheduled_completed"] == 0
    assert electric["progress_ot_pct"] == 16.0
    assert progress["monthly"]["programmed"] == 0
    assert progress["monthly"]["finalized"] == 0  # Cierre formal separado.
    assert "ESTADO_ORIGEN" in conn.monthly_sql
    assert ":begin >= DATE '2026-11-01'" in conn.monthly_sql
    assert "DISTINCT ON (especialidad,orden_mantenimiento_id)" in conn.monthly_sql
