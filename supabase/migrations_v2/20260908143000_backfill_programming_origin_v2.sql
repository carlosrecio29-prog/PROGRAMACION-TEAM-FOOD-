-- Normaliza el origen de las OT ya programadas antes de habilitar la columna visible de origen.
-- Es idempotente y puede ejecutarse nuevamente sin cambiar resultados correctos.

UPDATE programacion.programacion_item_v2
SET origen = 'BACKLOG'
WHERE origen_backlog = true
  AND origen IS DISTINCT FROM 'BACKLOG';

UPDATE programacion.programacion_item_v2
SET origen = 'PMP_MES'
WHERE origen_backlog = false
  AND origen IS DISTINCT FROM 'PMP_MES';

COMMENT ON COLUMN programacion.programacion_item_v2.origen IS
'Origen persistente de la OT al momento de programarla: PMP_MES o BACKLOG.';
