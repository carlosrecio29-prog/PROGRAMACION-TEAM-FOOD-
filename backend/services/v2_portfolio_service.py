"""Read-only portfolio authority shared by the dashboard and period indicators.

The portfolio is a current-state view, not an immutable monthly closure. A
completion reported without its execution date remains explicitly undated.
"""
from __future__ import annotations

from datetime import date
from decimal import Decimal, ROUND_HALF_UP
from typing import Any

from sqlalchemy import text


SPECIALTIES = {"MEC": "Mecánica", "ELE": "Eléctrica", "MET": "Metrología", "SER": "Servicios"}
SPECIALTY_NAMES = {**SPECIALTIES, "SOL": "Soldadura"}
ACTIVE_BACKLOG_STATES = ("PENDIENTE_DISPONIBLE", "PENDIENTE_PROGRAMADA")


def progress_payload(row: dict[str, Any]) -> dict[str, Any]:
    total = max(0, int(row.get("total_orders") or 0))
    finalized = max(0, min(total, int(row.get("finalized_orders") or 0)))
    total_hh = round(float(row.get("total_workload_hh") or 0), 2)
    finalized_hh = round(float(row.get("finalized_workload_hh") or 0), 2)
    return {
        "total_orders": total,
        "finalized_orders": finalized,
        "scheduled_finalized_orders": max(0, int(row.get("scheduled_finalized_orders") or 0)),
        "unplanned_finalized_orders": max(0, int(row.get("unplanned_finalized_orders") or 0)),
        "pending_orders": total - finalized,
        "progress_pct": round(100.0 * finalized / total, 1) if total else 0.0,
        "pmp_orders": max(0, int(row.get("pmp_orders") or 0)),
        "backlog_orders": max(0, int(row.get("backlog_orders") or 0)),
        "total_workload_hh": total_hh,
        "finalized_workload_hh": finalized_hh,
        "pending_workload_hh": round(max(0.0, total_hh - finalized_hh), 2),
        "progress_hh_pct": round(100.0 * finalized_hh / total_hh, 1) if total_hh else 0.0,
        "latest_tracking_at": row.get("latest_tracking_at"),
    }


def aggregate_portfolio(rows: list[dict[str, Any]], latest_tracking_at: Any = None) -> dict[str, Any]:
    """Aggregate unique order IDs from the portfolio query, including empty specialties."""
    def hh_total(items: list[dict[str, Any]]) -> float:
        total = sum((Decimal(str(r["hh"] or 0)) for r in items), Decimal(0))
        return float(total.quantize(Decimal("0.01"), rounding=ROUND_HALF_UP))

    def aggregate(items: list[dict[str, Any]]) -> dict[str, Any]:
        return progress_payload({
            "total_orders": len(items),
            "finalized_orders": sum(bool(r["finished"]) for r in items),
            "scheduled_finalized_orders": sum(bool(r["scheduled_finished"]) for r in items),
            "unplanned_finalized_orders": sum(bool(r["unplanned_finished"]) for r in items),
            "pmp_orders": sum(bool(r["is_pmp"]) for r in items),
            "backlog_orders": sum(bool(r["is_backlog"]) and not r["is_pmp"] for r in items),
            "total_workload_hh": hh_total(items),
            "finalized_workload_hh": hh_total([r for r in items if r["finished"]]),
            "latest_tracking_at": latest_tracking_at,
        })

    codes = list(SPECIALTIES)
    codes.extend(sorted({r.get("especialidad") or "SIN" for r in rows} - set(codes)))
    return {
        "tracking_progress": aggregate(rows),
        "portfolio_progress_by_specialty": [
            {"especialidad": code, "name": SPECIALTY_NAMES.get(code, "Sin especialidad" if code == "SIN" else code),
             **aggregate([r for r in rows if (r.get("especialidad") or "SIN") == code])}
            for code in codes
        ],
    }


def get_portfolio(conn, period: date, next_period: date) -> dict[str, Any]:
    rows = [dict(row) for row in conn.execute(text("""
        WITH month_pmp AS (
          SELECT o.id AS order_id FROM programacion.orden_mantenimiento o
          LEFT JOIN programacion.plan_trabajo p ON p.id=o.plan_trabajo_id
          WHERE o.periodo=:period AND NOT COALESCE(p.es_operacion,false)
            AND upper(COALESCE(o.estado,'')) NOT LIKE 'ANUL%'
        ), backlog_available AS (
          SELECT b.orden_mantenimiento_id AS order_id FROM programacion.backlog_v2 b
          JOIN programacion.orden_mantenimiento o ON o.id=b.orden_mantenimiento_id
          LEFT JOIN programacion.plan_trabajo p ON p.id=o.plan_trabajo_id
          WHERE b.estado_seguimiento='PENDIENTE_DISPONIBLE'
            AND NOT COALESCE(p.es_operacion,false)
            AND upper(COALESCE(o.estado,'')) NOT LIKE 'ANUL%'
        ), backlog_used_month AS (
          SELECT DISTINCT pi.orden_mantenimiento_id AS order_id
          FROM programacion.programacion_item_v2 pi
          JOIN programacion.programacion_semanal_v2 ps ON ps.id=pi.programacion_id
          JOIN programacion.orden_mantenimiento o ON o.id=pi.orden_mantenimiento_id
          LEFT JOIN programacion.plan_trabajo p ON p.id=o.plan_trabajo_id
          WHERE ps.semana_inicio>=:period AND ps.semana_inicio<:next_period
            AND COALESCE(pi.origen_backlog,false) AND NOT COALESCE(p.es_operacion,false)
            AND upper(COALESCE(o.estado,'')) NOT LIKE 'ANUL%'
        ), unplanned_month AS (
          SELECT n.orden_mantenimiento_id AS order_id,
                 bool_and(n.fecha_fin_orden IS NULL) AS unknown_completion_date
          FROM programacion.seguimiento_no_programado_v2 n
          JOIN programacion.programacion_semanal_v2 ps ON ps.id=n.programacion_id
          JOIN programacion.orden_mantenimiento o ON o.id=n.orden_mantenimiento_id
          LEFT JOIN programacion.plan_trabajo p ON p.id=o.plan_trabajo_id
          WHERE ps.semana_inicio>=:period AND ps.semana_inicio<:next_period
            AND NOT COALESCE(p.es_operacion,false)
            AND upper(COALESCE(o.estado,'')) NOT LIKE 'ANUL%'
          GROUP BY n.orden_mantenimiento_id
        ), universe AS (
          SELECT order_id FROM month_pmp UNION SELECT order_id FROM backlog_available
          UNION SELECT order_id FROM backlog_used_month UNION SELECT order_id FROM unplanned_month
        ), scheduled_finished AS (
          SELECT si.orden_mantenimiento_id AS order_id
          FROM programacion.seguimiento_semanal_item_v2 si
          JOIN programacion.seguimiento_semanal_v2 s ON s.id=si.seguimiento_id
          JOIN programacion.programacion_semanal_v2 ps ON ps.id=s.programacion_id
          WHERE ps.semana_inicio>=:period AND ps.semana_inicio<:next_period AND si.finalizado=true
          UNION
          SELECT pi.orden_mantenimiento_id AS order_id FROM programacion.programacion_item_v2 pi
          JOIN programacion.programacion_semanal_v2 ps ON ps.id=pi.programacion_id
          WHERE ps.semana_inicio>=:period AND ps.semana_inicio<:next_period
            AND ps.estado='CERRADA' AND pi.finalizado=true
        )
        SELECT u.order_id,COALESCE(NULLIF(o.especialidad,''),'SIN') AS especialidad,
               mp.order_id IS NOT NULL AS is_pmp,
               (ba.order_id IS NOT NULL OR bu.order_id IS NOT NULL) AS is_backlog,
               sf.order_id IS NOT NULL AS scheduled_finished,
               um.order_id IS NOT NULL AS unplanned_finished,
               (sf.order_id IS NOT NULL OR um.order_id IS NOT NULL) AS finished,
               COALESCE(um.unknown_completion_date,false) AS unknown_completion_date,
               CASE WHEN p.numero_personas_efectivo IS NOT NULL
                     AND COALESCE(o.tiempo_planeado_min,p.tiempo_ejecucion_min) IS NOT NULL
                    THEN COALESCE(o.tiempo_planeado_min,p.tiempo_ejecucion_min)/60.0*p.numero_personas_efectivo
                    ELSE NULL END AS hh
        FROM universe u JOIN programacion.orden_mantenimiento o ON o.id=u.order_id
        LEFT JOIN programacion.plan_trabajo p ON p.id=o.plan_trabajo_id
        LEFT JOIN month_pmp mp USING(order_id)
        LEFT JOIN backlog_available ba USING(order_id)
        LEFT JOIN backlog_used_month bu USING(order_id)
        LEFT JOIN scheduled_finished sf USING(order_id)
        LEFT JOIN unplanned_month um USING(order_id)
    """), {"period": period, "next_period": next_period}).mappings()]
    latest = conn.execute(text("""
        SELECT max(s.registrado_en) FROM programacion.seguimiento_semanal_v2 s
        JOIN programacion.programacion_semanal_v2 ps ON ps.id=s.programacion_id
        WHERE ps.semana_inicio>=:period AND ps.semana_inicio<:next_period
    """), {"period": period, "next_period": next_period}).scalar_one()
    result = aggregate_portfolio(rows, latest)
    result["missing_hh_count"] = sum(r["hh"] is None for r in rows)
    result["unknown_completion_date_count"] = sum(bool(r["unknown_completion_date"]) for r in rows)
    return result


def get_management_insights(conn, period: date, portfolio: dict[str, Any]) -> dict[str, Any]:
    record = dict(conn.execute(text("""
        WITH active AS (
          SELECT b.estado_seguimiento,
                 GREATEST(0,(CURRENT_TIMESTAMP AT TIME ZONE 'America/Bogota')::date-COALESCE(b.primera_semana_origen_inicio,b.semana_origen_inicio)) AS age,
                 upper(btrim(COALESCE(a.criticidad,'')))='A' AS critical_a
          FROM programacion.backlog_v2 b
          JOIN programacion.orden_mantenimiento o ON o.id=b.orden_mantenimiento_id
          JOIN programacion.activo a ON a.id=o.activo_id
          LEFT JOIN programacion.plan_trabajo p ON p.id=o.plan_trabajo_id
          WHERE b.estado_seguimiento IN ('PENDIENTE_DISPONIBLE','PENDIENTE_PROGRAMADA')
            AND upper(COALESCE(o.estado,'')) NOT LIKE 'ANUL%'
            AND upper(COALESCE(o.estado,'')) NOT LIKE 'FINALIZ%'
            AND NOT COALESCE(p.es_operacion,false)
        )
        SELECT (CURRENT_TIMESTAMP AT TIME ZONE 'America/Bogota')::date AS as_of,count(*)::int AS active_count,
               count(*) FILTER (WHERE estado_seguimiento='PENDIENTE_DISPONIBLE')::int AS available_count,
               count(*) FILTER (WHERE estado_seguimiento='PENDIENTE_PROGRAMADA')::int AS scheduled_count,
               count(*) FILTER (WHERE critical_a)::int AS critical_a_count,
               count(*) FILTER (WHERE age<=30)::int AS up_to_30,
               count(*) FILTER (WHERE age BETWEEN 31 AND 60)::int AS days_31_60,
               count(*) FILTER (WHERE age BETWEEN 61 AND 90)::int AS days_61_90,
               count(*) FILTER (WHERE age>90)::int AS over_90,
               COALESCE(
                 NULLIF((SELECT count(*) FROM programacion.operacion_exclusion_detalle_v2 WHERE periodo=:period),0),
                 (SELECT sum(cantidad) FROM programacion.operacion_exclusion_periodo_v2 WHERE periodo=:period),
                 0
               )::int AS operation_excluded_count
        FROM active
    """), {"period": period}).mappings().one())
    return {
        "period": str(period), "as_of": str(record.pop("as_of")),
        "scope": "CARTERA_PERIODO_Y_BACKLOG_ACTUAL",
        "counting_unit": "ACTIVIDAD_ORDEN_MANTENIMIENTO_ID",
        "unknown_completion_date_count": portfolio["unknown_completion_date_count"],
        "missing_hh_count": portfolio["missing_hh_count"],
        "operation_excluded_count": record.pop("operation_excluded_count"),
        "backlog": {
            "scope": "BACKLOG_ACTIVO_ACTUAL",
            "aging_buckets": {k: record.pop(k) for k in ("up_to_30", "days_31_60", "days_61_90", "over_90")},
            **record,
        },
    }
