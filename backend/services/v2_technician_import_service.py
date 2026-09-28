from __future__ import annotations

from datetime import date
from typing import Any

from sqlalchemy import text

from backend.database import get_engine
from backend.parsers.common import normalize_text
from backend.services.v2_import_service import _parse_technicians


def import_technician_schedule(*, content: bytes, year: int, month: int) -> dict[str, Any]:
    if not 2020 <= year <= 2100 or not 1 <= month <= 12:
        raise ValueError("Período inválido")

    technicians, schedule, warnings = _parse_technicians(content, year=year, month=month)
    if not technicians:
        raise ValueError("No se encontraron técnicos en la hoja PROGRAMACION DE TECNICOS")
    if not schedule:
        raise ValueError("No se encontraron turnos o ausencias para el período seleccionado")

    period = date(year, month, 1)
    with get_engine().begin() as conn:
        conn.execute(text("""
            INSERT INTO programacion.tecnico(
              identificacion,nombre,nombre_normalizado,especialidad,fila_origen
            ) VALUES(
              :identificacion,:nombre,:nombre_normalizado,:especialidad,:fila_origen
            )
            ON CONFLICT (nombre_normalizado) DO UPDATE SET
              identificacion=EXCLUDED.identificacion,
              nombre=EXCLUDED.nombre,
              especialidad=EXCLUDED.especialidad,
              fila_origen=EXCLUDED.fila_origen,
              actualizado_en=now()
        """), technicians)

        technician_map = {
            normalize_text(row["nombre_normalizado"]): int(row["id"])
            for row in conn.execute(text(
                "SELECT id,nombre_normalizado FROM programacion.tecnico"
            )).mappings()
        }

        db_rows = []
        missing = set()
        for row in schedule:
            tech_id = technician_map.get(normalize_text(row["nombre_normalizado"]))
            if tech_id is None:
                missing.add(row["nombre_normalizado"])
                continue
            db_rows.append({**row, "tecnico_id": tech_id})

        # Reimportar octubre reemplaza únicamente la programación de técnicos
        # de octubre. No toca otros meses ni el maestro de mantenimiento.
        deleted = conn.execute(text("""
            DELETE FROM programacion.programacion_tecnico
            WHERE date_trunc('month',fecha)::date=:period
        """), {"period": period}).rowcount or 0

        if db_rows:
            conn.execute(text("""
                INSERT INTO programacion.programacion_tecnico(
                  tecnico_id,fecha,turno_codigo,tipo_dia,horas_disponibles,fila_origen
                ) VALUES(
                  :tecnico_id,:fecha,:turno_codigo,:tipo_dia,:horas_disponibles,:fila_origen
                )
                ON CONFLICT (tecnico_id,fecha) DO UPDATE SET
                  turno_codigo=EXCLUDED.turno_codigo,
                  tipo_dia=EXCLUDED.tipo_dia,
                  horas_disponibles=EXCLUDED.horas_disponibles,
                  fila_origen=EXCLUDED.fila_origen,
                  actualizado_en=now()
            """), db_rows)

        stats = conn.execute(text("""
            SELECT
              count(*) AS registros,
              count(DISTINCT tecnico_id) AS tecnicos,
              round(COALESCE(sum(horas_disponibles),0),2) AS hh_disponibles,
              count(*) FILTER (WHERE tipo_dia <> 'TRABAJO') AS ausencias
            FROM programacion.programacion_tecnico
            WHERE date_trunc('month',fecha)::date=:period
        """), {"period": period}).mappings().one()

    return {
        "ok": True,
        "periodo": str(period),
        "tecnicos_archivo": len(technicians),
        "registros_archivo": len(schedule),
        "registros_mes_reemplazados": int(deleted),
        "tecnicos_sin_enlace": len(missing),
        **dict(stats),
        "warnings": warnings[:100],
    }
