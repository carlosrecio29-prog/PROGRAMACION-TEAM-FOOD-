CREATE OR REPLACE VIEW mantenimiento.vw_pmp_calculado
WITH (security_invoker=true) AS
SELECT
  p.id AS pmp_id,
  pm.anio,
  pm.mes,
  p.activo_id,
  a.codigo AS activo_codigo,
  a.descripcion AS activo_descripcion,
  a.area_nombre,
  a.linea_nombre,
  a.criticidad,
  p.plan_trabajo_id,
  pt.nombre AS plan_trabajo,
  COALESCE(gpt.nombre,'SIN GRUPO') AS grupo_plan,
  e.codigo AS especialidad,
  (
    CASE
      WHEN pt.equipo_detenido IS TRUE THEN 'EQUIPO DETENIDO'
      WHEN pt.equipo_detenido IS FALSE THEN 'OPERANDO'
      ELSE 'SIN CLASIFICAR'
    END
  )::varchar AS condicion,
  pt.numero_personas::numeric(8,2) AS personas_usar,
  COALESCE(p.tiempo_planeado_min,pt.tiempo_ejecucion_min)::numeric(12,2) AS tiempo_planeado_min,
  CASE
    WHEN COALESCE(p.tiempo_planeado_min,pt.tiempo_ejecucion_min) IS NULL
      OR pt.numero_personas IS NULL
    THEN NULL::numeric
    ELSE COALESCE(p.tiempo_planeado_min,pt.tiempo_ejecucion_min) / 60.0
      * pt.numero_personas
  END AS hh_pmp,
  COALESCE(p.tiempo_planeado_min,pt.tiempo_ejecucion_min) IS NOT NULL
    AND COALESCE(p.tiempo_planeado_min,pt.tiempo_ejecucion_min) > 0
    AND pt.numero_personas IS NOT NULL
    AND pt.equipo_detenido IS NOT NULL AS datos_completos,
  array_remove(ARRAY[
    CASE
      WHEN COALESCE(p.tiempo_planeado_min,pt.tiempo_ejecucion_min) IS NULL
        OR COALESCE(p.tiempo_planeado_min,pt.tiempo_ejecucion_min) <= 0
      THEN 'TIEMPO'::text ELSE NULL::text
    END,
    CASE
      WHEN pt.numero_personas IS NULL
      THEN 'PERSONAS'::text ELSE NULL::text
    END,
    CASE
      WHEN pt.equipo_detenido IS NULL
      THEN 'CONDICION'::text ELSE NULL::text
    END
  ],NULL::text) AS datos_faltantes,
  om.id AS orden_id,
  om.numero_orden,
  COALESCE(om.estado,'PENDIENTE') AS estado_orden
FROM mantenimiento.pmp p
JOIN mantenimiento.periodo_mensual pm ON pm.id=p.periodo_mensual_id
JOIN mantenimiento.activo a ON a.id=p.activo_id
JOIN mantenimiento.plan_trabajo pt ON pt.id=p.plan_trabajo_id
LEFT JOIN mantenimiento.grupo_plan_trabajo gpt ON gpt.id=pt.grupo_id
JOIN mantenimiento.especialidad e ON e.id=p.especialidad_id
LEFT JOIN mantenimiento.orden_mantenimiento om ON om.pmp_id=p.id;

CREATE OR REPLACE VIEW mantenimiento.vw_catalogo_actividades_planta
WITH (security_invoker=true) AS
SELECT
  am.id AS actividad_maestra_id,
  e.codigo AS especialidad,
  g.nombre AS grupo_ruta,
  pt.id AS plan_trabajo_id,
  pt.nombre AS plan_trabajo,
  pt.nombre_canonico,
  a.id AS activo_id,
  a.codigo AS activo_codigo,
  a.descripcion AS activo_descripcion,
  a.area_nombre,
  a.linea_nombre,
  a.criticidad,
  pt.numero_personas::numeric(8,2) AS personas_requeridas,
  pt.tiempo_ejecucion_min::numeric(12,2) AS tiempo_estandar_min,
  CASE
    WHEN pt.tiempo_ejecucion_min IS NULL OR pt.numero_personas IS NULL
    THEN NULL::numeric
    ELSE pt.tiempo_ejecucion_min/60.0 * pt.numero_personas
  END AS hh_estandar,
  am.fuente_datos,
  am.activo
FROM mantenimiento.actividad_maestra am
JOIN mantenimiento.activo a ON a.id=am.activo_id
JOIN mantenimiento.plan_trabajo pt ON pt.id=am.plan_trabajo_id
JOIN mantenimiento.especialidad e ON e.id=am.especialidad_id
LEFT JOIN mantenimiento.grupo_plan_trabajo g ON g.id=pt.grupo_id;

CREATE OR REPLACE VIEW mantenimiento.vw_maestro_planes
WITH (security_invoker=true) AS
SELECT
  pt.id AS plan_trabajo_id,
  e.codigo AS especialidad,
  COALESCE(g.nombre,'SIN GRUPO') AS descripcion_grupo,
  pt.nombre AS plan_trabajo,
  pt.tiempo_ejecucion_min,
  pt.numero_personas,
  CASE
    WHEN pt.equipo_detenido IS TRUE THEN 'SI'
    WHEN pt.equipo_detenido IS FALSE THEN 'NO'
    ELSE NULL
  END::varchar AS equipo_detenido,
  pt.tiempo_parada_min,
  pt.activo,
  pt.fuente_maestra,
  pt.actualizado_por
FROM mantenimiento.plan_trabajo pt
JOIN mantenimiento.especialidad e ON e.id=pt.especialidad_id
LEFT JOIN mantenimiento.grupo_plan_trabajo g ON g.id=pt.grupo_id;

ALTER VIEW mantenimiento.vw_backlog SET (security_invoker=true);
ALTER VIEW mantenimiento.vw_hh_tecnico_dia SET (security_invoker=true);

DROP TABLE IF EXISTS mantenimiento.clasificacion_plan_activo;
DROP TABLE IF EXISTS mantenimiento.clasificacion_plan;
DROP TABLE IF EXISTS mantenimiento.plan_trabajo_alias;

ALTER TABLE mantenimiento.actividad_maestra
  DROP COLUMN IF EXISTS personas_requeridas,
  DROP COLUMN IF EXISTS tiempo_estandar_min;

ALTER TABLE mantenimiento.plan_trabajo
  DROP COLUMN IF EXISTS personas_defecto;

COMMENT ON TABLE mantenimiento.plan_trabajo IS
  'Maestro canónico de PLAN DE TRABAJO de TEAM FOOD. NumeroPersonas y EquipoDetenido se aprenden aquí.';
COMMENT ON TABLE mantenimiento.actividad_maestra IS
  'Relación Activo-PlanTrabajo proveniente de la hoja PLANEACION.';
COMMENT ON TABLE mantenimiento.pmp IS
  'PMP/órdenes del periodo mensual que se usarán para programación.';
COMMENT ON TABLE mantenimiento.programacion_tecnico IS
  'Turno diario de cada técnico, base para calcular H-H disponibles.';
COMMENT ON TABLE mantenimiento.programacion_semanal IS
  'Cabecera de la programación semanal por especialidad.';
