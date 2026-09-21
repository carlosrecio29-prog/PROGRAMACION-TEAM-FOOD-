-- Clasificación reversible de planes delegados al área de OPERACIÓN.
-- Nunca elimina órdenes ni programaciones históricas.
ALTER TABLE programacion.plan_trabajo
  ADD COLUMN IF NOT EXISTS es_operacion boolean NOT NULL DEFAULT false;

UPDATE programacion.plan_trabajo
SET es_operacion = (
  plan_trabajo ~* '^[[:space:]]*([0-9]+[[:space:]]*[-–—:._/|]+[[:space:]]*)?OPERACI[OÓ]N([[:space:]]|[-–—:._/|]|$)'
)
WHERE es_operacion IS DISTINCT FROM (
  plan_trabajo ~* '^[[:space:]]*([0-9]+[[:space:]]*[-–—:._/|]+[[:space:]]*)?OPERACI[OÓ]N([[:space:]]|[-–—:._/|]|$)'
);

COMMENT ON COLUMN programacion.plan_trabajo.es_operacion IS
 'Excluye el plan del PMP, programación y backlog activos de mantenimiento; conserva historia y catálogo.';
