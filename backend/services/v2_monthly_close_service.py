from __future__ import annotations

from datetime import date
import json
from typing import Any

from sqlalchemy import text

from backend.database import get_engine
from backend.services.v2_progress_service import get_progress


class V2MonthlyCloseError(ValueError):
    pass


def _period(year: int, month: int) -> tuple[date, date]:
    if not 2020 <= year <= 2100 or not 1 <= month <= 12:
        raise V2MonthlyCloseError("Periodo inválido")
    begin = date(year, month, 1)
    end = date(year + 1, 1, 1) if month == 12 else date(year, month + 1, 1)
    return begin, end


def _requirements(progress: dict[str, Any], end: date) -> list[dict[str, Any]]:
    monthly = progress.get("monthly") or {}
    weeks_total = int(monthly.get("weeks_total") or 0)
    weeks_closed = int(monthly.get("weeks_closed") or 0)
    unchecked = int(monthly.get("unchecked") or 0)
    not_found = int(monthly.get("not_found") or 0)

    return [
        {
            "id": "period_finished",
            "label": "Período finalizado",
            "ok": date.today() >= end,
            "detail": (
                "El mes ya terminó y puede formalizarse."
                if date.today() >= end
                else "El cierre formal se habilita cuando termine el mes."
            ),
        },
        {
            "id": "has_programming",
            "label": "Programación registrada",
            "ok": weeks_total > 0,
            "detail": (
                f"{weeks_total} programación(es) registrada(s)."
                if weeks_total
                else "Aún no existen programaciones semanales para el período."
            ),
        },
        {
            "id": "weeks_closed",
            "label": "Semanas cerradas",
            "ok": weeks_total > 0 and weeks_closed == weeks_total,
            "detail": f"{weeks_closed} de {weeks_total} programación(es) cerrada(s).",
        },
        {
            "id": "reconciled",
            "label": "Conciliación completa",
            "ok": unchecked == 0 and not_found == 0,
            "detail": (
                "No hay actividades sin verificar ni no encontradas."
                if unchecked == 0 and not_found == 0
                else f"{unchecked} sin verificar · {not_found} no encontrada(s)."
            ),
        },
    ]


def get_monthly_close(year: int, month: int) -> dict[str, Any]:
    begin, end = _period(year, month)
    progress = get_progress(year, month)
    requirements = _requirements(progress, end)
    ready = all(item["ok"] for item in requirements)

    with get_engine().connect() as conn:
        row = conn.execute(text("""
            SELECT periodo,estado,cerrado_en,cerrado_por,resumen,actualizado_en
            FROM programacion.cierre_mensual_v2
            WHERE periodo=:period
        """), {"period": begin}).mappings().first()

    record = dict(row) if row else {
        "periodo": begin,
        "estado": "ABIERTO",
        "cerrado_en": None,
        "cerrado_por": None,
        "resumen": None,
        "actualizado_en": None,
    }
    if record.get("periodo") is not None:
        record["periodo"] = str(record["periodo"])
    for key in ("cerrado_en", "actualizado_en"):
        if record.get(key) is not None:
            record[key] = record[key].isoformat()

    return {
        "year": year,
        "month": month,
        "period": str(begin),
        "period_end": str(end),
        "ready_to_close": ready and record["estado"] != "CERRADO",
        "is_closed": record["estado"] == "CERRADO",
        "requirements": requirements,
        "record": record,
        "progress": progress,
    }


def close_month(year: int, month: int, closed_by: str | None = None) -> dict[str, Any]:
    begin, end = _period(year, month)
    progress = get_progress(year, month)
    requirements = _requirements(progress, end)
    blockers = [item for item in requirements if not item["ok"]]
    if blockers:
        reasons = "; ".join(item["detail"] for item in blockers)
        raise V2MonthlyCloseError(f"No se puede cerrar el mes: {reasons}")

    monthly = progress.get("monthly") or {}
    totals = progress.get("weekly_totals") or {}
    snapshot = {
        "monthly": monthly,
        "weekly_totals": totals,
        "unresolved_count": len(progress.get("unresolved") or []),
        "closed_at": date.today().isoformat(),
    }

    with get_engine().begin() as conn:
        conn.execute(text("""
            INSERT INTO programacion.cierre_mensual_v2(
                periodo,estado,cerrado_en,cerrado_por,resumen,actualizado_en
            ) VALUES(
                :period,'CERRADO',now(),:closed_by,CAST(:summary AS jsonb),now()
            )
            ON CONFLICT(periodo) DO UPDATE SET
                estado='CERRADO',
                cerrado_en=COALESCE(programacion.cierre_mensual_v2.cerrado_en,now()),
                cerrado_por=COALESCE(programacion.cierre_mensual_v2.cerrado_por,EXCLUDED.cerrado_por),
                resumen=COALESCE(programacion.cierre_mensual_v2.resumen,EXCLUDED.resumen),
                actualizado_en=now()
        """), {
            "period": begin,
            "closed_by": closed_by or "Aplicación",
            "summary": json.dumps(snapshot, ensure_ascii=False, default=str),
        })

    return get_monthly_close(year, month)
