from __future__ import annotations

from calendar import monthrange
from datetime import date
from typing import Any

from sqlalchemy import text

from backend.database import get_engine
from backend.services.v2_monthly_calendar_import import import_monthly_calendar


FINAL_STATES = {"CERRADO", "CERRADA", "COMPLETADO", "COMPLETADA"}


def _is_pending_sql(alias: str = "o") -> str:
    return (
        f"NOT (upper(btrim(COALESCE({alias}.estado,''))) LIKE 'FINALIZ%' "
        f"OR upper(btrim(COALESCE({alias}.estado,''))) IN "
        "('CERRADO','CERRADA','COMPLETADO','COMPLETADA'))"
    )


def bootstrap_initial_backlog(
    *,
    content: bytes,
    filename: str,
    year: int,
    month: int,
    moved_by: str | None = None,
) -> dict[str, Any]:
    """Carga única de arranque: importa el calendario histórico y lleva solo pendientes a backlog.

    No crea programación semanal ni realiza un cierre. Es idempotente por orden:
    si una OT ya está en backlog no se duplica.
    """
    if not 2020 <= year <= 2100 or not 1 <= month <= 12:
        raise ValueError("Período inválido")

    import_result = import_monthly_calendar(
        monthly_content=content,
        year=year,
        month=month,
    )
    period = date(year, month, 1)
    period_end = date(year, month, monthrange(year, month)[1])
    pending_sql = _is_pending_sql("o")
    reason = "ARRASTRE INICIAL CIERRE MENSUAL"

    with get_engine().begin() as conn:
        pending_detected = int(conn.execute(text(f"""
            SELECT count(*)
            FROM programacion.orden_mantenimiento o
            LEFT JOIN programacion.plan_trabajo p ON p.id=o.plan_trabajo_id
            WHERE o.periodo=:period
              AND COALESCE(p.es_operacion,false)=false
              AND {pending_sql}
        """), {"period": period}).scalar_one() or 0)

        conn.execute(text(f"""
            INSERT INTO programacion.backlog_v2(
              orden_mantenimiento_id,programacion_origen_id,
              semana_origen_inicio,semana_origen_fin,
              especialidad,motivo,movido_por,movido_en,actualizado_en,
              estado_seguimiento,primera_semana_origen_inicio,primera_semana_origen_fin,
              ultimo_resultado_cierre,ultima_programacion_id
            )
            SELECT
              o.id,NULL,:period_end,:period_end,
              CASE
                WHEN upper(btrim(COALESCE(o.especialidad,''))) IN ('MEC','ELE','MET','SER')
                THEN upper(btrim(o.especialidad))
                ELSE 'SIN'
              END,
              :reason,:moved_by,now(),now(),
              'PENDIENTE_DISPONIBLE',:period_end,:period_end,
              'PENDIENTE',NULL
            FROM programacion.orden_mantenimiento o
            LEFT JOIN programacion.plan_trabajo p ON p.id=o.plan_trabajo_id
            WHERE o.periodo=:period
              AND COALESCE(p.es_operacion,false)=false
              AND {pending_sql}
            ON CONFLICT(orden_mantenimiento_id) DO NOTHING
        """), {
            "period": period,
            "period_end": period_end,
            "reason": reason,
            "moved_by": moved_by or "CARGA INICIAL",
        })

        initial_total = int(conn.execute(text("""
            SELECT count(*)
            FROM programacion.backlog_v2 b
            JOIN programacion.orden_mantenimiento o ON o.id=b.orden_mantenimiento_id
            WHERE o.periodo=:period
              AND b.motivo=:reason
              AND b.estado_seguimiento<>'FINALIZADA'
        """), {"period": period, "reason": reason}).scalar_one() or 0)

        by_specialty = [
            dict(row)
            for row in conn.execute(text("""
                SELECT b.especialidad,count(*)::int AS cantidad
                FROM programacion.backlog_v2 b
                JOIN programacion.orden_mantenimiento o ON o.id=b.orden_mantenimiento_id
                WHERE o.periodo=:period
                  AND b.motivo=:reason
                  AND b.estado_seguimiento<>'FINALIZADA'
                GROUP BY b.especialidad
                ORDER BY b.especialidad
            """), {"period": period, "reason": reason}).mappings()
        ]

    return {
        "ok": True,
        "archivo": filename,
        "periodo": str(period),
        "periodo_fin": str(period_end),
        "pendientes_detectadas": pending_detected,
        "backlog_inicial_activo": initial_total,
        "por_especialidad": by_specialty,
        "importacion": import_result,
        "mensaje": (
            f"Se dejó un backlog inicial de {initial_total} OT pendientes del período "
            f"{year}-{month:02d}. Las cargas semanales siguientes continuarán alimentando "
            "la misma cola mediante el Cierre semanal."
        ),
    }
