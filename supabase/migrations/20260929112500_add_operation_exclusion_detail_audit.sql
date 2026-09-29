CREATE TABLE IF NOT EXISTS programacion.operacion_exclusion_detalle_v2 (
  id bigserial PRIMARY KEY,
  periodo date NOT NULL,
  fila_origen integer,
  numero_ot text,
  activo_codigo text NOT NULL,
  plan_clave_software text NOT NULL,
  titulo text,
  especialidad text,
  estado text,
  cronograma_planeacion text,
  tiempo_planeado_min numeric,
  plan_trabajo_id bigint NULL REFERENCES programacion.plan_trabajo(id) ON DELETE SET NULL,
  motivo text NOT NULL DEFAULT 'OPERACION',
  origen text NOT NULL DEFAULT 'IMPORTACION_CALENDARIO',
  registrado_en timestamptz NOT NULL DEFAULT now()
);

CREATE INDEX IF NOT EXISTS idx_operacion_exclusion_detalle_periodo
  ON programacion.operacion_exclusion_detalle_v2(periodo, especialidad);

CREATE INDEX IF NOT EXISTS idx_operacion_exclusion_detalle_activo
  ON programacion.operacion_exclusion_detalle_v2(activo_codigo);

COMMENT ON TABLE programacion.operacion_exclusion_detalle_v2 IS
  'Detalle fila a fila de actividades retiradas de la Lista de Calendario por ser OPERACIÓN.';
