CREATE OR REPLACE VIEW mantenimiento.vw_pmp_calculado
WITH (security_invoker = true)
AS
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
  COALESCE(gpt.nombre, 'SIN GRUPO') AS grupo_plan,
  e.codigo AS especialidad,
  COALESCE(cpa.condicion, cp.condicion, 'SIN CLASIFICAR') AS condicion,
  COALESCE(cpa.personas_usar, cp.personas_usar, pt.personas_defecto) AS personas_usar,
  COALESCE(p.tiempo_planeado_min, pt.tiempo_ejecucion_min) AS tiempo_planeado_min,
  CASE
    WHEN COALESCE(p.tiempo_planeado_min, pt.tiempo_ejecucion_min) IS NULL
      OR COALESCE(cpa.personas_usar, cp.personas_usar, pt.personas_defecto) IS NULL
    THEN NULL
    ELSE (COALESCE(p.tiempo_planeado_min, pt.tiempo_ejecucion_min) / 60.0)
      * COALESCE(cpa.personas_usar, cp.personas_usar, pt.personas_defecto)
  END AS hh_pmp,
  (
    COALESCE(p.tiempo_planeado_min, pt.tiempo_ejecucion_min) IS NOT NULL
    AND COALESCE(p.tiempo_planeado_min, pt.tiempo_ejecucion_min) > 0
    AND COALESCE(cpa.personas_usar, cp.personas_usar, pt.personas_defecto) IS NOT NULL
    AND COALESCE(cpa.condicion, cp.condicion, 'SIN CLASIFICAR') <> 'SIN CLASIFICAR'
  ) AS datos_completos,
  array_remove(ARRAY[
    CASE
      WHEN COALESCE(p.tiempo_planeado_min, pt.tiempo_ejecucion_min) IS NULL
        OR COALESCE(p.tiempo_planeado_min, pt.tiempo_ejecucion_min) <= 0
      THEN 'TIEMPO'
    END,
    CASE
      WHEN COALESCE(cpa.personas_usar, cp.personas_usar, pt.personas_defecto) IS NULL
      THEN 'PERSONAS'
    END,
    CASE
      WHEN COALESCE(cpa.condicion, cp.condicion, 'SIN CLASIFICAR') = 'SIN CLASIFICAR'
      THEN 'CONDICION'
    END
  ], NULL) AS datos_faltantes,
  om.id AS orden_id,
  om.numero_orden,
  COALESCE(om.estado, 'PENDIENTE') AS estado_orden
FROM mantenimiento.pmp p
JOIN mantenimiento.periodo_mensual pm ON pm.id = p.periodo_mensual_id
JOIN mantenimiento.activo a ON a.id = p.activo_id
JOIN mantenimiento.plan_trabajo pt ON pt.id = p.plan_trabajo_id
LEFT JOIN mantenimiento.grupo_plan_trabajo gpt ON gpt.id = pt.grupo_id
JOIN mantenimiento.especialidad e ON e.id = p.especialidad_id
LEFT JOIN mantenimiento.clasificacion_plan cp ON cp.plan_trabajo_id = p.plan_trabajo_id
LEFT JOIN mantenimiento.clasificacion_plan_activo cpa
  ON cpa.plan_trabajo_id = p.plan_trabajo_id
 AND cpa.activo_id = p.activo_id
LEFT JOIN mantenimiento.orden_mantenimiento om ON om.pmp_id = p.id;
