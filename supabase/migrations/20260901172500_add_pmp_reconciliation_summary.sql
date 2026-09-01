SET search_path TO mantenimiento, public;

ALTER TABLE mantenimiento.sincronizacion_fuente_maestra
  ADD COLUMN IF NOT EXISTS resumen_especialidad jsonb NOT NULL DEFAULT '{}'::jsonb;

COMMENT ON COLUMN mantenimiento.sincronizacion_fuente_maestra.resumen_especialidad
IS 'Conciliación por especialidad entre filas del maestro, OT únicas, estados y excepciones de relación.';
