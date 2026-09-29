CREATE TABLE IF NOT EXISTS programacion.cierre_mensual_v2 (
  periodo date PRIMARY KEY,
  estado text NOT NULL DEFAULT 'ABIERTO' CHECK (estado IN ('ABIERTO','CERRADO')),
  cerrado_en timestamptz NULL,
  cerrado_por text NULL,
  resumen jsonb NULL,
  actualizado_en timestamptz NOT NULL DEFAULT now()
);

COMMENT ON TABLE programacion.cierre_mensual_v2 IS
  'Registro formal del cierre mensual del programa de mantenimiento.';
