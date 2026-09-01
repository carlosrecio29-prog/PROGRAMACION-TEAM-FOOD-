SET search_path TO mantenimiento, public;

ALTER TABLE mantenimiento.importacion DROP CONSTRAINT IF EXISTS importacion_tipo_check;
ALTER TABLE mantenimiento.importacion ADD CONSTRAINT importacion_tipo_check CHECK (
  tipo::text = ANY (ARRAY[
    'PLANEACION_MENSUAL','PROGRAMACION_TECNICOS','ESTADO_ORDENES',
    'MAESTRO_ACTIVOS','MAESTRO_PLANES','MAESTRO_PERSONAL_TURNOS',
    'MAESTRO_ACTIVIDADES_PLANTA'
  ]::text[])
);

CREATE TABLE IF NOT EXISTS mantenimiento.actividad_maestra (
  id bigserial PRIMARY KEY,
  activo_id bigint NOT NULL REFERENCES mantenimiento.activo(id) ON DELETE CASCADE,
  plan_trabajo_id bigint NOT NULL REFERENCES mantenimiento.plan_trabajo(id) ON DELETE CASCADE,
  especialidad_id smallint NOT NULL REFERENCES mantenimiento.especialidad(id),
  tiempo_estandar_min numeric(12,2) CHECK (tiempo_estandar_min IS NULL OR tiempo_estandar_min >= 0),
  personas_requeridas numeric(8,2) CHECK (personas_requeridas IS NULL OR personas_requeridas > 0),
  fuente_datos varchar(40) NOT NULL DEFAULT 'MAESTRO',
  importacion_id_ultima bigint REFERENCES mantenimiento.importacion(id),
  activo boolean NOT NULL DEFAULT true,
  creado_en timestamptz NOT NULL DEFAULT now(),
  actualizado_en timestamptz NOT NULL DEFAULT now(),
  UNIQUE (activo_id,plan_trabajo_id,especialidad_id)
);
CREATE INDEX IF NOT EXISTS idx_actividad_maestra_plan ON mantenimiento.actividad_maestra(plan_trabajo_id);
CREATE INDEX IF NOT EXISTS idx_actividad_maestra_activo ON mantenimiento.actividad_maestra(activo_id);
CREATE INDEX IF NOT EXISTS idx_actividad_maestra_especialidad ON mantenimiento.actividad_maestra(especialidad_id);
ALTER TABLE mantenimiento.actividad_maestra ENABLE ROW LEVEL SECURITY;
REVOKE ALL ON TABLE mantenimiento.actividad_maestra FROM anon, authenticated;
GRANT SELECT,INSERT,UPDATE,DELETE ON TABLE mantenimiento.actividad_maestra TO service_role;
GRANT USAGE,SELECT ON SEQUENCE mantenimiento.actividad_maestra_id_seq TO service_role;

CREATE OR REPLACE VIEW mantenimiento.vw_catalogo_actividades_planta
WITH (security_invoker=true) AS
SELECT am.id actividad_maestra_id,e.codigo especialidad,g.nombre grupo_ruta,
pt.id plan_trabajo_id,pt.nombre plan_trabajo,pt.nombre_canonico,
a.id activo_id,a.codigo activo_codigo,a.descripcion activo_descripcion,
a.area_nombre,a.linea_nombre,a.criticidad,
COALESCE(am.personas_requeridas,pt.personas_defecto,1::numeric) personas_requeridas,
am.tiempo_estandar_min,
CASE WHEN am.tiempo_estandar_min IS NULL THEN NULL
ELSE (am.tiempo_estandar_min/60.0)*COALESCE(am.personas_requeridas,pt.personas_defecto,1::numeric) END hh_estandar,
am.fuente_datos,am.activo
FROM mantenimiento.actividad_maestra am
JOIN mantenimiento.activo a ON a.id=am.activo_id
JOIN mantenimiento.plan_trabajo pt ON pt.id=am.plan_trabajo_id
JOIN mantenimiento.especialidad e ON e.id=am.especialidad_id
LEFT JOIN mantenimiento.grupo_plan_trabajo g ON g.id=pt.grupo_id;
REVOKE ALL ON TABLE mantenimiento.vw_catalogo_actividades_planta FROM anon, authenticated;
GRANT SELECT ON TABLE mantenimiento.vw_catalogo_actividades_planta TO service_role;
