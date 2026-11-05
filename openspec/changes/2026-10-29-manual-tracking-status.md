# Estado manual en seguimiento semanal

Las OT de una programación abierta admiten una decisión manual `FINALIZADA`, `PENDIENTE` o `ANULADA`. La Lista de Calendario sigue importándose y conserva su resultado automático; una decisión manual vigente tiene precedencia, queda auditada y se marca como discrepante cuando difiere del Excel. Las semanas cerradas permanecen inmutables.

Los indicadores usan el estado efectivo: finalizada suma OT y H-H, pendiente queda pendiente y anulada se excluye del denominador de cumplimiento. La agregación mensual deduplica por OT/especialidad para no duplicar una OT seguida por su cierre.


## Conciliación de cierre semanal

Cuando se comparan las OT programadas con el Excel de Lista de Calendario,
la decisión persistida en `seguimiento_estado_manual_v2` prevalece para la
misma `programacion_item_id`. Esto incluye OT ausentes en el Excel; dejan
de ser «sin identificar» y se presentan como «identificadas manualmente».
La vista previa conserva el estado y la razón de coincidencia del Excel
para auditoría, incluso cuando difieren. Al confirmar el cierre se vuelven
a leer las decisiones de la base, sin confiar en el estado de la vista previa.
Las FINALIZADAS suman cumplimiento y HH; PENDIENTES van a backlog; ANULADAS
se excluyen de cumplimiento y backlog. Las órdenes sin resolución manual
continúan las validaciones existentes.
