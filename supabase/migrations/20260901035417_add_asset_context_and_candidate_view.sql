SET search_path TO mantenimiento, public;
ALTER TABLE activo ADD COLUMN IF NOT EXISTS area_nombre VARCHAR(255), ADD COLUMN IF NOT EXISTS linea_nombre VARCHAR(255);
CREATE INDEX IF NOT EXISTS idx_activo_area_nombre_lower ON activo (LOWER(area_nombre));
CREATE INDEX IF NOT EXISTS idx_activo_linea_nombre_lower ON activo (LOWER(linea_nombre));
DROP VIEW IF EXISTS vw_pmp_calculado;
CREATE VIEW vw_pmp_calculado AS
SELECT p.id AS pmp_id,pm.anio,pm.mes,p.activo_id,a.codigo AS activo_codigo,a.descripcion AS activo_descripcion,
a.area_nombre,a.linea_nombre,a.criticidad,p.plan_trabajo_id,pt.nombre AS plan_trabajo,
COALESCE(gpt.nombre,'SIN GRUPO') AS grupo_plan,e.codigo AS especialidad,
COALESCE(cpa.condicion,cp.condicion,'SIN CLASIFICAR') AS condicion,
COALESCE(cpa.personas_usar,cp.personas_usar,pt.personas_defecto,1) AS personas_usar,p.tiempo_planeado_min,
(p.tiempo_planeado_min/60.0)*COALESCE(cpa.personas_usar,cp.personas_usar,pt.personas_defecto,1) AS hh_pmp,
om.id AS orden_id,om.numero_orden,COALESCE(om.estado,'PENDIENTE') AS estado_orden
FROM pmp p JOIN periodo_mensual pm ON pm.id=p.periodo_mensual_id JOIN activo a ON a.id=p.activo_id
JOIN plan_trabajo pt ON pt.id=p.plan_trabajo_id LEFT JOIN grupo_plan_trabajo gpt ON gpt.id=pt.grupo_id
JOIN especialidad e ON e.id=p.especialidad_id LEFT JOIN clasificacion_plan cp ON cp.plan_trabajo_id=p.plan_trabajo_id
LEFT JOIN clasificacion_plan_activo cpa ON cpa.plan_trabajo_id=p.plan_trabajo_id AND cpa.activo_id=p.activo_id
LEFT JOIN orden_mantenimiento om ON om.pmp_id=p.id;
