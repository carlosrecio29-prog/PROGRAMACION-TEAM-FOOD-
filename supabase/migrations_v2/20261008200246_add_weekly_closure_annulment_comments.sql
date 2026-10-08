ALTER TABLE programacion.programacion_item_v2
  ADD COLUMN IF NOT EXISTS anulado boolean NOT NULL DEFAULT false,
  ADD COLUMN IF NOT EXISTS comentario_cierre text;

ALTER TABLE programacion.orden_mantenimiento
  ADD COLUMN IF NOT EXISTS ultimo_comentario_cierre text,
  ADD COLUMN IF NOT EXISTS ultimo_comentario_cierre_en timestamptz;

ALTER TABLE programacion.programacion_semanal_v2
  ADD COLUMN IF NOT EXISTS cierre_anuladas integer NOT NULL DEFAULT 0;

ALTER TABLE programacion.backlog_v2
  DROP CONSTRAINT IF EXISTS backlog_v2_estado_seguimiento_check;

ALTER TABLE programacion.backlog_v2
  ADD CONSTRAINT backlog_v2_estado_seguimiento_check
  CHECK (estado_seguimiento IN ('PENDIENTE_DISPONIBLE','PENDIENTE_PROGRAMADA','FINALIZADA','ANULADA'));

COMMENT ON COLUMN programacion.programacion_item_v2.anulado IS
  'Marca una actividad anulada manualmente durante el cierre semanal; no pasa a backlog.';
COMMENT ON COLUMN programacion.programacion_item_v2.comentario_cierre IS
  'Comentario de trazabilidad registrado durante la conciliación/cierre semanal.';
COMMENT ON COLUMN programacion.orden_mantenimiento.ultimo_comentario_cierre IS
  'Último comentario de cierre asociado a la actividad para consulta posterior.';
COMMENT ON COLUMN programacion.programacion_semanal_v2.cierre_anuladas IS
  'Cantidad de actividades anuladas manualmente en el cierre semanal.';
