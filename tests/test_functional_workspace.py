"""Behavioral regressions for terminal orders and the management workspace.

The SELECTs below run against an isolated relational fixture. PostgreSQL writes
are captured so these tests cannot touch an external database.
"""
import sqlite3
from datetime import date, timedelta
from contextlib import nullcontext

import pytest

from backend.services import v2_backlog_service as backlog
from backend.services import v2_week_tracking_service as tracking
from backend.services import v2_programming_runtime as programming
from backend.services.v2_portfolio_service import aggregate_portfolio, get_management_insights, get_portfolio


class Result:
    def __init__(self, rows):
        self.rows = rows

    def mappings(self):
        return self

    def __iter__(self):
        return iter(self.rows)

    def one(self):
        assert len(self.rows) == 1
        return self.rows[0]

    def scalar_one(self):
        return next(iter(self.one().values()))

    def first(self):
        return self.rows[0] if self.rows else None

    def all(self):
        return self.rows

    def scalars(self):
        return self


class RelationalConnection:
    def __init__(self, db):
        self.db = db
        self.writes = []

    def execute(self, statement, params=None):
        sql = str(statement)
        if sql.lstrip().upper().startswith(("SELECT", "WITH")):
            # Dialect-only conversion: the predicates, joins, filters and
            # aggregations remain the production query under test.
            sql = sql.replace(" ILIKE ", " LIKE ").replace("::int", "")
            sql = sql.replace("(CURRENT_TIMESTAMP AT TIME ZONE 'America/Bogota')::date", "CURRENT_DATE")
            sql = sql.replace("CURRENT_DATE-COALESCE(b.primera_semana_origen_inicio,b.semana_origen_inicio)",
                              "CAST(julianday(CURRENT_DATE)-julianday(COALESCE(b.primera_semana_origen_inicio,b.semana_origen_inicio)) AS INTEGER)")
            sql = sql.replace("CURRENT_DATE", "fixture_today()")
            bound = {key: value.isoformat() if isinstance(value, date) else value
                     for key, value in (params or {}).items()}
            return Result([dict(row) for row in self.db.execute(sql, bound)])
        self.writes.append((sql, params))
        return Result([])


class BooleanAnd:
    def __init__(self):
        self.value = True

    def step(self, value):
        self.value = self.value and bool(value)

    def finalize(self):
        return self.value


@pytest.fixture
def relational_backlog():
    db = sqlite3.connect(":memory:")
    db.row_factory = sqlite3.Row
    db.create_function("GREATEST", -1, max)
    db.create_function("btrim", 1, lambda value: value.strip() if value else value)
    db.create_function("concat_ws", -1, lambda separator, *parts: separator.join(str(x) for x in parts if x is not None))
    db.create_aggregate("bool_and", 1, BooleanAnd)
    # Freeze database time so boundary tests do not depend on host/UTC midnight.
    db.create_function("fixture_today", 0, lambda: "2026-10-22")
    db.execute("ATTACH DATABASE ':memory:' AS programacion")
    db.executescript("""
        CREATE TABLE programacion.activo(id INTEGER PRIMARY KEY, codigo TEXT, area_codigo TEXT);
        CREATE TABLE programacion.plan_trabajo(id INTEGER PRIMARY KEY, es_operacion BOOLEAN);
        CREATE TABLE programacion.orden_mantenimiento(
          id INTEGER PRIMARY KEY, numero_ot TEXT, estado TEXT, plan_clave_software TEXT,
          activo_id INTEGER, plan_trabajo_id INTEGER);
        CREATE TABLE programacion.backlog_v2(
          id INTEGER PRIMARY KEY, orden_mantenimiento_id INTEGER,
          especialidad TEXT, estado_seguimiento TEXT);
        INSERT INTO programacion.activo VALUES(1,'EQ-1','ENV');
        INSERT INTO programacion.plan_trabajo VALUES(1,false),(2,true);
        ALTER TABLE programacion.activo ADD COLUMN descripcion TEXT DEFAULT 'Bomba';
        ALTER TABLE programacion.activo ADD COLUMN criticidad TEXT DEFAULT 'A';
        ALTER TABLE programacion.plan_trabajo ADD COLUMN plan_trabajo TEXT DEFAULT 'Rutina';
        ALTER TABLE programacion.plan_trabajo ADD COLUMN numero_personas_efectivo INTEGER DEFAULT 2;
        ALTER TABLE programacion.plan_trabajo ADD COLUMN tiempo_ejecucion_min INTEGER DEFAULT 60;
        ALTER TABLE programacion.orden_mantenimiento ADD COLUMN titulo TEXT;
        ALTER TABLE programacion.orden_mantenimiento ADD COLUMN tiempo_planeado_min INTEGER;
        ALTER TABLE programacion.orden_mantenimiento ADD COLUMN periodo DATE DEFAULT '2026-10-01';
        ALTER TABLE programacion.orden_mantenimiento ADD COLUMN especialidad TEXT DEFAULT 'MEC';
        ALTER TABLE programacion.backlog_v2 ADD COLUMN motivo TEXT DEFAULT 'ARRASTRE INICIAL';
        ALTER TABLE programacion.backlog_v2 ADD COLUMN primera_semana_origen_inicio DATE;
        ALTER TABLE programacion.backlog_v2 ADD COLUMN semana_origen_inicio DATE;
        CREATE TABLE programacion.operacion_exclusion_detalle_v2(periodo DATE);
        INSERT INTO programacion.operacion_exclusion_detalle_v2 VALUES('2026-10-01'),('2026-10-01'),('2026-09-01');
        CREATE TABLE programacion.operacion_exclusion_periodo_v2(periodo DATE,cantidad INTEGER);
        INSERT INTO programacion.operacion_exclusion_periodo_v2 VALUES('2026-10-01',9),('2026-11-01',3);
    """)
    examples = [
        (1, "PENDIENTE_DISPONIBLE", "PENDIENTE", 1),
        (2, "PENDIENTE_PROGRAMADA", "PENDIENTE", 1),
        (3, "ANULADA", "ANULADA", 1),
        (4, "PENDIENTE_DISPONIBLE", "ANULADO", 1),
        (5, "FINALIZADA", "FINALIZADO", 1),
        (6, "PENDIENTE_DISPONIBLE", "PENDIENTE", 2),
    ]
    database_today = date.fromisoformat(db.execute("SELECT fixture_today()").fetchone()[0])
    for oid, state, source_state, plan in examples:
        db.execute("INSERT INTO programacion.orden_mantenimiento(id,numero_ot,estado,plan_clave_software,activo_id,plan_trabajo_id) VALUES(?,?,?,?,?,?)",
                   (oid, f"OT-{oid}", source_state, "10-RUTINA", 1, plan))
        db.execute("INSERT INTO programacion.backlog_v2(id,orden_mantenimiento_id,especialidad,estado_seguimiento,semana_origen_inicio) VALUES(?,?,?,?,?)",
                   (oid, oid, "MEC", state, (database_today - timedelta(days=10 if oid == 1 else 40)).isoformat()))
    yield RelationalConnection(db)
    db.close()


def test_default_backlog_omits_annulled_tracking_and_annulled_source(relational_backlog):
    where, params = backlog._build_backlog_filters(specialty="mec", area="ENV")
    rows = relational_backlog.db.execute(f"""
        SELECT b.id FROM programacion.backlog_v2 b
        JOIN programacion.orden_mantenimiento o ON o.id=b.orden_mantenimiento_id
        JOIN programacion.activo a ON a.id=o.activo_id
        LEFT JOIN programacion.plan_trabajo p ON p.id=o.plan_trabajo_id
        WHERE {where} AND COALESCE(p.es_operacion,false)=false
        ORDER BY b.id
    """, params)
    assert [row[0] for row in rows] == [1, 2]


def test_annulled_backlog_remains_queryable_as_history(relational_backlog):
    where, params = backlog._build_backlog_filters(state="anulada")
    rows = relational_backlog.db.execute(f"""
        SELECT b.id FROM programacion.backlog_v2 b
        JOIN programacion.orden_mantenimiento o ON o.id=b.orden_mantenimiento_id
        WHERE {where} ORDER BY b.id
    """, params)
    assert [row[0] for row in rows] == [3]


def test_calendar_reconciliation_cannot_finalize_terminal_or_operation_orders(relational_backlog):
    # Even a later source file claiming completion must not reactivate a
    # previously annulled order or reconcile operational exclusions.
    calendar = [{"numero_ot": f"OT-{oid}", "activo": "EQ-1", "plan": "10-RUTINA",
                 "estado": "FINALIZADO"} for oid in range(1, 7)]
    result = tracking._reconcile_backlog_from_calendar(
        relational_backlog, specialty="mec", calendar_rows=calendar, recorded_by="qa-fixture",
    )
    assert result["revisadas"] == 2
    assert result["finalizadas"] == 2
    assert set(result["finalizadas_ots"]) == {"OT-1", "OT-2"}
    source_updates = [params for sql, params in relational_backlog.writes
                      if "UPDATE programacion.orden_mantenimiento" in sql]
    assert source_updates
    assert {row["order_id"] for payload in source_updates for row in payload} == {1, 2}


def test_backlog_rejects_inverted_age_range_before_database_access(monkeypatch):
    def forbidden_database():
        pytest.fail("Invalid filters must be rejected before opening a database connection")
    monkeypatch.setattr(backlog, "get_engine", forbidden_database)
    with pytest.raises(ValueError, match="antigüedad mínima"):
        backlog.get_accumulated_backlog(age_min=91, age_max=30)


def portfolio_order(oid, *, specialty="MEC", hh=2, pmp=True, backlog=False,
                    scheduled=False, unplanned=False):
    return {"order_id": oid, "especialidad": specialty, "hh": hh,
            "is_pmp": pmp, "is_backlog": backlog, "finished": scheduled or unplanned,
            "scheduled_finished": scheduled, "unplanned_finished": unplanned}


def test_portfolio_does_not_double_count_pmp_that_also_exists_in_backlog():
    result = aggregate_portfolio([
        portfolio_order(1, pmp=True, backlog=True, scheduled=True, hh=3),
        portfolio_order(2, pmp=False, backlog=True, unplanned=True, hh=1.5),
        portfolio_order(3, specialty="ELE", hh=None),
    ], latest_tracking_at="2026-10-22T20:00:00")
    total = result["tracking_progress"]
    assert total["total_orders"] == 3
    assert total["pmp_orders"] == 2
    assert total["backlog_orders"] == 1
    assert total["finalized_orders"] == 2
    assert total["pending_orders"] == 1
    assert total["progress_pct"] == 66.7
    assert total["scheduled_finalized_orders"] == 1
    assert total["unplanned_finalized_orders"] == 1
    assert total["total_workload_hh"] == 4.5
    assert total["finalized_workload_hh"] == 4.5
    assert total["progress_hh_pct"] == 100.0
    assert total["latest_tracking_at"] == "2026-10-22T20:00:00"
    specialties = {row["especialidad"]: row for row in result["portfolio_progress_by_specialty"]}
    assert specialties["MEC"]["progress_pct"] == 100.0
    assert specialties["ELE"]["progress_pct"] == 0.0
    for field in ("total_orders", "finalized_orders", "pending_orders", "pmp_orders", "backlog_orders",
                  "total_workload_hh", "finalized_workload_hh"):
        assert sum(row[field] for row in specialties.values()) == total[field]


def test_empty_portfolio_keeps_specialties_and_finite_percentages():
    result = aggregate_portfolio([])
    assert {row["especialidad"] for row in result["portfolio_progress_by_specialty"]} == {"MEC", "ELE", "MET", "SER"}
    assert result["tracking_progress"]["progress_pct"] == 0.0
    assert result["tracking_progress"]["progress_hh_pct"] == 0.0
    assert all(row["total_orders"] == 0 for row in result["portfolio_progress_by_specialty"])


def test_unknown_specialty_is_preserved_in_totals_without_assigning_mechanical():
    result = aggregate_portfolio([portfolio_order(1, specialty=None, hh=1.5, scheduled=True)])
    specialties = {row["especialidad"]: row for row in result["portfolio_progress_by_specialty"]}
    assert specialties["SIN"]["name"] == "Sin especialidad"
    assert specialties["SIN"]["finalized_orders"] == 1
    assert specialties["MEC"]["total_orders"] == 0
    assert result["tracking_progress"]["finalized_workload_hh"] == 1.5


def test_scheduled_and_unplanned_observation_do_not_duplicate_total_completion():
    result = aggregate_portfolio([portfolio_order(1, scheduled=True, unplanned=True)])
    assert result["tracking_progress"]["total_orders"] == 1
    assert result["tracking_progress"]["finalized_orders"] == 1
    assert result["tracking_progress"]["progress_pct"] == 100.0


def test_global_summary_separates_history_active_and_excluded_orders(relational_backlog):
    result = backlog._get_backlog_summary(relational_backlog)
    assert result["movidas"] == 5
    assert result["finalizadas_por_ingeniero"] == 1
    assert result["anuladas"] == 1
    assert result["pendientes_activas"] == 2
    assert result["disponibles"] == 1
    assert result["programadas"] == 1
    assert result["hh_backlog_activo"] == 4.0


@pytest.mark.parametrize("filters,expected", [
    ({"specialty": "ele"}, 0),
    ({"specialty": "mec", "area": "ENV"}, 2),
    ({"state": "PENDIENTE_PROGRAMADA"}, 1),
    ({"search": "OT-1"}, 1),
    ({"age_min": 31, "age_max": 60}, 1),
    ({"area": "ENV", "age_max": 30, "search": "Bomba"}, 1),
])
def test_filtered_summary_uses_all_requested_filters(relational_backlog, filters, expected):
    where, params = backlog._build_backlog_filters(**filters)
    result = backlog._get_backlog_summary(relational_backlog, where=where, params=params)
    assert result["movidas"] == expected
    assert result["pendientes_activas"] == expected


def test_management_insights_use_current_backlog_and_selected_period_exclusions(relational_backlog):
    result = get_management_insights(relational_backlog, date(2026, 10, 1),
                                     {"missing_hh_count": 7, "unknown_completion_date_count": 3})
    assert result["period"] == "2026-10-01"
    assert result["as_of"] == "2026-10-22"
    assert result["scope"] == "CARTERA_PERIODO_Y_BACKLOG_ACTUAL"
    assert result["operation_excluded_count"] == 2
    assert result["missing_hh_count"] == 7
    assert result["unknown_completion_date_count"] == 3
    queue = result["backlog"]
    assert queue["scope"] == "BACKLOG_ACTIVO_ACTUAL"
    assert queue["active_count"] == queue["available_count"] + queue["scheduled_count"] == 2
    assert queue["critical_a_count"] == 2
    assert queue["aging_buckets"] == {"up_to_30": 1, "days_31_60": 1, "days_61_90": 0, "over_90": 0}


def test_operation_exclusions_fall_back_to_period_totals_without_adding_duplicate_sources(relational_backlog):
    portfolio = {"missing_hh_count": 0, "unknown_completion_date_count": 0}
    detailed = get_management_insights(relational_backlog, date(2026,10,1), portfolio)
    fallback = get_management_insights(relational_backlog, date(2026,11,1), portfolio)
    empty = get_management_insights(relational_backlog, date(2026,12,1), portfolio)
    assert detailed["operation_excluded_count"] == 2  # Not 2 + 9.
    assert fallback["operation_excluded_count"] == 3
    assert empty["operation_excluded_count"] == 0


@pytest.mark.parametrize("age,bucket", [(-5,"up_to_30"), (0,"up_to_30"), (30,"up_to_30"),
    (31,"days_31_60"), (60,"days_31_60"), (61,"days_61_90"), (90,"days_61_90"), (91,"over_90")])
def test_backlog_age_buckets_cover_boundaries_once(relational_backlog, age, bucket):
    db = relational_backlog.db
    today = date.fromisoformat(db.execute("SELECT fixture_today()").fetchone()[0])
    db.execute("UPDATE programacion.backlog_v2 SET estado_seguimiento='FINALIZADA' WHERE id=2")
    db.execute("UPDATE programacion.backlog_v2 SET primera_semana_origen_inicio=? WHERE id=1",
               ((today - timedelta(days=age)).isoformat(),))
    result = get_management_insights(relational_backlog, date(2026,10,1),
                                     {"missing_hh_count": 0, "unknown_completion_date_count": 0})
    counts = result["backlog"]["aging_buckets"]
    assert counts[bucket] == 1
    assert sum(counts.values()) == result["backlog"]["active_count"] == 1


def test_missing_hh_are_flagged_and_not_invented_in_backlog_summary(relational_backlog):
    relational_backlog.db.execute("UPDATE programacion.plan_trabajo SET numero_personas_efectivo=NULL WHERE id=1")
    result = backlog._get_backlog_summary(relational_backlog)
    assert result["pendientes_activas"] == 2
    assert result["backlog_sin_hh"] == 2
    assert result["hh_backlog_activo"] == 0.0


def test_portfolio_query_deduplicates_observations_and_preserves_period_authority(relational_backlog):
    db = relational_backlog.db
    db.executescript("""
        CREATE TABLE programacion.programacion_semanal_v2(id INTEGER,semana_inicio DATE,estado TEXT);
        CREATE TABLE programacion.programacion_item_v2(
          programacion_id INTEGER,orden_mantenimiento_id INTEGER,origen_backlog BOOLEAN,finalizado BOOLEAN);
        CREATE TABLE programacion.seguimiento_semanal_v2(id INTEGER,programacion_id INTEGER,registrado_en TEXT);
        CREATE TABLE programacion.seguimiento_semanal_item_v2(
          seguimiento_id INTEGER,orden_mantenimiento_id INTEGER,finalizado BOOLEAN);
        CREATE TABLE programacion.seguimiento_no_programado_v2(
          orden_mantenimiento_id INTEGER,programacion_id INTEGER,fecha_fin_orden DATE);
        INSERT INTO programacion.programacion_semanal_v2 VALUES
          (1,'2026-10-01','CERRADA'),(2,'2026-10-08','CERRADA'),(3,'2026-09-01','CERRADA');
        INSERT INTO programacion.programacion_item_v2 VALUES(1,1,false,true),(2,1,true,true);
        INSERT INTO programacion.seguimiento_semanal_v2 VALUES(1,1,'2026-10-07T20:00:00');
        INSERT INTO programacion.seguimiento_semanal_item_v2 VALUES(1,1,true);
        INSERT INTO programacion.seguimiento_no_programado_v2 VALUES
          (2,1,NULL),(2,2,NULL),(3,1,NULL),(4,1,NULL),(5,3,'2026-09-07'),(6,1,NULL);
    """)
    result = get_portfolio(relational_backlog, date(2026,10,1), date(2026,11,1))
    total = result["tracking_progress"]
    # Three valid maintenance orders; annulments and operation are excluded.
    # Repeated tracking/closures of OT-1 and OT-2 each count only once.
    assert total["total_orders"] == 3
    assert total["finalized_orders"] == 2
    assert total["pending_orders"] == 1
    assert total["scheduled_finalized_orders"] == 1
    assert total["unplanned_finalized_orders"] == 1
    assert total["total_workload_hh"] == 6.0
    assert total["finalized_workload_hh"] == 4.0
    assert total["progress_pct"] == total["progress_hh_pct"] == 66.7
    assert result["unknown_completion_date_count"] == 1
    assert result["missing_hh_count"] == 0


class ProgrammingGuardConnection:
    """Execute the actual eligibility SELECT; unrelated earlier reads are empty."""
    def __init__(self, relational, closed=False):
        self.relational = relational
        self.closed = closed
        self.eligibility_checked = False

    def begin(self):
        return nullcontext(self)

    def execute(self, statement, params=None):
        sql = str(statement)
        if not sql.lstrip().upper().startswith("SELECT"):
            pytest.fail("Rejected or closed orders must never reach a database mutation")
        if self.closed and "SELECT id,estado FROM programacion.programacion_semanal_v2" in sql:
            return Result([{"id": 1, "estado": "CERRADA"}])
        if "SELECT o.id AS orden_mantenimiento_id,o.numero_ot,p.requiere_parada" not in sql:
            return Result([])
        self.eligibility_checked = True
        bound = dict(params)
        ids = bound.pop("ids")
        names = []
        for index, oid in enumerate(ids):
            name = f"selected_id_{index}"
            bound[name] = oid
            names.append(":" + name)
        sql = sql.replace("=ANY(CAST(:ids AS bigint[]))", " IN (" + ",".join(names) + ")")
        return self.relational.execute(sql, bound)


@pytest.mark.parametrize("oid", [3, 4])
def test_saving_annulled_source_or_backlog_is_rejected_before_mutation(relational_backlog, monkeypatch, oid):
    db = relational_backlog.db
    # Both rows would otherwise be complete and eligible; one is terminal only
    # in backlog and the other only in its source state.
    db.executescript("""
        ALTER TABLE programacion.plan_trabajo ADD COLUMN requiere_parada BOOLEAN DEFAULT false;
        ALTER TABLE programacion.plan_trabajo ADD COLUMN tiempo_parada_efectivo_min INTEGER DEFAULT 0;
        CREATE TABLE programacion.programacion_item_v2(orden_mantenimiento_id INTEGER,programacion_id INTEGER,finalizado BOOLEAN,anulado BOOLEAN);
        CREATE TABLE programacion.programacion_semanal_v2(id INTEGER,especialidad TEXT,estado TEXT,semana_fin DATE);
        UPDATE programacion.orden_mantenimiento SET estado='PENDIENTE' WHERE id=3;
    """)
    conn = ProgrammingGuardConnection(relational_backlog)
    monkeypatch.setattr(programming, "get_engine", lambda: conn)
    monkeypatch.setattr(programming, "_capacity", lambda *args: {"target": 100})
    with pytest.raises(programming.V2ProgrammingError, match="ya no están disponibles"):
        programming.save_week_programming(date_from=date(2026,10,1), date_to=date(2026,10,7),
                                          specialty="MEC", order_ids=[oid], created_by="qa-fixture")
    assert conn.eligibility_checked


def test_saving_closed_week_is_rejected_before_any_mutation(relational_backlog, monkeypatch):
    conn = ProgrammingGuardConnection(relational_backlog, closed=True)
    monkeypatch.setattr(programming, "get_engine", lambda: conn)
    monkeypatch.setattr(programming, "_capacity", lambda *args: {"target": 100})
    with pytest.raises(programming.V2ProgrammingError, match="semana ya fue cerrada"):
        programming.save_week_programming(date_from=date(2026,10,1), date_to=date(2026,10,7),
                                          specialty="MEC", order_ids=[1], created_by="qa-fixture")
    assert not conn.eligibility_checked
