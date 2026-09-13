## 1. Preparación y estado de la pantalla

- [x] 1.1 Confirmar el comportamiento actual de selección, quitar OT, cambio de semana/especialidad y filtros mediante una matriz de casos reproducibles.
- [x] 1.2 Extraer la estructura de estado de filtros a un modelo independiente para `operating`, `stopped` y `backlog`, con actualización localizada por grupo.

## 2. Corrección de interacción y filtros

- [x] 2.1 Ajustar la selección y eliminación de OT para que no provoquen desplazamiento de la ventana ni del contenedor de tabla, manteniendo las validaciones de capacidad actuales.
- [x] 2.2 Implementar una barra de filtros propia dentro de cada grupo de actividades, con búsqueda y área independientes.
- [x] 2.3 Verificar que la selección, eliminación, cambio de semana y cambio de especialidad no reinicien los filtros de los grupos que permanecen en la vista.
- [x] 2.4 Mantener los mensajes de error/éxito y los contadores sincronizados con la selección sin recalcular HH o capacidad en el frontend.

## 3. Reorganización de componentes

- [x] 3.1 Extraer `WeeklyProgramming` y sus subcomponentes visuales desde `App.jsx` sin cambiar los contratos de `api.js`.
- [x] 3.2 Separar componentes de contexto semanal, resumen de capacidad, grupo de actividades, selección actual y acciones de guardado/exportación.
- [x] 3.3 Aplicar una jerarquía visual compacta que conserve las distinciones semánticas de Equipo operando, Parada requerida y Backlog.
- [x] 3.4 Mantener el modo de consulta solo lectura y el modo de edición, incluyendo sus acciones habilitadas/deshabilitadas.

## 4. Consolidación visual y responsive

- [x] 4.1 Auditar los selectores V2 duplicados entre `styles.css` y `backlog.css` y consolidar solo los overrides relacionados con la pantalla semanal.
- [x] 4.2 Implementar el layout responsive de las tres barras de filtros y de las acciones principales sin introducir dependencias nuevas.
- [x] 4.3 Revisar visualmente Resumen, Cierre semanal y PMP para asegurar que la limpieza de estilos no provoque regresiones.

## 5. Verificación

- [x] 5.1 Añadir pruebas de interacción para seleccionar/quitar OT conservando la posición de scroll.
- [x] 5.2 Añadir pruebas de aislamiento y persistencia de filtros para los tres grupos.
- [x] 5.3 Ejecutar `npm run build` y los scripts de verificación del repositorio: `bash scripts/verify.sh`, `python scripts/check_agent_ownership.py` y `python scripts/check_destructive_changes.py`.
- [x] 5.4 Realizar una comprobación manual responsive y documentar cualquier ajuste visual pendiente antes de integrar.
