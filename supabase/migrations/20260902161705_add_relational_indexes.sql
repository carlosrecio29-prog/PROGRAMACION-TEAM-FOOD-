CREATE INDEX IF NOT EXISTS idx_actividad_maestra_importacion
  ON mantenimiento.actividad_maestra(importacion_id_ultima);
CREATE INDEX IF NOT EXISTS idx_cierre_item_motivo
  ON mantenimiento.cierre_item(motivo_no_ejecucion_id);
CREATE INDEX IF NOT EXISTS idx_cierre_item_programacion
  ON mantenimiento.cierre_item(programacion_item_id);
CREATE INDEX IF NOT EXISTS idx_cierre_semanal_version
  ON mantenimiento.cierre_semanal(programacion_version_id);
CREATE INDEX IF NOT EXISTS idx_orden_estado_historial_importacion
  ON mantenimiento.orden_estado_historial(importacion_id);
CREATE INDEX IF NOT EXISTS idx_orden_mantenimiento_importacion
  ON mantenimiento.orden_mantenimiento(importacion_id_ultima);
CREATE INDEX IF NOT EXISTS idx_plan_trabajo_grupo
  ON mantenimiento.plan_trabajo(grupo_id);
CREATE INDEX IF NOT EXISTS idx_pmp_especialidad
  ON mantenimiento.pmp(especialidad_id);
CREATE INDEX IF NOT EXISTS idx_pmp_importacion
  ON mantenimiento.pmp(importacion_id_ultima);
CREATE INDEX IF NOT EXISTS idx_programacion_item_orden
  ON mantenimiento.programacion_item(orden_id);
CREATE INDEX IF NOT EXISTS idx_programacion_semanal_especialidad
  ON mantenimiento.programacion_semanal(especialidad_id);
CREATE INDEX IF NOT EXISTS idx_programacion_tecnico_importacion
  ON mantenimiento.programacion_tecnico(importacion_id);
CREATE INDEX IF NOT EXISTS idx_programacion_tecnico_turno
  ON mantenimiento.programacion_tecnico(turno_id);
CREATE INDEX IF NOT EXISTS idx_tecnico_especialidad
  ON mantenimiento.tecnico(especialidad_id);
CREATE INDEX IF NOT EXISTS idx_tecnico_alias_tecnico
  ON mantenimiento.tecnico_alias(tecnico_id);
CREATE INDEX IF NOT EXISTS idx_turno_alias_turno
  ON mantenimiento.turno_alias(turno_id);
