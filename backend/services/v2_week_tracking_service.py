from __future__ import annotations

from collections import defaultdict
from typing import Any

from sqlalchemy import text

from backend.database import get_engine
from backend.services.v2_closure_service import V2ClosureError, preview_week_closure


class V2WeeklyTrackingError(ValueError):
    pass


def _pct(value: float, total: float) -> float:
    return round(value / total * 100.0, 1) if total else 0.0


def _area_summary(rows: list[dict[str, Any]]) -> list[dict[str, Any]]:
    grouped: dict[str, dict[str, Any]] = defaultdict(lambda: {
        "area_codigo": "SIN ÁREA",
        "area_nombre": "",
        "programadas": 0,
        "finalizadas": 0,
        "pendientes": 0,
        "sin_coincidencia": 0,
        "hh_programadas": 0.0,
        "hh_finalizadas": 0.0,
        "hh_pendientes": 0.0,
    })
    for row in rows:
        key = str(row.get("area_codigo") or "SIN ÁREA")
        item = grouped[key]
        item["area_codigo"] = key
        item["area_nombre"] = row.get("area_nombre") or item["area_nombre"]
        hh = float(row.get("hh_programadas") or row.get("hh") or 0)
        item["programadas"] += 1
        item["hh_programadas"] += hh
        if row.get("finalizado") is True:
            item["finalizadas"] += 1
            item["hh_finalizadas"] += hh
        elif row.get("finalizado") is False:
            item["pendientes"] += 1
            item["hh_pendientes"] += hh
        else:
            item["sin_coincidencia"] += 1
    result = []
    for item in grouped.values():
        item["hh_programadas"] = round(item["hh_programadas"], 2)
        item["hh_finalizadas"] = round(item["hh_finalizadas"], 2)
        item["hh_pendientes"] = round(item["hh_pendientes"], 2)
        item["avance_ot_pct"] = _pct(item["finalizadas"], item["programadas"])
        item["avance_hh_pct"] = _pct(item["hh_finalizadas"], item["hh_programadas"])
        result.append(item)
    return sorted(result, key=lambda row: (-row["programadas"], row["area_codigo"]))


def get_week_tracking(programming_id: int) -> dict[str, Any]:
    with get_engine().connect() as conn:
        programming = conn.execute(text("""
            SELECT id,semana_inicio,semana_fin,especialidad,estado
            FROM programacion.programacion_semanal_v2
            WHERE id=:id
        """), {"id": programming_id}).mappings().first()
        if not programming:
            raise V2WeeklyTrackingError("Programación semanal no encontrada")

        history = [dict(row) for row in conn.execute(text("""
            SELECT id,archivo_nombre,registrado_por,registrado_en,total_items,
                   finalizados,pendientes,sin_coincidencia,
                   hh_programadas,hh_finalizadas,hh_pendientes,
                   avance_ot_pct,avance_hh_pct
            FROM programacion.seguimiento_semanal_v2
            WHERE programacion_id=:id
            ORDER BY registrado_en DESC,id DESC
            LIMIT 30
        """), {"id": programming_id}).mappings()]

        latest_rows: list[dict[str, Any]] = []
        if history:
            latest_id = int(history[0]["id"])
            latest_rows = [dict(row) for row in conn.execute(text("""
                SELECT s.programacion_item_id,s.orden_mantenimiento_id,s.numero_ot,
                       s.area_codigo,s.area_nombre,s.hh_programadas,
                       s.estado_calendario,s.finalizado,s.coincidencia,
                       a.codigo AS activo_codigo,a.descripcion AS activo_descripcion,
                       p.plan_trabajo,p.descripcion_grupo
                FROM programacion.seguimiento_semanal_item_v2 s
                JOIN programacion.orden_mantenimiento o ON o.id=s.orden_mantenimiento_id
                JOIN programacion.activo a ON a.id=o.activo_id
                LEFT JOIN programacion.plan_trabajo p ON p.id=o.plan_trabajo_id
                WHERE s.seguimiento_id=:tracking_id
                ORDER BY s.finalizado DESC NULLS LAST,s.area_codigo,s.numero_ot NULLS LAST,a.codigo
            """), {"tracking_id": latest_id}).mappings()]

    for row in history:
        for key in ("hh_programadas", "hh_finalizadas", "hh_pendientes",
                    "avance_ot_pct", "avance_hh_pct"):
            row[key] = float(row[key] or 0)

    return {
        "programming": dict(programming),
        "latest": history[0] if history else None,
        "history": history,
        "by_area": _area_summary(latest_rows),
        "rows": latest_rows,
    }


def record_week_tracking(
    *,
    programming_id: int,
    content: bytes,
    filename: str,
    recorded_by: str | None = None,
) -> dict[str, Any]:
    try:
        preview = preview_week_closure(programming_id=programming_id, content=content)
    except V2ClosureError as exc:
        raise V2WeeklyTrackingError(str(exc)) from exc

    if preview["programming"]["estado"] == "CERRADA":
        raise V2WeeklyTrackingError(
            "La semana ya está cerrada. El seguimiento histórico se conserva en modo consulta."
        )

    summary = preview["summary"]
    rows = preview["rows"]
    programmed = int(summary.get("programmed") or 0)
    finalized = int(summary.get("finalized") or 0)
    pending = int(summary.get("pending") or 0)
    unmatched = int(summary.get("not_found") or 0)
    hh_programmed = round(float(summary.get("hh_programmed") or 0), 2)
    hh_finalized = round(float(summary.get("hh_finalized") or 0), 2)
    hh_pending = round(float(summary.get("hh_pending") or 0), 2)
    ot_pct = _pct(finalized, programmed)
    hh_pct = _pct(hh_finalized, hh_programmed)

    with get_engine().begin() as conn:
        tracking_id = conn.execute(text("""
            INSERT INTO programacion.seguimiento_semanal_v2(
              programacion_id,archivo_nombre,registrado_por,
              total_items,finalizados,pendientes,sin_coincidencia,
              hh_programadas,hh_finalizadas,hh_pendientes,
              avance_ot_pct,avance_hh_pct
            ) VALUES(
              :programming_id,:filename,:recorded_by,
              :programmed,:finalized,:pending,:unmatched,
              :hh_programmed,:hh_finalized,:hh_pending,
              :ot_pct,:hh_pct
            )
            RETURNING id
        """), {
            "programming_id": programming_id,
            "filename": filename,
            "recorded_by": recorded_by,
            "programmed": programmed,
            "finalized": finalized,
            "pending": pending,
            "unmatched": unmatched,
            "hh_programmed": hh_programmed,
            "hh_finalized": hh_finalized,
            "hh_pending": hh_pending,
            "ot_pct": ot_pct,
            "hh_pct": hh_pct,
        }).scalar_one()

        if rows:
            payload = [{
                "tracking_id": tracking_id,
                "program_item_id": int(row["programacion_item_id"]),
                "order_id": int(row["orden_mantenimiento_id"]),
                "numero_ot": row.get("numero_ot"),
                "area_codigo": row.get("area_codigo"),
                "area_nombre": row.get("area_nombre"),
                "hh": float(row.get("hh") or 0),
                "state": row.get("estado_excel"),
                "finalized": row.get("finalizado"),
                "match": row.get("coincidencia"),
            } for row in rows]
            conn.execute(text("""
                INSERT INTO programacion.seguimiento_semanal_item_v2(
                  seguimiento_id,programacion_item_id,orden_mantenimiento_id,
                  numero_ot,area_codigo,area_nombre,hh_programadas,
                  estado_calendario,finalizado,coincidencia
                ) VALUES(
                  :tracking_id,:program_item_id,:order_id,
                  :numero_ot,:area_codigo,:area_nombre,:hh,
                  :state,:finalized,:match
                )
            """), payload)

    result = get_week_tracking(programming_id)
    result["saved"] = {
        "tracking_id": int(tracking_id),
        "archivo": filename,
        "finalizadas": finalized,
        "pendientes": pending,
        "sin_coincidencia": unmatched,
        "avance_ot_pct": ot_pct,
        "avance_hh_pct": hh_pct,
    }
    return result
