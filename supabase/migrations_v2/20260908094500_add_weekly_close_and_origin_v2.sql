ALTER TABLE programacion.programacion_item_v2
  ADD COLUMN IF NOT EXISTS origen varchar(20) NOT NULL DEFAULT 'PMP_MES',
  ADD COLUMN IF NOT EXISTS backlog_semana_inicio date,
  ADD COLUMN IF NOT EXISTS backlog_semana_fin date,
  ADD COLUMN IF NOT EXISTS estado_cierre varchar(30),
  ADD COLUMN IF NOT EXISTS estado_software_cierre text,
  ADD COLUMN IF NOT EXISTS verificado_cierre_en timestamptz;

ALTER TABLE programacion.programacion_semanal_v2
  ADD COLUMN IF NOT EXISTS cierre_archivo_nombre text,
  ADD COLUMN IF NOT EXISTS cierre_comparado_en timestamptz,
  ADD COLUMN IF NOT EXISTS cerrado_en timestamptz,
  ADD COLUMN IF NOT EXISTS cerrado_por text;

CREATE INDEX IF NOT EXISTS idx_programacion_item_v2_origen
  ON programacion.programacion_item_v2(programacion_id, origen);

COMMENT ON COLUMN programacion.programacion_item_v2.origen IS
  'Origen de la OT al momento de programarla: PMP_MES o BACKLOG.';
COMMENT ON COLUMN programacion.programacion_item_v2.estado_cierre IS
  'Resultado del cierre semanal: FINALIZADA, PENDIENTE o NO_ENCONTRADA.';
COMMENT ON COLUMN programacion.programacion_semanal_v2.cierre_archivo_nombre IS
  'Nombre del calendario/PMP actualizado usado para comprobar el cierre semanal.';
