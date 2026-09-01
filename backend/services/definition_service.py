from __future__ import annotations

from typing import Any

from sqlalchemy import text

from backend.database import get_engine

VALID_CONDITIONS={
    "OPERANDO",
    "EQUIPO DETENIDO",
    "LINEA DETENIDA",
    "AREA/PLANTA DETENIDA",
}


class DefinitionError(ValueError):
    pass


def get_pending_definitions(*,year:int,month:int,specialty:str|None=None)->list[dict[str,Any]]:
    filters=[
        "v.anio=:year",
        "v.mes=:month",
        "v.estado_orden<>'FINALIZADA'",
        "NOT v.datos_completos",
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
      COUNT(*)::int AS pmp_afectados,
      COUNT(DISTINCT v.activo_id)::int AS equipos_afectados,
      BOOL_OR('TIEMPO'=ANY(v.datos_faltantes)) AS falta_tiempo,
      BOOL_OR('PERSONAS'=ANY(v.datos_faltantes)) AS falta_personas,
      BOOL_OR('CONDICION'=ANY(v.datos_faltantes)) AS falta_condicion,
      pt.tiempo_ejecucion_min,
      COALESCE(cp.personas_usar,pt.personas_defecto) AS personas_usar,
      COALESCE(cp.condicion,'SIN CLASIFICAR') AS condicion,
      MIN(v.area_nombre) AS area_ejemplo,
      MIN(v.activo_codigo) AS equipo_ejemplo
    FROM mantenimiento.vw_pmp_calculado v
    JOIN mantenimiento.plan_trabajo pt ON pt.id=v.plan_trabajo_id
    LEFT JOIN mantenimiento.clasificacion_plan cp ON cp.plan_trabajo_id=v.plan_trabajo_id
    WHERE {' AND '.join(filters)}
    GROUP BY
      v.plan_trabajo_id,v.especialidad,v.plan_trabajo,
      pt.tiempo_ejecucion_min,cp.personas_usar,pt.personas_defecto,cp.condicion
    ORDER BY
      CASE v.especialidad WHEN 'MEC' THEN 1 WHEN 'ELE' THEN 2 WHEN 'SER' THEN 3 ELSE 4 END,
      v.plan_trabajo
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
    if condition is not None:
        condition=condition.upper()
        if condition not in VALID_CONDITIONS:
            raise DefinitionError("Condición inválida")

    if execution_minutes is None and people is None and condition is None:
        raise DefinitionError("No se recibió ningún dato para definir")

    with get_engine().begin() as conn:
        plan=conn.execute(text("""SELECT id,tiempo_ejecucion_min,personas_defecto
          FROM mantenimiento.plan_trabajo WHERE id=:id AND activo=true"""),{"id":plan_id}).mappings().one_or_none()
        if not plan:
            raise DefinitionError("Plan de trabajo no encontrado")

        if execution_minutes is not None and plan["tiempo_ejecucion_min"] is None:
            conn.execute(text("""UPDATE mantenimiento.plan_trabajo
              SET tiempo_ejecucion_min=:t,actualizado_por=:u
              WHERE id=:id"""),{"t":execution_minutes,"u":updated_by,"id":plan_id})

        if people is not None or condition is not None:
            current=conn.execute(text("""SELECT condicion,personas_usar
              FROM mantenimiento.clasificacion_plan WHERE plan_trabajo_id=:id"""),{"id":plan_id}).mappings().one_or_none()

            if current:
                fallback_condition=current["condicion"]
                fallback_people=current["personas_usar"]
            else:
                fallback_condition="SIN CLASIFICAR"
                fallback_people=plan["personas_defecto"]

            next_condition=condition or fallback_condition
            next_people=people if people is not None else fallback_people

            conn.execute(text("""INSERT INTO mantenimiento.clasificacion_plan(
                plan_trabajo_id,condicion,personas_usar,observacion,actualizado_por,fuente
              ) VALUES(:id,:c,:p,'Definido desde Pendientes por definir',:u,'USUARIO')
              ON CONFLICT(plan_trabajo_id) DO UPDATE SET
                condicion=EXCLUDED.condicion,
                personas_usar=EXCLUDED.personas_usar,
                observacion=EXCLUDED.observacion,
                actualizado_por=EXCLUDED.actualizado_por,
                fuente='USUARIO',
                actualizado_en=now()"""),
              {"id":plan_id,"c":next_condition,"p":next_people,"u":updated_by})

    return {"ok":True,"plan_id":plan_id}
