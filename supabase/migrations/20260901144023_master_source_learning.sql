SET search_path TO mantenimiento, public;

ALTER TABLE mantenimiento.importacion DROP CONSTRAINT IF EXISTS importacion_tipo_check;
ALTER TABLE mantenimiento.importacion ADD CONSTRAINT importacion_tipo_check CHECK (
  tipo::text = ANY (ARRAY[
    'PLANEACION_MENSUAL','PROGRAMACION_TECNICOS','ESTADO_ORDENES',
    'MAESTRO_ACTIVOS','MAESTRO_PLANES','MAESTRO_PERSONAL_TURNOS',
    'MAESTRO_ACTIVIDADES_PLANTA','MAESTRO_TEAM_FOOD'
  ]::text[])
);

ALTER TABLE mantenimiento.plan_trabajo
  ALTER COLUMN personas_defecto DROP NOT NULL,
  ALTER COLUMN personas_defecto DROP DEFAULT;
ALTER TABLE mantenimiento.plan_trabajo
  ADD COLUMN IF NOT EXISTS tiempo_ejecucion_min numeric(12,2) CHECK(tiempo_ejecucion_min IS NULL OR tiempo_ejecucion_min>=0),
  ADD COLUMN IF NOT EXISTS tiempo_parada_min numeric(12,2) CHECK(tiempo_parada_min IS NULL OR tiempo_parada_min>=0),
  ADD COLUMN IF NOT EXISTS fuente_maestra varchar(40),
  ADD COLUMN IF NOT EXISTS actualizado_por varchar(120);

ALTER TABLE mantenimiento.clasificacion_plan
  ALTER COLUMN personas_usar DROP NOT NULL,
  ALTER COLUMN personas_usar DROP DEFAULT;
ALTER TABLE mantenimiento.clasificacion_plan
  ADD COLUMN IF NOT EXISTS actualizado_por varchar(120),
  ADD COLUMN IF NOT EXISTS fuente varchar(30) NOT NULL DEFAULT 'MAESTRO';
ALTER TABLE mantenimiento.clasificacion_plan_activo
  ADD COLUMN IF NOT EXISTS actualizado_por varchar(120),
  ADD COLUMN IF NOT EXISTS fuente varchar(30) NOT NULL DEFAULT 'USUARIO';

CREATE TABLE IF NOT EXISTS mantenimiento.sincronizacion_fuente_maestra(
  id bigserial PRIMARY KEY,
  fuente varchar(40) NOT NULL DEFAULT 'TEAM_FOOD',
  referencia varchar(255), anio smallint,
  mes smallint CHECK(mes IS NULL OR mes BETWEEN 1 AND 12),
  estado varchar(20) NOT NULL CHECK(estado IN('PROCESANDO','COMPLETADA','CON_ADVERTENCIAS','ERROR')),
  filas_leidas integer NOT NULL DEFAULT 0,
  filas_procesadas integer NOT NULL DEFAULT 0,
  mensaje text, iniciado_en timestamptz NOT NULL DEFAULT now(), finalizado_en timestamptz
);
ALTER TABLE mantenimiento.sincronizacion_fuente_maestra ENABLE ROW LEVEL SECURITY;
REVOKE ALL ON TABLE mantenimiento.sincronizacion_fuente_maestra FROM anon,authenticated;
GRANT SELECT,INSERT,UPDATE,DELETE ON TABLE mantenimiento.sincronizacion_fuente_maestra TO service_role;
GRANT USAGE,SELECT ON SEQUENCE mantenimiento.sincronizacion_fuente_maestra_id_seq TO service_role;
CREATE INDEX IF NOT EXISTS idx_sync_fuente_maestra_fecha
ON mantenimiento.sincronizacion_fuente_maestra(iniciado_en DESC);

DROP VIEW IF EXISTS mantenimiento.vw_pmp_calculado;
CREATE VIEW mantenimiento.vw_pmp_calculado WITH(security_invoker=true) AS
SELECT p.id pmp_id,pm.anio,pm.mes,p.activo_id,a.codigo activo_codigo,a.descripcion activo_descripcion,
a.area_nombre,a.linea_nombre,a.criticidad,p.plan_trabajo_id,pt.nombre plan_trabajo,
COALESCE(gpt.nombre,'SIN GRUPO') grupo_plan,e.codigo especialidad,
COALESCE(cpa.condicion,cp.condicion,'SIN CLASIFICAR') condicion,
COALESCE(cpa.personas_usar,cp.personas_usar,pt.personas_defecto) personas_usar,
p.tiempo_planeado_min,
CASE WHEN p.tiempo_planeado_min IS NULL OR COALESCE(cpa.personas_usar,cp.personas_usar,pt.personas_defecto) IS NULL
THEN NULL ELSE (p.tiempo_planeado_min/60.0)*COALESCE(cpa.personas_usar,cp.personas_usar,pt.personas_defecto) END hh_pmp,
(p.tiempo_planeado_min IS NOT NULL AND p.tiempo_planeado_min>0
 AND COALESCE(cpa.personas_usar,cp.personas_usar,pt.personas_defecto) IS NOT NULL
 AND COALESCE(cpa.condicion,cp.condicion,'SIN CLASIFICAR')<>'SIN CLASIFICAR') datos_completos,
array_remove(ARRAY[
 CASE WHEN p.tiempo_planeado_min IS NULL OR p.tiempo_planeado_min<=0 THEN 'TIEMPO' END,
 CASE WHEN COALESCE(cpa.personas_usar,cp.personas_usar,pt.personas_defecto) IS NULL THEN 'PERSONAS' END,
 CASE WHEN COALESCE(cpa.condicion,cp.condicion,'SIN CLASIFICAR')='SIN CLASIFICAR' THEN 'CONDICION' END
],NULL) datos_faltantes,
om.id orden_id,om.numero_orden,COALESCE(om.estado,'PENDIENTE') estado_orden
FROM mantenimiento.pmp p
JOIN mantenimiento.periodo_mensual pm ON pm.id=p.periodo_mensual_id
JOIN mantenimiento.activo a ON a.id=p.activo_id
JOIN mantenimiento.plan_trabajo pt ON pt.id=p.plan_trabajo_id
LEFT JOIN mantenimiento.grupo_plan_trabajo gpt ON gpt.id=pt.grupo_id
JOIN mantenimiento.especialidad e ON e.id=p.especialidad_id
LEFT JOIN mantenimiento.clasificacion_plan cp ON cp.plan_trabajo_id=p.plan_trabajo_id
LEFT JOIN mantenimiento.clasificacion_plan_activo cpa ON cpa.plan_trabajo_id=p.plan_trabajo_id AND cpa.activo_id=p.activo_id
LEFT JOIN mantenimiento.orden_mantenimiento om ON om.pmp_id=p.id;
REVOKE ALL ON TABLE mantenimiento.vw_pmp_calculado FROM anon,authenticated;
GRANT SELECT ON TABLE mantenimiento.vw_pmp_calculado TO service_role;

DROP VIEW IF EXISTS mantenimiento.vw_catalogo_actividades_planta;
CREATE VIEW mantenimiento.vw_catalogo_actividades_planta WITH(security_invoker=true) AS
SELECT am.id actividad_maestra_id,e.codigo especialidad,g.nombre grupo_ruta,
pt.id plan_trabajo_id,pt.nombre plan_trabajo,pt.nombre_canonico,
a.id activo_id,a.codigo activo_codigo,a.descripcion activo_descripcion,
a.area_nombre,a.linea_nombre,a.criticidad,
COALESCE(am.personas_requeridas,pt.personas_defecto) personas_requeridas,
COALESCE(am.tiempo_estandar_min,pt.tiempo_ejecucion_min) tiempo_estandar_min,
CASE WHEN COALESCE(am.tiempo_estandar_min,pt.tiempo_ejecucion_min) IS NULL
 OR COALESCE(am.personas_requeridas,pt.personas_defecto) IS NULL THEN NULL
ELSE (COALESCE(am.tiempo_estandar_min,pt.tiempo_ejecucion_min)/60.0)*
COALESCE(am.personas_requeridas,pt.personas_defecto) END hh_estandar,
am.fuente_datos,am.activo
FROM mantenimiento.actividad_maestra am
JOIN mantenimiento.activo a ON a.id=am.activo_id
JOIN mantenimiento.plan_trabajo pt ON pt.id=am.plan_trabajo_id
JOIN mantenimiento.especialidad e ON e.id=am.especialidad_id
LEFT JOIN mantenimiento.grupo_plan_trabajo g ON g.id=pt.grupo_id;
REVOKE ALL ON TABLE mantenimiento.vw_catalogo_actividades_planta FROM anon,authenticated;
GRANT SELECT ON TABLE mantenimiento.vw_catalogo_actividades_planta TO service_role;

CREATE OR REPLACE FUNCTION mantenimiento.sincronizar_actividad_maestra_desde_pmp(p_periodo_mensual_id bigint DEFAULT NULL)
RETURNS integer LANGUAGE plpgsql SECURITY INVOKER SET search_path=mantenimiento,pg_temp AS $$
DECLARE v_count integer;
BEGIN
 WITH src AS(
  SELECT DISTINCT ON(p.activo_id,p.plan_trabajo_id,p.especialidad_id)
   p.activo_id,p.plan_trabajo_id,p.especialidad_id,p.tiempo_planeado_min tiempo_estandar_min,
   pt.personas_defecto personas_requeridas,p.importacion_id_ultima
  FROM mantenimiento.pmp p JOIN mantenimiento.plan_trabajo pt ON pt.id=p.plan_trabajo_id
  WHERE p_periodo_mensual_id IS NULL OR p.periodo_mensual_id=p_periodo_mensual_id
  ORDER BY p.activo_id,p.plan_trabajo_id,p.especialidad_id,p.fecha_planeada_inicio DESC NULLS LAST,p.id DESC
 )
 INSERT INTO mantenimiento.actividad_maestra(
  activo_id,plan_trabajo_id,especialidad_id,tiempo_estandar_min,personas_requeridas,
  fuente_datos,importacion_id_ultima,activo,actualizado_en)
 SELECT activo_id,plan_trabajo_id,especialidad_id,tiempo_estandar_min,personas_requeridas,
  'PLANEACION_MENSUAL',importacion_id_ultima,true,now() FROM src
 ON CONFLICT(activo_id,plan_trabajo_id,especialidad_id) DO UPDATE SET
  tiempo_estandar_min=excluded.tiempo_estandar_min,
  personas_requeridas=COALESCE(excluded.personas_requeridas,mantenimiento.actividad_maestra.personas_requeridas),
  fuente_datos=excluded.fuente_datos,importacion_id_ultima=excluded.importacion_id_ultima,
  activo=true,actualizado_en=now();
 GET DIAGNOSTICS v_count=ROW_COUNT;
 RETURN v_count;
END; $$;
REVOKE ALL ON FUNCTION mantenimiento.sincronizar_actividad_maestra_desde_pmp(bigint) FROM public,anon,authenticated;
GRANT EXECUTE ON FUNCTION mantenimiento.sincronizar_actividad_maestra_desde_pmp(bigint) TO service_role;
