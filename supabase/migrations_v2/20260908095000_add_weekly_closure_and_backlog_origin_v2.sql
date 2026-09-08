ALTER TABLE programacion.programacion_item_v2
  ADD COLUMN IF NOT EXISTS origen_backlog boolean NOT NULL DEFAULT false,
  ADD COLUMN IF NOT EXISTS estado_cierre text,
  ADD COLUMN IF NOT EXISTS finalizado boolean,
  ADD COLUMN IF NOT EXISTS verificado_en timestamptz,
  ADD COLUMN IF NOT EXISTS cierre_fuente text;

ALTER TABLE programacion.programacion_semanal_v2
  ADD COLUMN IF NOT EXISTS cierre_en timestamptz,
  ADD COLUMN IF NOT EXISTS cierre_por text,
  ADD COLUMN IF NOT EXISTS cierre_archivo text,
  ADD COLUMN IF NOT EXISTS cierre_total integer,
  ADD COLUMN IF NOT EXISTS cierre_finalizadas integer,
  ADD COLUMN IF NOT EXISTS cierre_pendientes integer,
  ADD COLUMN IF NOT EXISTS cierre_no_encontradas integer;

CREATE INDEX IF NOT EXISTS idx_programacion_item_v2_cierre
  ON programacion.programacion_item_v2(programacion_id, finalizado);

COMMENT ON COLUMN programacion.programacion_item_v2.origen_backlog IS
  'Snapshot del origen al momento de programar: true si la OT fue seleccionada desde BACKLOG.';
COMMENT ON COLUMN programacion.programacion_item_v2.estado_cierre IS
  'Estado encontrado en el archivo de calendario/PMP usado para el cierre semanal.';
COMMENT ON COLUMN programacion.programacion_item_v2.finalizado IS
  'Resultado del cierre semanal. NULL significa que todavía no fue verificada.';
COMMENT ON COLUMN programacion.programacion_semanal_v2.cierre_archivo IS
  'Nombre del archivo de calendario/PMP cargado para realizar el cierre semanal.';
