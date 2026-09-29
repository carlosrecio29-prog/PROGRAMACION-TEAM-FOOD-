ALTER TABLE programacion.tecnico
  DROP COLUMN especialidad_efectiva;

ALTER TABLE programacion.tecnico
  ADD COLUMN especialidad_efectiva text
  GENERATED ALWAYS AS (COALESCE(especialidad_app, especialidad)) STORED;

COMMENT ON COLUMN programacion.tecnico.especialidad_efectiva IS
  'Especialidad usada por la aplicación. Una asignación manual en especialidad_app tiene prioridad sobre la especialidad importada del software.';
