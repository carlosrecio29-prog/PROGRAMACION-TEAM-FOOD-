# Corrección semanal OT fuera de programación: calendario frente a cierre formal

Fecha: 2026-11-19. Alcance: las cuatro especialidades (ELE, MEC, MET, SER).

## Defecto identificado
La regla inicial asignaba cada primera detección FINALIZADA a la semana guardada **más antigua** que aún fuera elegible por no haber completado su cierre formal. Los cierres de la semana 1 se efectuaron el 12 de noviembre en la tarde (MEC 21:13 UTC, ELE 21:19 UTC). La sincronización del 12 de noviembre a las 19:40 UTC ocurrió antes de esos cierres, pero ya dentro de la **semana calendario 2**, por lo que el algoritmo clasificó erróneamente a la semana 1 las detecciones del 12/11. Como consecuencia, Eléctrico mostraba solamente 12 OT fuera de programación en semana 2, y Mecánica también omitía numerosas OT.

## Regla corregida
- Si la primera detección de una OT finalizada corresponde al calendario de una semana semanal guardada, atribuirla a **esa** semana incluso si la semana anterior se cerró más tarde el mismo día.
- Si la detección ocurre después del fin de calendario de todas las semanas guardadas relevantes, atribuirla a la semana **más reciente aún elegible** (pendiente de cierre formal).
- Nunca asignar una detección posterior al cierre formal de una semana cerrada. No sumar a programadas las OT fuera de programación. Una misma OT aporta una primera detección como máximo a una semana; excluir OPERACIÓN.
- Se trata de una atribución **por detección de Google Sheets**, no de la fecha física real del mantenimiento.

## Evidencia de verificación (SQL de la consulta de producción en modo lectura)
Para semana 2 de noviembre (12 al 18; las cuatro semanas de especialidad todavía GUARDADA), al consultar la misma SQL actualizada en Supabase:
- ELE: **68 finalizadas fuera de semana 2** = 63 sin programación en el mes + 5 programadas en otra semana, con 3 detectadas el 19/11.
- MEC: **36** = 1 sin programación del mes + 35 programadas en otra semana, con 0 detectadas después del 18.
- MET: **20** = 11 sin programación del mes + 9 programadas en otra semana.
- SER: **12** = 12 sin programación del mes, las 12 detectadas el 19/11.
Para comparar: semana 1 ELE devuelve 111, MEC 3. Estas cifras son *por primera detección* dentro del ámbito semanal, no el conjunto de todas las finalizadas del mes.

## Archivos y garantías
- backend/services/v2_sheet_sync_service.py: ordenar primero por pertenencia a ventana calendario, luego semana de inicio descendente.
- frontend/src/components/WeeklyTracking.jsx: explicar fecha calendario y detecciones posteriores a corte.
- tests/test_weekly_outside_sync_detections.py: añadir regresión por sincronización en 12/11 anterior al cierre de semana 1.
- No migración, cambios de órdenes, estados ni cierres; consulta de solo lectura.