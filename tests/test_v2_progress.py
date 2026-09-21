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
        "hh_programadas": hh, "finalizado": finished,
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
