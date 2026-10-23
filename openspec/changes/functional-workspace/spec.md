# Espacio de trabajo funcional de mantenimiento

## Objetivo autorizado
Ordenar toda la aplicación manteniendo la composición del Panel de control aprobada por el usuario. La aplicación conecta fuentes externas con preparación, programación, seguimiento, cierre y mejora del mantenimiento.

## Alcance de esta entrega
- Navegación completa y accesible: Inicio (panel e indicadores), Preparar (cartera, paradas, personal), Ejecutar (programación, seguimiento, backlog), Cerrar (semanal y mensual), Datos (importación, calidad y exclusiones). Conservar todos los IDs/rutas existentes.
- Un contexto operativo común en todas las pantallas, acciones claras, tablas legibles y estados de carga/error/vacío consistentes. Mantener el panel actual como referencia visual.
- Indicadores con alcance explícito: cartera única del mes frente a ejecuciones semanales; resultado observado frente a cierre confirmado; H-H estimadas frente a horas reales; operación excluida del cumplimiento.
- Resumen gerencial aditivo, calculado en backend: cartera y finalización con la misma autoridad del dashboard, exclusiones, pendientes de datos y antigüedad/prioridad de backlog activo. No inventar MTBF/MTTR/disponibilidad/OEE sin datos de fallas/operación/horas reales.
- ANULADA es terminal: no activa/programable y no se reactiva en conciliación. Consultable como historial. No modificar datos ni cierres existentes en esta entrega.
- No cambiar política de capacidad doble80 ni fórmulas H-H; no crear migraciones ni reemplazar maestros o importaciones históricas.

## Contrato
Compatibilidad de endpoints actuales obligatoria. Cualquier campo aditivo se documenta antes de consumo frontend. El frontend presenta cálculos de backend, sin reglas de elegibilidad duplicadas.

## Verificación
Pruebas de estados terminales y filtros backlog; contrato indicadores y regresión fuentes existentes; build frontend; validación visual desktop/móvil de todos los módulos y recorrido lectura producción. No probar cargas/cierres contra producción.

## Recuperación
Base de código original abbdae3c05aceb31da35100a2e859492cb161cb5, ZIP ../backups/team-food-before-restructure-abbdae3.zip desde carpeta raíz del repositorio. Snapshot de datos de negocio id2, nombre20261022_antes_reestructuracion_funcional, en programacion.programming_backup_snapshot del proyecto eovzsaufwqsqsjvapbdx. Solo se contempla restauración explícita y acotada tras revisar nuevos datos posteriores; no sobrescribir trabajo nuevo automáticamente.
