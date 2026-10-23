# Estudio funcional de TEAM FOOD

## Qué debe ser esta aplicación

TEAM FOOD debe ayudar a decidir qué mantenimiento hacer, con qué capacidad, cuándo y con qué resultado verificable. El software externo conserva los maestros y los estados fuente. Esta aplicación conserva la planeación, los turnos, la programación, la conciliación, el backlog, los cierres y la trazabilidad. La evolución recomendada es fortalecer ese circuito antes de convertirla en un sistema completo de confiabilidad o costos.

## Diagnóstico del punto de partida

El panel de control tiene una jerarquía útil: carga pendiente, capacidad disponible, accesos al proceso y avance del período. Se conserva esa composición. El problema principal estaba en los recorridos: indicadores y seguimiento estaban ocultos fuera del menú; preparación mezclaba cartera y exclusiones; importación se montaba en dos lugares; varias pantallas repetían títulos y ayudas sin aclarar el siguiente paso.

Había diferencias de significado entre cartera mensual, ejecuciones semanales y cierres oficiales. Un número de OT puede repetirse en semanas de reprogramación, mientras cada identidad de actividad del mes se cuenta una vez en la cartera. Las actividades excluidas por operación no deben sumar cumplimiento de mantenimiento. Una finalización constatada en octubre sin fecha real tampoco demuestra ejecución en octubre.

Se detectaron defectos de consultas: ANULADA entraba en backlog activo y podía volver a finalizarse durante una conciliación; las tarjetas de backlog eran globales aunque las filas estuvieran filtradas; los indicadores por especialidad tenían un universo distinto del panel general. Los cambios de esta entrega se dirigen a esos casos, sin alterar cierres ni estados históricos.

## Estructura funcional propuesta

| Etapa | Pantallas | Decisión que facilita |
|---|---|---|
| Inicio | Panel de control, Indicadores | Qué necesita atención y cómo avanza el período |
| Preparar | PMP del mes, Paradas, Técnicos | Qué está listo y con qué recursos contamos |
| Ejecutar | Programación semanal, Seguimiento, Backlog | Qué se asigna, qué avanza y qué queda pendiente |
| Cerrar | Cierre semanal, Cierre mensual | Qué resultado se confirma y qué debe conciliarse |
| Datos | Cargar Excel, Completar datos, Excluidas | Qué fuente se cargó, qué falta y qué no pertenece a mantenimiento |

Todas conservan los enlaces actuales. El contexto de trabajo identifica período y alcance; Backlog aclara que acumula períodos. Las acciones siguientes guían el proceso sin asumir que todos los requisitos están cumplidos.

## Indicadores que conviene utilizar ahora

| Indicador | Definición / alcance | Uso |
|---|---|---|
| Avance de cartera por OT | Actividades finalizadas constatadas / universo de cartera y backlog del panel, sin operación | Avance general y por especialidad con la misma autoridad |
| Avance por H-H estimadas | H-H estimadas de actividades finalizadas / H-H estimadas de cartera | Distingue terminar muchas tareas cortas de terminar mayor carga |
| Cumplimiento semanal | Ejecuciones finalizadas / ejecuciones programadas, por semana y especialidad | Evalúa la programación y la reprogramación; no confundir con OT únicas |
| Resultado de cierre | Resultado confirmado en semanas formalmente cerradas | Informe oficial, separado del seguimiento provisional |
| Pendiente disponible | PMP y backlog disponibles sin duplicar la misma identidad | Preparar la siguiente programación; los subtotales pueden solaparse |
| Capacidad y carga | H-H disponibles y H-H programadas con fórmula existente | Detecta sobrecarga o capacidad libre, sin cambiar la regla doble80 |
| Backlog por antigüedad | Pendientes activos hasta30,31–60,61–90,más90 días desde fecha origen registrada | Prioriza rezago; fecha origen no equivale automáticamente a vencimiento |
| Backlog crítico | Pendientes activos de equipos con criticidadA | Prioriza impacto potencial con criticidad del maestro |
| Calidad de información | Planes incompletos, H-H no calculables, finalizaciones sin fecha real | Hace visible qué resultados requieren revisión |
| Excluidas por operación | Actividades conservadas por período y especialidad, fuera del cumplimiento | Control de integridad de importación y conciliación |

Las metas deben definirse con el equipo después de observar una línea base y acordar criticidad, calendario y responsables. No se introducen semáforos de éxito basados en porcentajes arbitrarios.

## Indicadores para una segunda etapa

1. Backlog en semanas de capacidad: H-H de backlog ejecutable / capacidad semanal utilizable de la misma especialidad. Requiere acordar reservas y alcance; no mezclar capacidad mensual con backlog semanal.
2. Cumplimiento dentro de la fecha comprometida: requiere fecha prometida y fecha real de fin, no usar FECHA PROG como fin real.
3. Porcentaje planificado frente a emergente: requiere clasificación fiable preventiva/correctiva/emergencia y horas reales o estimadas identificadas.
4. Reprogramaciones y motivos de incumplimiento: disponibilidad de equipo, repuestos, permisos, personal y alcance. Facilita eliminar causas repetidas.
5. Disponibilidad, MTBF y MTTR: incorporar cuando existan eventos de falla, horas de operación, inicio/fin de indisponibilidad y reparación por equipo. No calcularlos con las órdenes preventivas actuales.
6. Costos por activo/área y desviación plan/real: requiere mano de obra real, materiales, contratistas y costos homogéneos.

La guía del Departamento de Energía de EE.UU. recomienda seguir órdenes generadas/cerradas y backlog para entender carga y efectividad. IBM explica que MTBF y MTTR necesitan información de fallas y recuperación; por eso se reservan para una etapa con esos datos.

## Cambios técnicos y de operación siguientes, por prioridad

| Prioridad | Propuesta | Razón |
|---|---|---|
| Alta | Registro de lotes de importación con hash, actor, fecha, archivo, filas aceptadas/rechazadas y vista previa | Permite conciliar y revertir una carga puntual sin reemplazar el mes |
| Alta | Importación de exclusiones que preserve conciliaciones complementarias | La importación mensual actual reemplaza las exclusiones del período |
| Alta | Identidad estable de actividad cuando una misma OT contiene varias actividades | La identidad por ocurrencia puede variar si se reordena el archivo |
| Alta | Bandeja de diferencias entre fuente y cierre | Ejemplo: OT-10948-26 anulada en Excel y pendiente en la aplicación; revisar sin reescribir el cierre44 |
| Media | Guardar datos y H-H de referencia en el cierre | Los maestros vivos pueden cambiar resultados históricos recalculados |
| Media | Selección explícita de año y período persistido; se conserva2026 en este release | Preparar operación de períodos futuros y evitar aperturas en octubre por defecto |
| Media | Auditoría individual de usuarios y permisos por función | La aplicación tiene modo administrador; conviene avanzar a identidad individual trazable |
| Media | Automatizar pruebas de ciclo completo y despliegue | Evita regresiones entre importación, programación, seguimiento y cierre |

La documentación antigua decía que el importador base borraba tablas. La revisión del código actual confirmó UPSERTs; ese diagnóstico antiguo debe actualizarse y no se presenta como defecto vigente.

## Recuperación y límites

Código base: abbdae3c05aceb31da35100a2e859492cb161cb5, coincidente con producción antes de los cambios. ZIP guardado en backups del workspace. Snapshot de negocio id2 en programacion.programming_backup_snapshot (PROGRAMADOR), después de las conciliaciones eléctricas y mecánicas. Deploy anterior: 3ouyqm5TA8mpid1MVnnouXPPKSoG / programacion-team-food-9i7l7fv55-cek-global.vercel.app.

Esta reorganización no necesita migración ni modificación de los datos de negocio. Volver al diseño anterior requiere revertir el código y redesplegar; el backup de BD solo se usa con revisión de movimientos posteriores, para evitar perder trabajo nuevo. No se han prometido horas reales, ejecución en una fecha desconocida, confiabilidad ni disponibilidad sin fuentes suficientes.

## Referencias consultadas

- [DOE — Operations and Maintenance Best Practices, Release3.0](https://www1.eere.energy.gov/femp/pdfs/om_3.pdf)
- [IBM — MTTR vs. MTBF](https://www.ibm.com/think/topics/mttr-vs-mtbf)
- Código, consultas y contratos actuales de este repositorio; revisión lectura de la base PROGRAMADOR y pantallas de producción. Los hallazgos internos son conclusiones de esa revisión, no afirmaciones de las referencias externas.
