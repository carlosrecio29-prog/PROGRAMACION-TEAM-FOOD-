ALTER TABLE programacion.programacion_item_v2
  ADD COLUMN IF NOT EXISTS origen varchar(20) NOT NULL DEFAULT 'PMP_MES';

ALTER TABLE programacion.programacion_item_v2
  ALTER COLUMN origen SET DEFAULT 'PMP_MES';

ALTER TABLE programacion.programacion_item_v2
  DROP CONSTRAINT IF EXISTS programacion_item_v2_origen_check;
ALTER TABLE programacion.programacion_item_v2
  ADD CONSTRAINT programacion_item_v2_origen_check CHECK (origen IN ('PMP_MES','BACKLOG'));

CREATE TABLE IF NOT EXISTS programacion.cierre_semanal_v2 (
  id bigserial PRIMARY KEY,
  programacion_id bigint NOT NULL REFERENCES programacion.programacion_semanal_v2(id) ON DELETE CASCADE,
  archivo_nombre text,
  cerrado_por text,
  cerrado_en timestamptz NOT NULL DEFAULT now(),
  total_items integer NOT NULL DEFAULT 0,
  finalizados integer NOT NULL DEFAULT 0,
  pendientes integer NOT NULL DEFAULT 0,
  sin_coincidencia integer NOT NULL DEFAULT 0,
  CONSTRAINT cierre_semanal_v2_unico UNIQUE (programacion_id)
);

CREATE TABLE IF NOT EXISTS programacion.cierre_item_v2 (
  id bigserial PRIMARY KEY,
  cierre_id bigint NOT NULL REFERENCES programacion.cierre_semanal_v2(id) ON DELETE CASCADE,
  programacion_item_id bigint NOT NULL REFERENCES programacion.programacion_item_v2(id) ON DELETE CASCADE,
  numero_ot text,
  estado_calendario text,
  finalizado boolean NOT NULL DEFAULT false,
  encontrado boolean NOT NULL DEFAULT false,
  registrado_en timestamptz NOT NULL DEFAULT now(),
  CONSTRAINT cierre_item_v2_unico UNIQUE (cierre_id,programacion_item_id)
);

CREATE INDEX IF NOT EXISTS idx_cierre_item_v2_cierre ON programacion.cierre_item_v2(cierre_id);
CREATE INDEX IF NOT EXISTS idx_cierre_item_v2_ot ON programacion.cierre_item_v2(numero_ot);

COMMENT ON COLUMN programacion.programacion_item_v2.origen IS
'Indica si la actividad se seleccionó desde el PMP del mes o desde el backlog.';
COMMENT ON TABLE programacion.cierre_semanal_v2 IS
'Snapshot del cierre semanal realizado al volver a cargar el calendario/PMP actualizado.';
COMMENT ON TABLE programacion.cierre_item_v2 IS
'Estado detectado para cada actividad programada al momento del cierre semanal.';
