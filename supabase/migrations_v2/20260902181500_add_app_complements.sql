ALTER TABLE programacion.plan_trabajo
  ADD COLUMN IF NOT EXISTS numero_personas_app numeric(8,2),
  ADD COLUMN IF NOT EXISTS tiempo_parada_app_min numeric(12,2),
  ADD COLUMN IF NOT EXISTS complementado_en timestamptz;

ALTER TABLE programacion.plan_trabajo
  DROP COLUMN IF EXISTS numero_personas_efectivo,
  DROP COLUMN IF EXISTS tiempo_parada_efectivo_min,
  DROP COLUMN IF EXISTS requiere_parada;

ALTER TABLE programacion.plan_trabajo
  ADD COLUMN numero_personas_efectivo numeric(8,2)
    GENERATED ALWAYS AS (COALESCE(numero_personas,numero_personas_app)) STORED,
  ADD COLUMN tiempo_parada_efectivo_min numeric(12,2)
    GENERATED ALWAYS AS (COALESCE(tiempo_parada_min,tiempo_parada_app_min)) STORED,
  ADD COLUMN requiere_parada boolean
    GENERATED ALWAYS AS (
      CASE
        WHEN COALESCE(tiempo_parada_min,tiempo_parada_app_min) IS NULL THEN NULL
        ELSE COALESCE(tiempo_parada_min,tiempo_parada_app_min) > 0
      END
    ) STORED;

ALTER TABLE programacion.plan_trabajo
  DROP CONSTRAINT IF EXISTS plan_numero_personas_app_check,
  DROP CONSTRAINT IF EXISTS plan_tiempo_parada_app_check;

ALTER TABLE programacion.plan_trabajo
  ADD CONSTRAINT plan_numero_personas_app_check
    CHECK (numero_personas_app IS NULL OR numero_personas_app > 0),
  ADD CONSTRAINT plan_tiempo_parada_app_check
    CHECK (tiempo_parada_app_min IS NULL OR tiempo_parada_app_min >= 0);

ALTER TABLE programacion.tecnico
  ADD COLUMN IF NOT EXISTS especialidad_app varchar(20),
  ADD COLUMN IF NOT EXISTS complementado_en timestamptz;

ALTER TABLE programacion.tecnico
  DROP COLUMN IF EXISTS especialidad_efectiva;

ALTER TABLE programacion.tecnico
  ADD COLUMN especialidad_efectiva varchar(20)
    GENERATED ALWAYS AS (COALESCE(especialidad,especialidad_app)) STORED;

ALTER TABLE programacion.tecnico
  DROP CONSTRAINT IF EXISTS tecnico_especialidad_app_check;

ALTER TABLE programacion.tecnico
  ADD CONSTRAINT tecnico_especialidad_app_check
    CHECK (especialidad_app IS NULL OR especialidad_app IN ('MEC','ELE','MET','SER'));

COMMENT ON COLUMN programacion.plan_trabajo.numero_personas IS 'Valor exportado por el software de mantenimiento.';
COMMENT ON COLUMN programacion.plan_trabajo.numero_personas_app IS 'Valor complementado manualmente en la aplicación cuando el software está vacío.';
COMMENT ON COLUMN programacion.plan_trabajo.numero_personas_efectivo IS 'Usa primero el software; si está vacío, usa el valor aprendido en la app.';
COMMENT ON COLUMN programacion.plan_trabajo.tiempo_parada_min IS 'Tiempo de parada exportado por el software.';
COMMENT ON COLUMN programacion.plan_trabajo.tiempo_parada_app_min IS 'Tiempo de parada completado en la app cuando el software está vacío. 0 significa que no requiere equipo detenido.';
COMMENT ON COLUMN programacion.plan_trabajo.requiere_parada IS 'NULL=falta dato; FALSE=tiempo de parada 0; TRUE=tiempo de parada mayor que 0.';
COMMENT ON COLUMN programacion.tecnico.especialidad IS 'Especialidad exportada por el software.';
COMMENT ON COLUMN programacion.tecnico.especialidad_app IS 'Especialidad completada en la app si falta en el software.';
