from __future__ import annotations

from typing import Any

from sqlalchemy import text

from backend.database import get_engine

VALID_CONDITIONS={"OPERANDO","EQUIPO DETENIDO"}


class DefinitionError(ValueError):
    pass


def get_pending_definitions(*,year:int,month:int,specialty:str|None=None)->list[dict[str,Any]]:
    filters=[
        "v.anio=:year",
        "v.mes=:month",
        "v.estado_orden<>'FINALIZADA'",
        "('PERSONAS'=ANY(v.datos_faltantes) OR 'CONDICION'=ANY(v.datos_faltantes))",
    ]
    params={"year":year,"month":month}
    if specialty:
        filters.append("v.especialidad=:specialty")
        params["specialty"]=specialty.upper()

    sql=f"""
    SELECT
      v.plan_trabajo_id,
      v.especialidad,
      v.plan_trabajo,
      COALESCE(g.nombre,'SIN GRUPO') AS descripcion_grupo,
      COUNT(*)::int AS pmp_afectados,
      COUNT(DISTINCT v.activo_id)::int AS equipos_afectados,
      BOOL_OR('PERSONAS'=ANY(v.datos_faltantes)) AS falta_personas,
      BOOL_OR('CONDICION'=ANY(v.datos_faltantes)) AS falta_condicion,
      pt.numero_personas AS personas_usar,
      CASE
        WHEN pt.equipo_detenido IS TRUE THEN 'EQUIPO DETENIDO'
        WHEN pt.equipo_detenido IS FALSE THEN 'OPERANDO'
        ELSE 'SIN CLASIFICAR'
      END AS condicion,
      MIN(v.area_nombre) AS area_ejemplo,
      MIN(v.activo_codigo) AS equipo_ejemplo
    FROM mantenimiento.vw_pmp_calculado v
    JOIN mantenimiento.plan_trabajo pt ON pt.id=v.plan_trabajo_id
    LEFT JOIN mantenimiento.grupo_plan_trabajo g ON g.id=pt.grupo_id
    WHERE {' AND '.join(filters)}
    GROUP BY
      v.plan_trabajo_id,v.especialidad,v.plan_trabajo,g.nombre,
      pt.numero_personas,pt.equipo_detenido
    ORDER BY
      CASE v.especialidad WHEN 'MEC' THEN 1 WHEN 'ELE' THEN 2 WHEN 'SER' THEN 3 ELSE 4 END,
      g.nombre,v.plan_trabajo
    """
    with get_engine().connect() as conn:
        return [dict(r) for r in conn.execute(text(sql),params).mappings().all()]


def define_plan(
    *,
    plan_id:int,
    execution_minutes:float|None=None,
    people:float|None=None,
    condition:str|None=None,
    updated_by:str="PRUEBA_WEB",
)->dict[str,Any]:
    if execution_minutes is not None and execution_minutes<=0:
        raise DefinitionError("El tiempo debe ser mayor que cero")
    if people is not None and people<=0:
        raise DefinitionError("El número de personas debe ser mayor que cero")

    equipment_stopped=None
    if condition is not None:
        condition=condition.upper()
        if condition not in VALID_CONDITIONS:
            raise DefinitionError("Condición inválida")
        equipment_stopped=condition=="EQUIPO DETENIDO"

    if execution_minutes is None and people is None and condition is None:
        raise DefinitionError("No se recibió ningún dato para definir")

    with get_engine().begin() as conn:
        plan=conn.execute(text("""SELECT id,tiempo_ejecucion_min,numero_personas,equipo_detenido
          FROM mantenimiento.plan_trabajo
          WHERE id=:id AND activo=true"""),{"id":plan_id}).mappings().one_or_none()
        if not plan:
            raise DefinitionError("Plan de trabajo no encontrado")

        conn.execute(text("""UPDATE mantenimiento.plan_trabajo
          SET
            tiempo_ejecucion_min=CASE
              WHEN :t IS NOT NULL AND tiempo_ejecucion_min IS NULL THEN :t
              ELSE tiempo_ejecucion_min
            END,
            numero_personas=COALESCE(:p,numero_personas),
            equipo_detenido=COALESCE(:ed,equipo_detenido),
            actualizado_por=:u
          WHERE id=:id"""),
          {"t":execution_minutes,"p":people,"ed":equipment_stopped,"u":updated_by,"id":plan_id})

        saved=conn.execute(text("""SELECT
            id AS plan_id,
            numero_personas,
            equipo_detenido,
            CASE
              WHEN equipo_detenido IS TRUE THEN 'EQUIPO DETENIDO'
              WHEN equipo_detenido IS FALSE THEN 'OPERANDO'
              ELSE 'SIN CLASIFICAR'
            END AS condicion
          FROM mantenimiento.plan_trabajo
          WHERE id=:id"""),{"id":plan_id}).mappings().one()

    return {
        "ok":True,
        "master_source":"SUPABASE",
        **dict(saved),
    }
