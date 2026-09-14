CREATE TABLE IF NOT EXISTS programacion.plan_trabajo_actividad (
  id bigserial PRIMARY KEY,
  plan_trabajo_id bigint NOT NULL REFERENCES programacion.plan_trabajo(id) ON DELETE CASCADE,
  consecutivo integer NOT NULL,
  actividad text NOT NULL,
  tiempo_min numeric,
  obligatorio boolean,
  fila_origen integer,
  actualizado_en timestamptz NOT NULL DEFAULT now(),
  CONSTRAINT plan_trabajo_actividad_unique UNIQUE(plan_trabajo_id, consecutivo)
);

CREATE INDEX IF NOT EXISTS ix_plan_trabajo_actividad_plan
  ON programacion.plan_trabajo_actividad(plan_trabajo_id, consecutivo);
