CREATE OR REPLACE FUNCTION mantenimiento.sincronizar_actividad_maestra_desde_pmp(
  p_periodo_mensual_id bigint DEFAULT NULL
)
RETURNS integer
LANGUAGE plpgsql
SECURITY INVOKER
SET search_path=mantenimiento,pg_temp
AS $$
DECLARE v_count integer;
BEGIN
  WITH src AS (
    SELECT DISTINCT ON (p.activo_id,p.plan_trabajo_id,p.especialidad_id)
      p.activo_id,p.plan_trabajo_id,p.especialidad_id,
      p.tiempo_planeado_min tiempo_estandar_min,
      COALESCE(pt.personas_defecto,1::numeric) personas_requeridas,
      p.importacion_id_ultima
    FROM mantenimiento.pmp p
    JOIN mantenimiento.plan_trabajo pt ON pt.id=p.plan_trabajo_id
    WHERE p_periodo_mensual_id IS NULL OR p.periodo_mensual_id=p_periodo_mensual_id
    ORDER BY p.activo_id,p.plan_trabajo_id,p.especialidad_id,p.fecha_planeada_inicio DESC NULLS LAST,p.id DESC
  )
  INSERT INTO mantenimiento.actividad_maestra(
    activo_id,plan_trabajo_id,especialidad_id,tiempo_estandar_min,
    personas_requeridas,fuente_datos,importacion_id_ultima,activo,actualizado_en
  )
  SELECT activo_id,plan_trabajo_id,especialidad_id,tiempo_estandar_min,
    personas_requeridas,'PLANEACION_MENSUAL',importacion_id_ultima,true,now()
  FROM src
  ON CONFLICT(activo_id,plan_trabajo_id,especialidad_id) DO UPDATE SET
    tiempo_estandar_min=excluded.tiempo_estandar_min,
    personas_requeridas=COALESCE(excluded.personas_requeridas,mantenimiento.actividad_maestra.personas_requeridas),
    fuente_datos=excluded.fuente_datos,
    importacion_id_ultima=excluded.importacion_id_ultima,
    activo=true,actualizado_en=now();
  GET DIAGNOSTICS v_count=ROW_COUNT;
  RETURN v_count;
END;
$$;
REVOKE ALL ON FUNCTION mantenimiento.sincronizar_actividad_maestra_desde_pmp(bigint) FROM public,anon,authenticated;
GRANT EXECUTE ON FUNCTION mantenimiento.sincronizar_actividad_maestra_desde_pmp(bigint) TO service_role;
