# Estado manual en seguimiento semanal

Las OT de una programación abierta admiten una decisión manual `FINALIZADA`, `PENDIENTE` o `ANULADA`. La Lista de Calendario sigue importándose y conserva su resultado automático; una decisión manual vigente tiene precedencia, queda auditada y se marca como discrepante cuando difiere del Excel. Las semanas cerradas permanecen inmutables.

Los indicadores usan el estado efectivo: finalizada suma OT y H-H, pendiente queda pendiente y anulada se excluye del denominador de cumplimiento. La agregación mensual deduplica por OT/especialidad para no duplicar una OT seguida por su cierre.
