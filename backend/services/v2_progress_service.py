from __future__ import annotations

from collections import defaultdict
from datetime import date
from typing import Any

from sqlalchemy import text
from backend.database import get_engine

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
                       pmp_count: int, month_period: date | None = None) -> dict[str, Any]:
    """Semana = ejecuciones programadas; mes = OT únicas con último cierre conocido."""
    by_week: dict[int, dict[str, Any]] = {}
    for row in headers:
        week = dict(row)
        week.update({
            "programming_id": int(row["id"]),
            "programmed": 0, "finalized": 0, "pending": 0,
            "not_found": 0, "unchecked": 0,
            "hh_programmed": 0.0, "hh_finalized": 0.0,
            "hh_pending": 0.0, "hh_not_found": 0.0,
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
            if item["finalizado"] is True:
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
        "programmed", "finalized", "pending", "not_found", "unchecked",
        "origin_backlog", "hh_programmed", "hh_finalized", "hh_pending", "hh_not_found",
    )}
    specialty_agg: dict[str, dict[str, Any]] = defaultdict(
        lambda: {**{key: 0 for key in totals}, "closed": 0, "weeks": 0}
    )
    for week in weeks:
        week["progress_ot_pct"] = _pct(week["finalized"], week["programmed"]) if week["estado"] == "CERRADA" else None
        week["progress_hh_pct"] = _pct(week["hh_finalized"], week["hh_programmed"]) if week["estado"] == "CERRADA" else None
        for key in totals:
            if key.startswith("hh_"):
                week[key] = round(week[key], 2)
            totals[key] += week[key]
            specialty_agg[week["especialidad"]][key] += week[key]
        specialty_agg[week["especialidad"]]["weeks"] += 1
        specialty_agg[week["especialidad"]]["closed"] += int(week["estado"] == "CERRADA")
    for key in totals:
        if key.startswith("hh_"):
            totals[key] = round(totals[key], 2)

    unique = {"programmed": len(latest), "finalized": 0, "pending": 0,
              "not_found": 0, "unchecked": 0}
    unresolved = []
    for record in latest.values():
        status = record["_estado_programacion"]
        if status != "CERRADA" or not record.get("estado_cierre"):
            unique["unchecked"] += 1
        elif record["finalizado"] is True:
            unique["finalized"] += 1
        elif record["finalizado"] is False:
            unique["pending"] += 1
        else:
            unique["not_found"] += 1
        if status == "CERRADA" and record["finalizado"] is not True:
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
        record["progress_ot_pct"] = _pct(record["finalized"], record["programmed"])
        record["progress_hh_pct"] = _pct(record["hh_finalized"], record["hh_programmed"])

    unique["programmed_from_pmp"] = sum(
        1 for record in latest.values()
        if month_period is None or record.get("periodo") == month_period
    )
    unique["from_prior_backlog"] = unique["programmed"] - unique["programmed_from_pmp"]
    unique["progress_ot_pct"] = _pct(unique["finalized"], unique["programmed"])
    complete = bool(weeks) and all(w["estado"] == "CERRADA" for w in weeks)
    return {
        "weeks": weeks, "specialties": sorted(specialty_agg.values(), key=lambda x: x["especialidad"]),
        "weekly_totals": {**totals, "progress_ot_pct": _pct(totals["finalized"], totals["programmed"]),
                          "progress_hh_pct": _pct(totals["hh_finalized"], totals["hh_programmed"])},
        "monthly": {**unique, "pmp_count": int(pmp_count),
                    "not_programmed": max(0, int(pmp_count) - unique["programmed_from_pmp"]),
                    "all_weeks_closed": complete,
                    "contains_future_week_closures": any(w["estado"] == "CERRADA" and w["semana_fin"] > date.today() for w in weeks),
                    "weeks_total": len(weeks),
                    "weeks_closed": sum(w["estado"] == "CERRADA" for w in weeks)},
        "unresolved": unresolved,
        "criteria": {
            "weekly": "Cada OT se cuenta por cada semana programada; solo CERRADA tiene resultado de ejecución.",
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
                   i.finalizado,i.estado_cierre,i.origen_backlog,
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
    return {"year": year, "month": month, **aggregate_progress(headers, items, pmp_count, begin)}


def export_progress_pdf(year: int, month: int, programming_id: int | None = None) -> tuple[bytes, str]:
    """Create one consistent visual PDF regardless of installed PDF packages.

    Read-only: reuses the same monthly aggregation as the dashboard, plus
    per-OT closure rows when a single weekly report is requested.
    """
    from backend.services.v2_pdf_fallback import render_progress_fallback

    data = get_progress(year, month)
    details = None
    if programming_id is not None:
        week = next((w for w in data["weeks"] if w["programming_id"] == programming_id), None)
        if week is None:
            raise ValueError("La programación no corresponde al mes indicado")
        from backend.services.v2_closure_service import get_week_closure

        report = get_week_closure(programming_id)
        details = []
        for row in report["rows"]:
            details.append({
                "numero_ot": row.get("numero_ot"),
                "especialidad": week["especialidad"],
                "activo": row.get("activo_codigo"),
                "plan": row.get("plan_trabajo") or "",
                "estado_cierre": row.get("estado_cierre"),
                "resultado": (
                    "FINALIZADA" if row.get("finalizado") is True else
                    "PENDIENTE" if row.get("finalizado") is False else
                    "NO ENCONTRADA" if row.get("estado_cierre") else
                    "SIN VERIFICAR"
                ),
                "hh_estimada": row.get("hh_programadas") or 0,
            })
    return render_progress_fallback(data, year, month, programming_id, details)
