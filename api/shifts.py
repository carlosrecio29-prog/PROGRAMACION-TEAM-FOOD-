from __future__ import annotations

from datetime import date

from fastapi import FastAPI, HTTPException, Query
from pydantic import BaseModel, Field
from sqlalchemy import text

from backend.database import get_engine

app = FastAPI(title="Programación Team Food · Turnos")


class ShiftHoursUpdate(BaseModel):
    hours: float = Field(ge=0, le=24)


@app.get("/api/v2/shifts")
def list_shifts(
    year: int = Query(..., ge=2020, le=2100),
    month: int = Query(..., ge=1, le=12),
):
    period = date(year, month, 1)
    with get_engine().connect() as conn:
        rows = [
            dict(row)
            for row in conn.execute(
                text(
                    """
                    SELECT
                      c.codigo,
                      c.horas,
                      c.es_ausencia,
                      c.activo,
                      c.actualizado_en,
                      count(pt.id) FILTER (
                        WHERE date_trunc('month', pt.fecha)::date = :period
                      ) AS registros_mes,
                      count(DISTINCT pt.tecnico_id) FILTER (
                        WHERE date_trunc('month', pt.fecha)::date = :period
                      ) AS tecnicos_mes
                    FROM programacion.turno_config c
                    LEFT JOIN programacion.programacion_tecnico pt
                      ON pt.turno_codigo = c.codigo
                    GROUP BY c.codigo, c.horas, c.es_ausencia, c.activo, c.actualizado_en
                    ORDER BY c.es_ausencia, c.codigo
                    """
                ),
                {"period": period},
            ).mappings()
        ]
    return {"periodo": str(period), "shifts": rows}


@app.patch("/api/v2/shifts/{shift_code}")
def update_shift_hours(shift_code: str, body: ShiftHoursUpdate):
    code = shift_code.strip()
    if not code:
        raise HTTPException(422, "Código de turno inválido")

    with get_engine().begin() as conn:
        row = conn.execute(
            text(
                """
                UPDATE programacion.turno_config
                   SET horas = :hours,
                       actualizado_en = now()
                 WHERE codigo = :code
                 RETURNING codigo, horas, es_ausencia, activo, actualizado_en
                """
            ),
            {"hours": body.hours, "code": code},
        ).mappings().first()
        if not row:
            raise HTTPException(404, "Turno no encontrado")

        affected = conn.execute(
            text(
                """
                SELECT count(*)
                  FROM programacion.programacion_tecnico
                 WHERE turno_codigo = :code
                   AND tipo_dia = 'TRABAJO'
                """
            ),
            {"code": code},
        ).scalar_one()

    return {"ok": True, "shift": dict(row), "schedule_rows_updated": int(affected)}
