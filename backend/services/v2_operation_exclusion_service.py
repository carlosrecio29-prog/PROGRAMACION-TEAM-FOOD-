from __future__ import annotations

from datetime import date
from typing import Any

from sqlalchemy import text

from backend.database import get_engine


def get_operation_exclusions(*, year: int, month: int) -> dict[str, Any]:
    period = date(year, month, 1)
    with get_engine().connect() as conn:
        catalog = [
            dict(row)
            for row in conn.execute(text("""
                SELECT
                  id,grupo,plan_trabajo,descripcion_plan_trabajo,especialidad,
                  habilitado,tiempo_ejecucion_min,numero_personas_efectivo,
                  tiempo_parada_efectivo_min
                FROM programacion.plan_trabajo
                WHERE es_operacion=true
                ORDER BY especialidad,grupo,plan_trabajo
            """)).mappings()
        ]

        period_rows = [
            dict(row)
            for row in conn.execute(text("""
                SELECT
                  e.periodo,e.plan_clave_software,e.especialidad,e.cantidad,
                  e.motivo,e.origen,e.actualizado_en,e.plan_trabajo_id,
                  p.grupo,p.plan_trabajo AS plan_maestro,
                  p.descripcion_plan_trabajo AS descripcion_maestro
                FROM programacion.operacion_exclusion_periodo_v2 e
                LEFT JOIN programacion.plan_trabajo p ON p.id=e.plan_trabajo_id
                WHERE e.periodo=:period
                ORDER BY e.especialidad,e.cantidad DESC,e.plan_clave_software
            """), {"period": period}).mappings()
        ]

    catalog_by_specialty: dict[str, int] = {}
    for row in catalog:
        specialty = row.get("especialidad") or "SIN DEFINIR"
        catalog_by_specialty[specialty] = catalog_by_specialty.get(specialty, 0) + 1

    period_by_specialty: dict[str, int] = {}
    for row in period_rows:
        specialty = row.get("especialidad") or "SIN DEFINIR"
        period_by_specialty[specialty] = period_by_specialty.get(specialty, 0) + int(row.get("cantidad") or 0)

    return {
        "period": str(period),
        "catalog_total": len(catalog),
        "period_total": sum(int(row.get("cantidad") or 0) for row in period_rows),
        "catalog_by_specialty": catalog_by_specialty,
        "period_by_specialty": period_by_specialty,
        "catalog": catalog,
        "period_exclusions": period_rows,
    }
