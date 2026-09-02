ALTER TABLE mantenimiento.plan_trabajo
  ADD COLUMN IF NOT EXISTS numero_personas numeric(8,2) NULL,
  ADD COLUMN IF NOT EXISTS equipo_detenido boolean NULL;

UPDATE mantenimiento.plan_trabajo pt
SET numero_personas = COALESCE(cp.personas_usar, pt.personas_defecto)
FROM mantenimiento.clasificacion_plan cp
WHERE cp.plan_trabajo_id = pt.id
  AND pt.numero_personas IS NULL;

UPDATE mantenimiento.plan_trabajo
SET numero_personas = personas_defecto
WHERE numero_personas IS NULL
  AND personas_defecto IS NOT NULL;

UPDATE mantenimiento.plan_trabajo pt
SET equipo_detenido = CASE
  WHEN cp.condicion = 'EQUIPO DETENIDO' THEN TRUE
  WHEN cp.condicion = 'OPERANDO' THEN FALSE
  ELSE pt.equipo_detenido
END
FROM mantenimiento.clasificacion_plan cp
WHERE cp.plan_trabajo_id = pt.id
  AND pt.equipo_detenido IS NULL
  AND cp.condicion IN ('EQUIPO DETENIDO','OPERANDO');

ALTER TABLE mantenimiento.plan_trabajo
  DROP CONSTRAINT IF EXISTS plan_trabajo_numero_personas_check;

ALTER TABLE mantenimiento.plan_trabajo
  ADD CONSTRAINT plan_trabajo_numero_personas_check
  CHECK (numero_personas IS NULL OR numero_personas > 0);

COMMENT ON COLUMN mantenimiento.plan_trabajo.numero_personas IS
  'NumeroPersonas del maestro TEAM FOOD. Se aprende durante la programación cuando está vacío.';

COMMENT ON COLUMN mantenimiento.plan_trabajo.equipo_detenido IS
  'EquipoDetenido del maestro TEAM FOOD: TRUE=SI, FALSE=NO, NULL=pendiente por definir.';

CREATE OR REPLACE VIEW mantenimiento.vw_pmp_calculado AS
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
      ELSE COALESCE(cpa.condicion,cp.condicion,'SIN CLASIFICAR')
    END
  )::varchar AS condicion,
  COALESCE(
    pt.numero_personas,
    cpa.personas_usar,
    cp.personas_usar,
    pt.personas_defecto
  )::numeric(8,2) AS personas_usar,
  COALESCE(p.tiempo_planeado_min,pt.tiempo_ejecucion_min)::numeric(12,2) AS tiempo_planeado_min,
  CASE
    WHEN COALESCE(p.tiempo_planeado_min,pt.tiempo_ejecucion_min) IS NULL
      OR COALESCE(pt.numero_personas,cpa.personas_usar,cp.personas_usar,pt.personas_defecto) IS NULL
    THEN NULL::numeric
    ELSE COALESCE(p.tiempo_planeado_min,pt.tiempo_ejecucion_min) / 60.0
      * COALESCE(pt.numero_personas,cpa.personas_usar,cp.personas_usar,pt.personas_defecto)
  END AS hh_pmp,
  COALESCE(p.tiempo_planeado_min,pt.tiempo_ejecucion_min) IS NOT NULL
    AND COALESCE(p.tiempo_planeado_min,pt.tiempo_ejecucion_min) > 0
    AND COALESCE(pt.numero_personas,cpa.personas_usar,cp.personas_usar,pt.personas_defecto) IS NOT NULL
    AND (
      CASE
        WHEN pt.equipo_detenido IS TRUE THEN 'EQUIPO DETENIDO'
        WHEN pt.equipo_detenido IS FALSE THEN 'OPERANDO'
        ELSE COALESCE(cpa.condicion,cp.condicion,'SIN CLASIFICAR')
      END
    ) <> 'SIN CLASIFICAR' AS datos_completos,
  array_remove(ARRAY[
    CASE
      WHEN COALESCE(p.tiempo_planeado_min,pt.tiempo_ejecucion_min) IS NULL
        OR COALESCE(p.tiempo_planeado_min,pt.tiempo_ejecucion_min) <= 0
      THEN 'TIEMPO'::text ELSE NULL::text
    END,
    CASE
      WHEN COALESCE(pt.numero_personas,cpa.personas_usar,cp.personas_usar,pt.personas_defecto) IS NULL
      THEN 'PERSONAS'::text ELSE NULL::text
    END,
    CASE
      WHEN (
        CASE
          WHEN pt.equipo_detenido IS TRUE THEN 'EQUIPO DETENIDO'
          WHEN pt.equipo_detenido IS FALSE THEN 'OPERANDO'
          ELSE COALESCE(cpa.condicion,cp.condicion,'SIN CLASIFICAR')
        END
      ) = 'SIN CLASIFICAR'
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
LEFT JOIN mantenimiento.clasificacion_plan cp ON cp.plan_trabajo_id=p.plan_trabajo_id
LEFT JOIN mantenimiento.clasificacion_plan_activo cpa
  ON cpa.plan_trabajo_id=p.plan_trabajo_id AND cpa.activo_id=p.activo_id
LEFT JOIN mantenimiento.orden_mantenimiento om ON om.pmp_id=p.id;

CREATE OR REPLACE VIEW mantenimiento.vw_catalogo_actividades_planta AS
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
  COALESCE(am.personas_requeridas,pt.numero_personas,pt.personas_defecto)::numeric(8,2) AS personas_requeridas,
  COALESCE(am.tiempo_estandar_min,pt.tiempo_ejecucion_min)::numeric(12,2) AS tiempo_estandar_min,
  CASE
    WHEN COALESCE(am.tiempo_estandar_min,pt.tiempo_ejecucion_min) IS NULL
      OR COALESCE(am.personas_requeridas,pt.numero_personas,pt.personas_defecto) IS NULL
    THEN NULL::numeric
    ELSE COALESCE(am.tiempo_estandar_min,pt.tiempo_ejecucion_min)/60.0
      * COALESCE(am.personas_requeridas,pt.numero_personas,pt.personas_defecto)
  END AS hh_estandar,
  am.fuente_datos,
  am.activo
FROM mantenimiento.actividad_maestra am
JOIN mantenimiento.activo a ON a.id=am.activo_id
JOIN mantenimiento.plan_trabajo pt ON pt.id=am.plan_trabajo_id
JOIN mantenimiento.especialidad e ON e.id=am.especialidad_id
LEFT JOIN mantenimiento.grupo_plan_trabajo g ON g.id=pt.grupo_id;
