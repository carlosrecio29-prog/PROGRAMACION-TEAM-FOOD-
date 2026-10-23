from __future__ import annotations

from collections import defaultdict
from datetime import date
from typing import Any

from sqlalchemy import text
from backend.database import get_engine
from backend.services.v2_portfolio_service import get_portfolio

SPECS = {"MEC": "Mecánica", "ELE": "Eléctrica", "MET": "Metrología", "SER": "Servicios"}


def _period(year: int, month: int) -> tuple[date, date]:
    if not 2020 <= year <= 2100 or not 1 <= month <= 12:
        raise ValueError("Periodo inválido")
    begin = date(year, month, 1)
    end = date(year + 1, 1, 1) if month == 12 else date(year, month + 1, 1)
    return begin, end


def _pct(a: float, b: float) -> float:
    return round(100 * a / b, 1) if b else 0.0


def aggregate_progress(headers: list[dict[str, Any]], items: list[dict[str, Any]],
                       pmp_count: int, month_period: date | None = None,
                       tracking: dict[int, dict[str, Any]] | None = None) -> dict[str, Any]:
    """Semana = ejecuciones programadas; mes = OT únicas con último cierre conocido.

    El bloque operational combina cierre oficial para semanas cerradas y el último
    seguimiento disponible para semanas abiertas, sin alterar el resultado oficial.
    """
    tracking = tracking or {}
    by_week: dict[int, dict[str, Any]] = {}
    for row in headers:
        week = dict(row)
        week.update({
            "programming_id": int(row["id"]),
            "programmed": 0, "finalized": 0, "pending": 0, "annulled": 0,
            "not_found": 0, "unchecked": 0,
            "hh_programmed": 0.0, "hh_finalized": 0.0,
            "hh_pending": 0.0, "hh_annulled": 0.0, "hh_not_found": 0.0,
            "origin_backlog": 0, "progress_ot_pct": 0.0,
            "progress_hh_pct": 0.0,
        })
        week["week_from"] = str(row["semana_inicio"])
        week["week_to"] = str(row["semana_fin"])
        by_week[int(row["id"])] = week

    latest: dict[int, dict[str, Any]] = {}
    for item in items:
        week = by_week.get(int(item["programacion_id"]))
        if not week:
            continue
        hh = float(item["hh_programadas"] or 0)
        week["programmed"] += 1
        week["hh_programmed"] += hh
        if item.get("origen_backlog"):
            week["origin_backlog"] += 1
        # Una programación GUARDADA todavía no equivale a una OT finalizada o pendiente.
        if week["estado"] == "CERRADA" and item.get("estado_cierre"):
            if item.get("anulado"):
                week["annulled"] += 1
                week["hh_annulled"] += hh
            elif item["finalizado"] is True:
                week["finalized"] += 1
                week["hh_finalized"] += hh
            elif item["finalizado"] is False:
                week["pending"] += 1
                week["hh_pending"] += hh
            else:
                week["not_found"] += 1
                week["hh_not_found"] += hh
        else:
            week["unchecked"] += 1
        oid = int(item["orden_mantenimiento_id"])
        priority = (week["semana_fin"], week["semana_inicio"], int(week["id"]))
        previous = latest.get(oid)
        if not previous or priority > previous["_priority"]:
            latest[oid] = {**item, "_priority": priority, "_estado_programacion": week["estado"]}

    weeks = sorted(by_week.values(), key=lambda w: (w["semana_inicio"], w["especialidad"]))
    totals = {key: 0 for key in (
        "programmed", "finalized", "pending", "annulled", "not_found", "unchecked",
        "origin_backlog", "hh_programmed", "hh_finalized", "hh_pending", "hh_annulled", "hh_not_found",
    )}
    operational_totals = {
        "programmed": 0, "finalized": 0, "pending": 0, "annulled": 0, "unchecked": 0,
        "hh_programmed": 0.0, "hh_finalized": 0.0, "hh_pending": 0.0, "hh_annulled": 0.0,
        "weeks_tracking": 0, "weeks_closed": 0, "weeks_open": 0,
        "latest_tracking_at": None,
    }
    specialty_agg: dict[str, dict[str, Any]] = defaultdict(
        lambda: {**{key: 0 for key in totals}, "closed": 0, "weeks": 0}
    )
    for week in weeks:
        closed = week["estado"] == "CERRADA"
        track = tracking.get(int(week["id"]))

        effective_programmed = max(0, week["programmed"] - week["annulled"])
        effective_hh = max(0.0, week["hh_programmed"] - week["hh_annulled"])
        week["progress_ot_pct"] = _pct(week["finalized"], effective_programmed) if closed else None
        week["progress_hh_pct"] = _pct(week["hh_finalized"], effective_hh) if closed else None

        if closed:
            week["operational_source"] = "CIERRE"
            week["operational_programmed"] = week["programmed"]
            week["operational_finalized"] = week["finalized"]
            week["operational_pending"] = week["pending"]
            week["operational_annulled"] = week["annulled"]
            week["operational_unchecked"] = week["not_found"]
            week["operational_hh_programmed"] = week["hh_programmed"]
            week["operational_hh_finalized"] = week["hh_finalized"]
            week["operational_hh_pending"] = week["hh_pending"]
            week["operational_hh_annulled"] = week["hh_annulled"]
            week["operational_progress_ot_pct"] = week["progress_ot_pct"]
            week["operational_progress_hh_pct"] = week["progress_hh_pct"]
            week["tracking_at"] = None
            operational_totals["weeks_closed"] += 1
        elif track:
            week["operational_source"] = "SEGUIMIENTO"
            week["operational_programmed"] = int(track.get("total_items") or week["programmed"])
            week["operational_finalized"] = int(track.get("finalizados") or 0)
            week["operational_pending"] = int(track.get("pendientes") or 0)
            week["operational_annulled"] = 0
            week["operational_unchecked"] = int(track.get("sin_coincidencia") or 0)
            week["operational_hh_programmed"] = float(track.get("hh_programadas") or week["hh_programmed"] or 0)
            week["operational_hh_finalized"] = float(track.get("hh_finalizadas") or 0)
            week["operational_hh_pending"] = float(track.get("hh_pendientes") or 0)
            week["operational_hh_annulled"] = 0.0
            week["operational_progress_ot_pct"] = float(track.get("avance_ot_pct") or 0)
            week["operational_progress_hh_pct"] = float(track.get("avance_hh_pct") or 0)
            week["tracking_at"] = track.get("registrado_en")
            operational_totals["weeks_tracking"] += 1
            operational_totals["weeks_open"] += 1
            if track.get("registrado_en") and (
                operational_totals["latest_tracking_at"] is None
                or track["registrado_en"] > operational_totals["latest_tracking_at"]
            ):
                operational_totals["latest_tracking_at"] = track["registrado_en"]
        else:
            week["operational_source"] = "SIN SEGUIMIENTO"
            week["operational_programmed"] = week["programmed"]
            week["operational_finalized"] = 0
            week["operational_pending"] = 0
            week["operational_annulled"] = 0
            week["operational_unchecked"] = week["programmed"]
            week["operational_hh_programmed"] = week["hh_programmed"]
            week["operational_hh_finalized"] = 0.0
            week["operational_hh_pending"] = 0.0
            week["operational_hh_annulled"] = 0.0
            week["operational_progress_ot_pct"] = None
            week["operational_progress_hh_pct"] = None
            week["tracking_at"] = None
            operational_totals["weeks_open"] += 1

        for key in totals:
            if key.startswith("hh_"):
                week[key] = round(week[key], 2)
            totals[key] += week[key]
            specialty_agg[week["especialidad"]][key] += week[key]

        for key in ("programmed", "finalized", "pending", "annulled", "unchecked"):
            operational_totals[key] += int(week[f"operational_{key}"] or 0)
        for key in ("hh_programmed", "hh_finalized", "hh_pending", "hh_annulled"):
            operational_totals[key] += float(week[f"operational_{key}"] or 0)

        specialty_agg[week["especialidad"]]["weeks"] += 1
        specialty_agg[week["especialidad"]]["closed"] += int(closed)

    for key in totals:
        if key.startswith("hh_"):
            totals[key] = round(totals[key], 2)
    for key in ("hh_programmed", "hh_finalized", "hh_pending", "hh_annulled"):
        operational_totals[key] = round(operational_totals[key], 2)
    operational_totals["progress_ot_pct"] = _pct(
        operational_totals["finalized"],
        max(0, operational_totals["programmed"] - operational_totals["annulled"]),
    )
    operational_totals["progress_hh_pct"] = _pct(
        operational_totals["hh_finalized"],
        max(0.0, operational_totals["hh_programmed"] - operational_totals["hh_annulled"]),
    )

    unique = {"programmed": len(latest), "finalized": 0, "pending": 0, "annulled": 0,
              "not_found": 0, "unchecked": 0}
    unresolved = []
    for record in latest.values():
        status = record["_estado_programacion"]
        if status != "CERRADA" or not record.get("estado_cierre"):
            unique["unchecked"] += 1
        elif record.get("anulado"):
            unique["annulled"] += 1
        elif record["finalizado"] is True:
            unique["finalized"] += 1
        elif record["finalizado"] is False:
            unique["pending"] += 1
        else:
            unique["not_found"] += 1
        if status == "CERRADA" and not record.get("anulado") and record["finalizado"] is not True:
            unresolved.append({
                "numero_ot": record.get("numero_ot") or "SIN ASIGNAR",
                "activo": record.get("activo_codigo") or "",
                "plan": record.get("plan_clave_software") or "",
                "especialidad": record.get("especialidad") or "",
                "estado_cierre": record.get("estado_cierre") or "SIN VERIFICAR",
                "hh_estimada": round(float(record.get("hh_programadas") or 0), 2),
                "resultado": "PENDIENTE" if record["finalizado"] is False else "NO ENCONTRADA",
            })
    unresolved.sort(key=lambda row: (row["especialidad"], row["resultado"], row["numero_ot"]))
    for code, record in specialty_agg.items():
        record["especialidad"] = code
        record["name"] = SPECS.get(code, code)
        for key in totals:
            if key.startswith("hh_"):
                record[key] = round(record[key], 2)
        record["progress_ot_pct"] = _pct(
            record["finalized"], max(0, record["programmed"] - record["annulled"])
        )
        record["progress_hh_pct"] = _pct(
            record["hh_finalized"], max(0.0, record["hh_programmed"] - record["hh_annulled"])
        )

    unique["programmed_from_pmp"] = sum(
        1 for record in latest.values()
        if month_period is None or record.get("periodo") == month_period
    )
    unique["from_prior_backlog"] = unique["programmed"] - unique["programmed_from_pmp"]
    unique["progress_ot_pct"] = _pct(
        unique["finalized"], max(0, unique["programmed"] - unique["annulled"])
    )
    complete = bool(weeks) and all(w["estado"] == "CERRADA" for w in weeks)
    return {
        "weeks": weeks, "specialties": sorted(specialty_agg.values(), key=lambda x: x["especialidad"]),
        "weekly_totals": {
            **totals,
            "progress_ot_pct": _pct(totals["finalized"], max(0, totals["programmed"] - totals["annulled"])),
            "progress_hh_pct": _pct(
                totals["hh_finalized"], max(0.0, totals["hh_programmed"] - totals["hh_annulled"])
            ),
        },
        "operational": operational_totals,
        "monthly": {**unique, "pmp_count": int(pmp_count),
                    "not_programmed": max(0, int(pmp_count) - unique["programmed_from_pmp"]),
                    "all_weeks_closed": complete,
                    "contains_future_week_closures": any(w["estado"] == "CERRADA" and w["semana_fin"] > date.today() for w in weeks),
                    "weeks_total": len(weeks),
                    "weeks_closed": sum(w["estado"] == "CERRADA" for w in weeks)},
        "unresolved": unresolved,
        "criteria": {
            "weekly": "Cada OT se cuenta por cada semana programada; el avance operativo usa el último seguimiento en semanas abiertas y el cierre oficial en semanas cerradas.",
            "monthly": "Cada OT se cuenta una vez según el cierre de su última semana programada del periodo.",
            "hh": "H-H estimadas al programar, NO horas reales trabajadas.",
            "month": "Semanas cuya fecha de inicio pertenece al mes seleccionado; OPERACIÓN excluida.",
            "pmp": "Cartera PMP de mantenimiento del mes, aunque alguna OT nunca haya sido programada.",
        },
    }


def get_progress(year: int, month: int) -> dict[str, Any]:
    begin, end = _period(year, month)
    with get_engine().connect() as conn:
        headers = [dict(r) for r in conn.execute(text("""
            SELECT id,semana_inicio,semana_fin,especialidad,estado,
                   hh_disponibles,hh_objetivo,hh_reserva,cierre_en,cierre_archivo
            FROM programacion.programacion_semanal_v2
            WHERE semana_inicio >= :begin AND semana_inicio < :end
            ORDER BY semana_inicio,especialidad
        """), {"begin": begin, "end": end}).mappings()]
        items = [dict(r) for r in conn.execute(text("""
            SELECT i.programacion_id,i.orden_mantenimiento_id,i.hh_programadas,
                   i.finalizado,i.anulado,i.comentario_cierre,i.estado_cierre,i.origen_backlog,
                   o.numero_ot,o.plan_clave_software,o.especialidad,o.periodo,
                   a.codigo AS activo_codigo
            FROM programacion.programacion_item_v2 i
            JOIN programacion.programacion_semanal_v2 s ON s.id=i.programacion_id
            JOIN programacion.orden_mantenimiento o ON o.id=i.orden_mantenimiento_id
            JOIN programacion.activo a ON a.id=o.activo_id
            LEFT JOIN programacion.plan_trabajo p ON p.id=o.plan_trabajo_id
            WHERE s.semana_inicio >= :begin AND s.semana_inicio < :end
              AND COALESCE(p.es_operacion,false)=false
        """), {"begin": begin, "end": end}).mappings()]
        pmp_count = conn.execute(text("""
            SELECT count(*) FROM programacion.orden_mantenimiento o
            LEFT JOIN programacion.plan_trabajo p ON p.id=o.plan_trabajo_id
            WHERE o.periodo=:begin AND COALESCE(p.es_operacion,false)=false
        """), {"begin": begin}).scalar_one()

        tracking_rows = [dict(r) for r in conn.execute(text("""
            SELECT DISTINCT ON (t.programacion_id)
                   t.programacion_id,t.registrado_en,t.total_items,
                   t.finalizados,t.pendientes,t.sin_coincidencia,
                   t.hh_programadas,t.hh_finalizadas,t.hh_pendientes,
                   t.avance_ot_pct,t.avance_hh_pct
            FROM programacion.seguimiento_semanal_v2 t
            JOIN programacion.programacion_semanal_v2 s ON s.id=t.programacion_id
            WHERE s.semana_inicio >= :begin AND s.semana_inicio < :end
            ORDER BY t.programacion_id,t.registrado_en DESC,t.id DESC
        """), {"begin": begin, "end": end}).mappings()]
        tracking = {int(row["programacion_id"]): row for row in tracking_rows}

        portfolio = get_portfolio(conn, begin, end)
        monthly_specialty_rows = [dict(r) for r in conn.execute(text("""
            WITH specs(code,name) AS (
              VALUES
                ('MEC','Mecánica'),
                ('ELE','Eléctrica'),
                ('MET','Metrología'),
                ('SER','Servicios')
            ),
            month_pmp AS (
              SELECT
                o.id AS orden_mantenimiento_id,
                o.numero_ot,
                o.especialidad,
                CASE
                  WHEN p.numero_personas_efectivo IS NOT NULL
                   AND COALESCE(o.tiempo_planeado_min,p.tiempo_ejecucion_min) IS NOT NULL
                  THEN round(
                    COALESCE(o.tiempo_planeado_min,p.tiempo_ejecucion_min)/60.0
                    * p.numero_personas_efectivo,
                    2
                  )
                  ELSE NULL
                END AS hh
              FROM programacion.orden_mantenimiento o
              JOIN programacion.plan_trabajo p ON p.id=o.plan_trabajo_id
              WHERE o.periodo=:begin
                AND NOT COALESCE(p.es_operacion,false)
            ),
            initial_backlog AS (
              SELECT
                o.id AS orden_mantenimiento_id,
                o.numero_ot,
                o.especialidad,
                CASE
                  WHEN p.numero_personas_efectivo IS NOT NULL
                   AND COALESCE(o.tiempo_planeado_min,p.tiempo_ejecucion_min) IS NOT NULL
                  THEN round(
                    COALESCE(o.tiempo_planeado_min,p.tiempo_ejecucion_min)/60.0
                    * p.numero_personas_efectivo,
                    2
                  )
                  ELSE NULL
                END AS hh
              FROM programacion.backlog_v2 b
              JOIN programacion.orden_mantenimiento o ON o.id=b.orden_mantenimiento_id
              JOIN programacion.plan_trabajo p ON p.id=o.plan_trabajo_id
              WHERE NOT COALESCE(p.es_operacion,false)
                AND COALESCE(
                  b.primera_semana_origen_inicio,
                  b.semana_origen_inicio,
                  o.periodo
                ) < :begin
                AND (
                  b.estado_seguimiento IN ('PENDIENTE_DISPONIBLE','PENDIENTE_PROGRAMADA')
                  OR (
                    b.estado_seguimiento='FINALIZADA'
                    AND b.finalizado_en IS NOT NULL
                    AND b.finalizado_en::date >= :begin
                  )
                  OR (
                    b.estado_seguimiento='ANULADA'
                    AND COALESCE(b.ultimo_cierre_en,b.actualizado_en)::date >= :begin
                  )
                )
            ),
            base_universe AS (
              SELECT
                orden_mantenimiento_id,
                especialidad,
                max(numero_ot) AS numero_ot,
                max(hh) AS hh
              FROM (
                SELECT * FROM month_pmp
                UNION ALL
                SELECT * FROM initial_backlog
              ) u
              GROUP BY orden_mantenimiento_id,especialidad
            ),
            month_programs AS (
              SELECT id,especialidad,estado
              FROM programacion.programacion_semanal_v2
              WHERE semana_inicio >= :begin AND semana_inicio < :end
            ),
            latest_tracking AS (
              SELECT DISTINCT ON (t.programacion_id)
                     t.programacion_id,t.id AS seguimiento_id
              FROM programacion.seguimiento_semanal_v2 t
              JOIN month_programs mp ON mp.id=t.programacion_id
              ORDER BY t.programacion_id,t.registrado_en DESC,t.id DESC
            ),
            completed_candidates AS (
              SELECT
                mp.especialidad,
                i.orden_mantenimiento_id,
                o.numero_ot,
                i.hh_programadas::numeric AS hh,
                'PROGRAMADA'::text AS fuente,
                1 AS prioridad
              FROM month_programs mp
              JOIN programacion.programacion_item_v2 i ON i.programacion_id=mp.id
              JOIN programacion.orden_mantenimiento o ON o.id=i.orden_mantenimiento_id
              WHERE mp.estado='CERRADA'
                AND COALESCE(i.finalizado,false)=true
                AND COALESCE(i.anulado,false)=false

              UNION ALL

              SELECT
                mp.especialidad,
                si.orden_mantenimiento_id,
                si.numero_ot,
                si.hh_programadas::numeric AS hh,
                'PROGRAMADA'::text AS fuente,
                2 AS prioridad
              FROM month_programs mp
              JOIN latest_tracking lt ON lt.programacion_id=mp.id
              JOIN programacion.seguimiento_semanal_item_v2 si
                ON si.seguimiento_id=lt.seguimiento_id
              WHERE mp.estado<>'CERRADA'
                AND COALESCE(si.finalizado,false)=true

              UNION ALL

              SELECT
                COALESCE(NULLIF(btrim(snp.especialidad),''),mp.especialidad) AS especialidad,
                snp.orden_mantenimiento_id,
                snp.numero_ot,
                snp.hh_estimada::numeric AS hh,
                'NO_PROGRAMADA'::text AS fuente,
                3 AS prioridad
              FROM programacion.seguimiento_no_programado_v2 snp
              JOIN month_programs mp ON mp.id=snp.programacion_id
              WHERE snp.fecha_fin_orden IS NULL
                 OR (
                   snp.fecha_fin_orden::date >= :begin
                   AND snp.fecha_fin_orden::date < :end
                 )
            ),
            mapped_completed AS (
              SELECT
                c.especialidad,
                COALESCE(c.orden_mantenimiento_id,b.orden_mantenimiento_id) AS orden_mantenimiento_id,
                COALESCE(c.hh,b.hh) AS hh,
                c.fuente,
                c.prioridad
              FROM completed_candidates c
              LEFT JOIN base_universe b
                ON c.orden_mantenimiento_id IS NULL
               AND c.numero_ot IS NOT NULL
               AND b.numero_ot IS NOT NULL
               AND upper(btrim(b.numero_ot))=upper(btrim(c.numero_ot))
               AND b.especialidad=c.especialidad
            ),
            completed_unique AS (
              SELECT DISTINCT ON (especialidad,orden_mantenimiento_id)
                     especialidad,orden_mantenimiento_id,hh,fuente
              FROM mapped_completed
              WHERE orden_mantenimiento_id IS NOT NULL
              ORDER BY especialidad,orden_mantenimiento_id,prioridad
            ),
            base_summary AS (
              SELECT
                especialidad,
                count(*)::int AS total_ot,
                round(COALESCE(sum(hh),0),2) AS total_hh
              FROM base_universe
              GROUP BY especialidad
            ),
            completed_summary AS (
              SELECT
                c.especialidad,
                count(*)::int AS completed_ot,
                round(COALESCE(sum(COALESCE(c.hh,b.hh)),0),2) AS completed_hh,
                count(*) FILTER (WHERE c.fuente='PROGRAMADA')::int AS scheduled_completed,
                count(*) FILTER (WHERE c.fuente='NO_PROGRAMADA')::int AS unplanned_completed
              FROM completed_unique c
              JOIN base_universe b
                ON b.orden_mantenimiento_id=c.orden_mantenimiento_id
               AND b.especialidad=c.especialidad
              GROUP BY c.especialidad
            )
            SELECT
              s.code AS especialidad,
              s.name,
              COALESCE(bs.total_ot,0)::int AS total_ot,
              round(COALESCE(bs.total_hh,0),2) AS total_hh,
              COALESCE(cs.completed_ot,0)::int AS completed_ot,
              round(COALESCE(cs.completed_hh,0),2) AS completed_hh,
              COALESCE(cs.scheduled_completed,0)::int AS scheduled_completed,
              COALESCE(cs.unplanned_completed,0)::int AS unplanned_completed
            FROM specs s
            LEFT JOIN base_summary bs ON bs.especialidad=s.code
            LEFT JOIN completed_summary cs ON cs.especialidad=s.code
            ORDER BY CASE s.code
              WHEN 'MEC' THEN 1
              WHEN 'ELE' THEN 2
              WHEN 'MET' THEN 3
              WHEN 'SER' THEN 4
              ELSE 5
            END
        """), {"begin": begin, "end": end}).mappings()]

    monthly_progress_by_specialty = []
    for row in monthly_specialty_rows:
        total_ot = int(row["total_ot"] or 0)
        total_hh = round(float(row["total_hh"] or 0), 2)
        completed_ot = int(row["completed_ot"] or 0)
        completed_hh = round(float(row["completed_hh"] or 0), 2)
        monthly_progress_by_specialty.append({
            "especialidad": row["especialidad"],
            "name": row["name"],
            "total_ot": total_ot,
            "total_hh": total_hh,
            "completed_ot": completed_ot,
            "completed_hh": completed_hh,
            "progress_ot_pct": _pct(completed_ot, total_ot),
            "progress_hh_pct": _pct(completed_hh, total_hh),
            "scheduled_completed": int(row["scheduled_completed"] or 0),
            "unplanned_completed": int(row["unplanned_completed"] or 0),
        })


    return {
        "year": year,
        "month": month,
        **aggregate_progress(headers, items, pmp_count, begin, tracking),
        "monthly_progress_by_specialty": monthly_progress_by_specialty,
        "portfolio_progress_by_specialty": portfolio["portfolio_progress_by_specialty"],
    }


def export_progress_pdf(year: int, month: int, programming_id: int | None = None) -> tuple[bytes, str]:
    """Create one consistent visual PDF regardless of installed PDF packages.

    Read-only: reuses the same monthly aggregation as the dashboard, plus
    per-OT closure rows when a single weekly report is requested.
    """
    from backend.services.v2_pdf_fallback import render_progress_fallback

    data = get_progress(year, month)
    details = None
    unplanned_details = None
    if programming_id is not None:
        week = next((w for w in data["weeks"] if w["programming_id"] == programming_id), None)
        if week is None:
            raise ValueError("La programación no corresponde al mes indicado")
        from backend.services.v2_closure_service import get_week_closure
        from backend.services.v2_week_tracking_service import get_week_tracking

        report = get_week_closure(programming_id)
        tracking = get_week_tracking(programming_id)
        unplanned_details = list((tracking.get("unplanned") or {}).get("rows") or [])
        details = []
        for row in report["rows"]:
            details.append({
                "numero_ot": row.get("numero_ot"),
                "especialidad": week["especialidad"],
                "activo": row.get("activo_codigo"),
                "plan": row.get("plan_trabajo") or "",
                "estado_cierre": row.get("estado_cierre"),
                "resultado": (
                    "ANULADA" if row.get("anulado") else
                    "FINALIZADA" if row.get("finalizado") is True else
                    "PENDIENTE" if row.get("finalizado") is False else
                    "NO ENCONTRADA" if row.get("estado_cierre") else
                    "SIN VERIFICAR"
                ),
                "comentario": row.get("comentario_cierre"),
                "hh_estimada": row.get("hh_programadas") or 0,
            })
    return render_progress_fallback(
        data, year, month, programming_id, details,
        unplanned_rows=unplanned_details,
    )
