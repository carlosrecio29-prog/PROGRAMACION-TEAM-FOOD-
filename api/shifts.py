from __future__ import annotations

from datetime import date

from fastapi import FastAPI, HTTPException, Query
from pydantic import BaseModel, Field
from typing import Optional
from sqlalchemy import text

from backend.database import get_engine
from backend.services.v2_programming_service import capacity_split, refresh_open_program_capacities

app = FastAPI(title="Programación Team Food · Turnos")


ABSENCE_DAY_TYPE = {
    "VAC": "VACACION",
    "INC": "INCAPACIDAD",
    "C": "COMPENSATORIO",
    "DE": "DESCANSO",
    "PERM": "PERMISO",
}


class ShiftHoursUpdate(BaseModel):
    hours: float = Field(ge=0, le=24)
    year: Optional[int] = Field(default=None, ge=2020, le=2100)
    month: Optional[int] = Field(default=None, ge=1, le=12)


class TechnicianScheduleChange(BaseModel):
    technician_id: int = Field(ge=1)
    work_date: date
    shift_code: Optional[str] = None


class TechnicianScheduleUpdate(BaseModel):
    changes: list[TechnicianScheduleChange]


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

        params = {"code": code, "hours": body.hours}
        period_filter = ""
        if body.year is not None and body.month is not None:
            params["period"] = date(body.year, body.month, 1)
            period_filter = "AND date_trunc('month', fecha)::date = :period"
        affected = conn.execute(
            text(
                f"""
                UPDATE programacion.programacion_tecnico
                   SET horas_disponibles = :hours,
                       actualizado_en = now()
                 WHERE turno_codigo = :code
                   AND tipo_dia = 'TRABAJO'
                   {period_filter}
                """
            ),
            params,
        ).rowcount or 0
        programs_refreshed = refresh_open_program_capacities(conn)

    return {
        "ok": True,
        "shift": dict(row),
        "schedule_rows_updated": int(affected),
        "programs_refreshed": int(programs_refreshed),
    }


@app.get("/api/v2/technician-schedule")
def technician_schedule(
    year: int = Query(..., ge=2020, le=2100),
    month: int = Query(..., ge=1, le=12),
):
    period = date(year, month, 1)
    with get_engine().connect() as conn:
        shifts = [
            dict(row)
            for row in conn.execute(text("""
                SELECT codigo, horas, es_ausencia, activo
                FROM programacion.turno_config
                WHERE activo = true
                ORDER BY es_ausencia, codigo
            """)).mappings()
        ]
        technicians = [
            dict(row)
            for row in conn.execute(text("""
                SELECT
                  id, identificacion, nombre,
                  especialidad AS especialidad_software,
                  especialidad_app,
                  especialidad_efectiva AS especialidad
                FROM programacion.tecnico
                WHERE activo = true
                ORDER BY COALESCE(especialidad_efectiva,'ZZZ'), nombre
            """)).mappings()
        ]
        schedule_rows = [
            dict(row)
            for row in conn.execute(text("""
                SELECT tecnico_id, fecha, turno_codigo, tipo_dia, horas_disponibles
                FROM programacion.programacion_tecnico
                WHERE date_trunc('month', fecha)::date = :period
                ORDER BY tecnico_id, fecha
            """), {"period": period}).mappings()
        ]
        specialty_rows = [
            dict(row)
            for row in conn.execute(text("""
                SELECT
                  COALESCE(t.especialidad_efectiva,'SIN DEFINIR') AS especialidad,
                  round(COALESCE(sum(pt.horas_disponibles),0),2) AS hh_disponibles
                FROM programacion.tecnico t
                LEFT JOIN programacion.programacion_tecnico pt
                  ON pt.tecnico_id=t.id
                 AND date_trunc('month',pt.fecha)::date=:period
                WHERE t.activo=true
                GROUP BY COALESCE(t.especialidad_efectiva,'SIN DEFINIR')
                ORDER BY especialidad
            """), {"period": period}).mappings()
        ]
        pmp_rows = [
            dict(row)
            for row in conn.execute(text("""
                SELECT
                  COALESCE(o.especialidad,'SIN') AS especialidad,
                  round(COALESCE(sum(
                    COALESCE(o.tiempo_planeado_min,p.tiempo_ejecucion_min)
                    / 60.0 * p.numero_personas_efectivo
                  ) FILTER (
                    WHERE p.numero_personas_efectivo IS NOT NULL
                      AND COALESCE(o.tiempo_planeado_min,p.tiempo_ejecucion_min) IS NOT NULL
                  ),0),2) AS hh_pmp
                FROM programacion.orden_mantenimiento o
                LEFT JOIN programacion.plan_trabajo p ON p.id=o.plan_trabajo_id
                WHERE o.periodo=:period
                  AND COALESCE(p.es_operacion,false)=false
                GROUP BY COALESCE(o.especialidad,'SIN')
                ORDER BY especialidad
            """), {"period": period}).mappings()
        ]

    by_technician = {}
    totals = {}
    for row in schedule_rows:
        tid = str(row["tecnico_id"])
        by_technician.setdefault(tid, {})[row["fecha"].isoformat()] = {
            "shift_code": row["turno_codigo"],
            "day_type": row["tipo_dia"],
            "hours": float(row["horas_disponibles"] or 0),
        }
        totals[tid] = round(totals.get(tid, 0) + float(row["horas_disponibles"] or 0), 2)

    for technician in technicians:
        technician["hh_mes"] = totals.get(str(technician["id"]), 0)

    capacity_by_specialty = {
        row["especialidad"]: float(row["hh_disponibles"] or 0)
        for row in specialty_rows
    }
    pmp_by_specialty = {
        row["especialidad"]: float(row["hh_pmp"] or 0)
        for row in pmp_rows
    }

    specialties = []
    for specialty in sorted(set(capacity_by_specialty) | set(pmp_by_specialty)):
        split = capacity_split(capacity_by_specialty.get(specialty, 0))
        specialties.append({
            "specialty": specialty,
            "pmp_hours": round(pmp_by_specialty.get(specialty, 0), 2),
            **split,
        })

    return {
        "period": str(period),
        "year": year,
        "month": month,
        "shifts": shifts,
        "technicians": technicians,
        "schedule": by_technician,
        "specialties": specialties,
    }


@app.put("/api/v2/technician-schedule")
def update_technician_schedule(body: TechnicianScheduleUpdate):
    if len(body.changes) > 1000:
        raise HTTPException(422, "Demasiados cambios en una sola operación")

    updated = 0
    cleared = 0
    with get_engine().begin() as conn:
        shift_map = {
            row["codigo"]: dict(row)
            for row in conn.execute(text("""
                SELECT codigo, horas, es_ausencia, activo
                FROM programacion.turno_config
                WHERE activo = true
            """)).mappings()
        }

        valid_technicians = {
            int(row["id"])
            for row in conn.execute(text("""
                SELECT id FROM programacion.tecnico WHERE activo = true
            """)).mappings()
        }

        for change in body.changes:
            if change.technician_id not in valid_technicians:
                raise HTTPException(422, f"Técnico {change.technician_id} no válido")

            code = (change.shift_code or "").strip()
            if not code:
                conn.execute(text("""
                    DELETE FROM programacion.programacion_tecnico
                    WHERE tecnico_id=:technician_id AND fecha=:work_date
                """), {
                    "technician_id": change.technician_id,
                    "work_date": change.work_date,
                })
                cleared += 1
                continue

            shift = shift_map.get(code)
            if not shift:
                raise HTTPException(422, f"Turno {code} no válido")

            is_absence = bool(shift["es_ausencia"])
            day_type = ABSENCE_DAY_TYPE.get(code, "AUSENCIA") if is_absence else "TRABAJO"
            hours = 0.0 if is_absence else float(shift["horas"] or 0)

            conn.execute(text("""
                INSERT INTO programacion.programacion_tecnico(
                  tecnico_id,fecha,turno_codigo,tipo_dia,horas_disponibles,fila_origen,actualizado_en
                ) VALUES(
                  :technician_id,:work_date,:shift_code,:day_type,:hours,NULL,now()
                )
                ON CONFLICT (tecnico_id,fecha) DO UPDATE SET
                  turno_codigo=EXCLUDED.turno_codigo,
                  tipo_dia=EXCLUDED.tipo_dia,
                  horas_disponibles=EXCLUDED.horas_disponibles,
                  fila_origen=NULL,
                  actualizado_en=now()
            """), {
                "technician_id": change.technician_id,
                "work_date": change.work_date,
                "shift_code": code,
                "day_type": day_type,
                "hours": hours,
            })
            updated += 1

        programs_refreshed = refresh_open_program_capacities(conn)

    return {
        "ok": True,
        "updated": updated,
        "cleared": cleared,
        "processed": len(body.changes),
        "programs_refreshed": int(programs_refreshed),
    }
