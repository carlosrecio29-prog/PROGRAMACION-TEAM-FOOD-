CREATE TABLE IF NOT EXISTS programacion.operacion_exclusion_periodo_v2 (
  periodo date NOT NULL,
  plan_clave_software text NOT NULL,
  especialidad text NOT NULL DEFAULT 'SIN DEFINIR',
  plan_trabajo_id bigint NULL REFERENCES programacion.plan_trabajo(id) ON DELETE SET NULL,
  cantidad integer NOT NULL CHECK (cantidad >= 0),
  motivo text NOT NULL DEFAULT 'OPERACION',
  origen text NOT NULL DEFAULT 'IMPORTACION_CALENDARIO',
  actualizado_en timestamptz NOT NULL DEFAULT now(),
  PRIMARY KEY (periodo, plan_clave_software, especialidad)
);

CREATE INDEX IF NOT EXISTS idx_operacion_exclusion_periodo_v2_periodo
  ON programacion.operacion_exclusion_periodo_v2(periodo, especialidad);

COMMENT ON TABLE programacion.operacion_exclusion_periodo_v2 IS
  'Resumen auditable por período de actividades excluidas del PMP por corresponder a planes OPERACIÓN.';
