# Atribución de finalizaciones fuera de programación a semana pendiente de cierre

Fecha: 2026-11-19. Especialidad diagnosticada: Servicio (SER), noviembre 2026.

## Situación
La semana operativa del 12 al 18 de noviembre está GUARDADA, no CERRADA. La sincronización del jueves 19/11 a las 06:04 (America/Bogota) reportó 12 OT de Servicio FINALIZADA fuera de ambas programaciones semanales, pero la consulta anterior limitaba el registro a la fecha calendario del miércoles 18 y devolvía 0 OT para semana 2.

## Decisión
La fecha de corte (miércoles) es la referencia de planeación, pero no debe ocultar estados que llegaron mientras el cierre formal sigue pendiente. Atribuir la primera detección de FINALIZADA a la programación semanal elegible más antigua de la especialidad que todavía no estuviera formalmente cerrada cuando ocurrió dicha detección. Para una semana ya cerrada, mantener únicamente detecciones con timestamp menor o igual que cierre_en/cerrado_en; si no hay fecha formal registrada, limitar a su ventana calendario. Esto evita duplicar una misma primera detección entre semanas guardadas.

Se excluyen actividades OPERACIÓN y OT de la programación de la propia semana. Si no existe una programación semanal guardada elegible, usar el rango calendario para la vista consultada como antes.

Esta atribución es **solo de detección** y **no demuestra** que la ejecución física ocurrió en esa semana. La interfaz debe distinguir las detecciones posteriores al miércoles y no alterar indicadores de cumplimiento programado, H-H, cierre de semana ni historiales.

## Verificación de datos (solo lectura)
Consulta de conciliación contra Supabase: semana SER #56 (12–18/11) GUARDADA, semana #51 CERRADA el 12/11. Resultado con el nuevo criterio: 12 OT sin programación, las 12 detectadas tras el miércoles 18, números OT-15130-26, OT-15151-26, OT-15152-26, OT-15154-26, OT-15155-26, OT-15156-26, OT-15157-26, OT-15158-26, OT-15159-26, OT-15162-26, OT-15163-26 y OT-15164-26.

## Archivos
- backend/services/v2_sheet_sync_service.py: consulta de solo lectura y campo posteriores_al_corte.
- frontend/src/components/WeeklyTracking.jsx: explicación y contador del alcance extendido.
- tests/test_weekly_outside_sync_detections.py: contrato SQL y caso de detección al día siguiente antes del cierre.

No se modificaron datos de programación, estados, ni cierres en la base.