-- Reconstruir de forma idempotente las detecciones históricas ya guardadas
-- sin modificar programaciones, cierres ni estados maestros.
WITH candidates AS (
  SELECT DISTINCT ON (o.id)
    o.id AS order_id,
    date_trunc('month',ps.semana_inicio)::date AS periodo,
    ps.especialidad,
    n.fecha_fin_orden,
    ps.id AS programming_id,
    n.primera_seguimiento_id AS tracking_id
  FROM programacion.seguimiento_no_programado_v2 n
  JOIN programacion.programacion_semanal_v2 ps ON ps.id=n.programacion_id
  JOIN programacion.orden_mantenimiento o ON (
    o.id=n.orden_mantenimiento_id
    OR (n.orden_mantenimiento_id IS NULL
        AND upper(btrim(n.numero_ot))=upper(btrim(o.numero_ot)))
  )
  JOIN programacion.plan_trabajo p ON p.id=o.plan_trabajo_id
  WHERE n.primera_seguimiento_id IS NOT NULL
    AND upper(COALESCE(n.estado_calendario,'')) LIKE 'FINALIZ%'
    AND n.fecha_fin_orden::date >= date_trunc('month',ps.semana_inicio)::date
    AND n.fecha_fin_orden::date <= ps.semana_fin
    AND o.especialidad=ps.especialidad
    AND NOT COALESCE(p.es_operacion,false)
    AND (
      o.periodo=date_trunc('month',ps.semana_inicio)::date
      OR EXISTS (
        SELECT 1 FROM programacion.backlog_v2 b
        WHERE b.orden_mantenimiento_id=o.id
          AND b.especialidad=ps.especialidad
          AND COALESCE(b.primera_semana_origen_inicio,b.semana_origen_inicio,o.periodo)
              <date_trunc('month',ps.semana_inicio)::date
      )
    )
  ORDER BY o.id,ps.semana_inicio,n.id
)
INSERT INTO programacion.finalizaciones_detectadas_v2(
  orden_mantenimiento_id,periodo,especialidad,fecha_fin_orden,
  programacion_origen_id,seguimiento_origen_id
)
SELECT order_id,periodo,especialidad,fecha_fin_orden,programming_id,tracking_id
FROM candidates
ON CONFLICT (orden_mantenimiento_id) DO NOTHING;
