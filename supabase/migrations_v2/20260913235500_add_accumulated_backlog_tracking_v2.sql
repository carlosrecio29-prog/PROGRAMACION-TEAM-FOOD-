ALTER TABLE programacion.backlog_v2
  ADD COLUMN IF NOT EXISTS estado_seguimiento varchar(32) NOT NULL DEFAULT 'PENDIENTE_DISPONIBLE',
  ADD COLUMN IF NOT EXISTS primera_semana_origen_inicio date,
  ADD COLUMN IF NOT EXISTS primera_semana_origen_fin date,
  ADD COLUMN IF NOT EXISTS ultima_programacion_id bigint REFERENCES programacion.programacion_semanal_v2(id) ON DELETE SET NULL,
  ADD COLUMN IF NOT EXISTS ultimo_resultado_cierre varchar(32),
  ADD COLUMN IF NOT EXISTS ultimo_cierre_en timestamptz,
  ADD COLUMN IF NOT EXISTS reprogramaciones integer NOT NULL DEFAULT 0,
  ADD COLUMN IF NOT EXISTS finalizado_en timestamptz,
  ADD COLUMN IF NOT EXISTS finalizado_por text;

UPDATE programacion.backlog_v2
SET primera_semana_origen_inicio=COALESCE(primera_semana_origen_inicio,semana_origen_inicio),
    primera_semana_origen_fin=COALESCE(primera_semana_origen_fin,semana_origen_fin),
    estado_seguimiento=COALESCE(estado_seguimiento,'PENDIENTE_DISPONIBLE')
WHERE primera_semana_origen_inicio IS NULL
   OR primera_semana_origen_fin IS NULL
   OR estado_seguimiento IS NULL;

ALTER TABLE programacion.backlog_v2
  ADD CONSTRAINT backlog_v2_estado_seguimiento_check
  CHECK (estado_seguimiento IN ('PENDIENTE_DISPONIBLE','PENDIENTE_PROGRAMADA','FINALIZADA'));

ALTER TABLE programacion.backlog_v2
  ADD CONSTRAINT backlog_v2_reprogramaciones_check CHECK (reprogramaciones >= 0);

CREATE INDEX IF NOT EXISTS ix_backlog_v2_estado_especialidad
  ON programacion.backlog_v2(estado_seguimiento,especialidad,primera_semana_origen_inicio);

CREATE INDEX IF NOT EXISTS ix_backlog_v2_ultima_programacion
  ON programacion.backlog_v2(ultima_programacion_id)
  WHERE estado_seguimiento='PENDIENTE_PROGRAMADA';

COMMENT ON COLUMN programacion.backlog_v2.estado_seguimiento IS
'PENDIENTE_DISPONIBLE, PENDIENTE_PROGRAMADA o FINALIZADA; solo cierre externo cambia a FINALIZADA.';
