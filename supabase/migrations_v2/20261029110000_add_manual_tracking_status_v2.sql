-- La decisión manual pertenece al seguimiento, no reemplaza la lectura del Excel.
CREATE TABLE IF NOT EXISTS programacion.seguimiento_estado_manual_v2 (
  id bigserial PRIMARY KEY,
  programacion_item_id bigint NOT NULL UNIQUE REFERENCES programacion.programacion_item_v2(id) ON DELETE RESTRICT,
  estado varchar(12) NOT NULL CHECK (estado IN ('FINALIZADA','PENDIENTE','ANULADA')),
  comentario text,
  actualizado_por text,
  creado_en timestamptz NOT NULL DEFAULT now(),
  actualizado_en timestamptz NOT NULL DEFAULT now()
);
CREATE TABLE IF NOT EXISTS programacion.seguimiento_estado_manual_auditoria_v2 (
  id bigserial PRIMARY KEY,
  programacion_item_id bigint NOT NULL REFERENCES programacion.programacion_item_v2(id) ON DELETE RESTRICT,
  estado_anterior varchar(12), estado_nuevo varchar(12) NOT NULL CHECK (estado_nuevo IN ('FINALIZADA','PENDIENTE','ANULADA')),
  comentario text, actor text, registrado_en timestamptz NOT NULL DEFAULT now()
);
CREATE INDEX IF NOT EXISTS idx_seguimiento_manual_auditoria_item ON programacion.seguimiento_estado_manual_auditoria_v2(programacion_item_id, registrado_en DESC);
ALTER TABLE programacion.seguimiento_semanal_v2 ADD COLUMN IF NOT EXISTS anuladas integer NOT NULL DEFAULT 0, ADD COLUMN IF NOT EXISTS hh_anuladas numeric NOT NULL DEFAULT 0;
ALTER TABLE programacion.seguimiento_semanal_item_v2 ADD COLUMN IF NOT EXISTS estado_manual varchar(12), ADD COLUMN IF NOT EXISTS origen_estado varchar(20), ADD COLUMN IF NOT EXISTS discrepancia_manual_excel boolean NOT NULL DEFAULT false;
ALTER TABLE programacion.seguimiento_semanal_item_v2 DROP CONSTRAINT IF EXISTS seguimiento_semanal_item_v2_estado_manual_check;
ALTER TABLE programacion.seguimiento_semanal_item_v2 ADD CONSTRAINT seguimiento_semanal_item_v2_estado_manual_check CHECK (estado_manual IS NULL OR estado_manual IN ('FINALIZADA','PENDIENTE','ANULADA'));
COMMENT ON TABLE programacion.seguimiento_estado_manual_v2 IS 'Estado manual vigente por OT programada; prevalece sobre futuras cargas de Lista de Calendario.';
COMMENT ON TABLE programacion.seguimiento_estado_manual_auditoria_v2 IS 'Historial inmutable de decisiones manuales de seguimiento.';
