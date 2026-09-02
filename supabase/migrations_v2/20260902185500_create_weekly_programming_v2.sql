CREATE TABLE IF NOT EXISTS programacion.programacion_semanal_v2 (
  id bigserial PRIMARY KEY,
  semana_inicio date NOT NULL,
  semana_fin date NOT NULL,
  especialidad varchar(20) NOT NULL,
  hh_disponibles numeric(12,2) NOT NULL DEFAULT 0,
  hh_objetivo numeric(12,2) NOT NULL DEFAULT 0,
  hh_reserva numeric(12,2) NOT NULL DEFAULT 0,
  estado varchar(20) NOT NULL DEFAULT 'BORRADOR',
  creado_por text,
  creado_en timestamptz NOT NULL DEFAULT now(),
  actualizado_en timestamptz NOT NULL DEFAULT now(),
  emitido_en timestamptz,
  CONSTRAINT programacion_semanal_v2_especialidad_check CHECK (especialidad IN ('MEC','ELE','MET','SER')),
  CONSTRAINT programacion_semanal_v2_fechas_check CHECK (semana_fin >= semana_inicio AND semana_fin - semana_inicio <= 6),
  CONSTRAINT programacion_semanal_v2_hh_check CHECK (hh_disponibles >= 0 AND hh_objetivo >= 0 AND hh_reserva >= 0),
  CONSTRAINT programacion_semanal_v2_unica UNIQUE (semana_inicio,semana_fin,especialidad)
);

CREATE TABLE IF NOT EXISTS programacion.programacion_item_v2 (
  id bigserial PRIMARY KEY,
  programacion_id bigint NOT NULL REFERENCES programacion.programacion_semanal_v2(id) ON DELETE CASCADE,
  orden_mantenimiento_id bigint NOT NULL REFERENCES programacion.orden_mantenimiento(id) ON DELETE RESTRICT,
  hh_programadas numeric(12,2) NOT NULL,
  requiere_parada boolean NOT NULL,
  seleccionado_en timestamptz NOT NULL DEFAULT now(),
  CONSTRAINT programacion_item_v2_hh_check CHECK (hh_programadas >= 0),
  CONSTRAINT programacion_item_v2_unico UNIQUE (programacion_id,orden_mantenimiento_id)
);

CREATE INDEX IF NOT EXISTS idx_programacion_semanal_v2_semana
  ON programacion.programacion_semanal_v2(semana_inicio,semana_fin,especialidad);
CREATE INDEX IF NOT EXISTS idx_programacion_item_v2_programacion
  ON programacion.programacion_item_v2(programacion_id);
CREATE INDEX IF NOT EXISTS idx_programacion_item_v2_orden
  ON programacion.programacion_item_v2(orden_mantenimiento_id);

COMMENT ON TABLE programacion.programacion_semanal_v2 IS
  'Programación interna semanal V2. La capacidad se calcula desde turnos reales; 80% es programable y 20% reserva.';
COMMENT ON TABLE programacion.programacion_item_v2 IS
  'Órdenes/actividades seleccionadas para una semana. Guarda snapshot de H-H y condición de parada.';
