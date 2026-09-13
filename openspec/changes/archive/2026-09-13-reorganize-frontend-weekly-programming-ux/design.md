## Context

La pantalla activa de Programación semanal está implementada dentro de `App.jsx`. Su estado combina filtros, selección, carga, edición y mensajes, mientras que `styles.css` y `backlog.css` contienen overrides V2 superpuestos. La selección actual re-renderiza listas completas y luego intenta restaurar la posición del scroll con callbacks temporizados; además existe scroll suave global.

El diseño debe permanecer en V2, conservar los contratos existentes y respetar que capacidad y HH son autoridad del backend.

## Goals / Non-Goals

**Goals:**

- Mantener estable el contexto de scroll durante las mutaciones de selección.
- Modelar filtros como estado independiente por grupo: operating, stopped y backlog.
- Reducir carga cognitiva mediante una jerarquía única y componentes visuales pequeños.
- Mantener visibles o fácilmente accesibles los totales y acciones relevantes.
- Hacer que la reorganización sea incremental y comprobable en desktop y móvil.

**Non-Goals:**

- Cambiar endpoints, payloads, persistencia o reglas de capacidad.
- Rediseñar toda la aplicación en una sola iteración.
- Cambiar la identidad de marca, paleta principal o semántica de los grupos operativos.
- Introducir una librería de UI o una dependencia externa.

## Decisions

1. **Separar el estado de filtros por grupo.** Se usará una estructura equivalente a `{ operating: { search, area }, stopped: { search, area }, backlog: { search, area } }`. Cada `ActivityTable` recibirá su filtro y callback; no se reutilizará un único `search`/`area` para los tres grupos. Se considera Backlog desde el inicio para que el modelo no vuelva a acoplarse después.

2. **Eliminar la restauración temporizada como mecanismo principal de scroll.** La selección debe ser una mutación local de estado que no enfoque controles ni cambie la ruta. Se evitarán los dos `requestAnimationFrame` y el scroll suave global para que el navegador conserve naturalmente el contexto. Si alguna actualización de layout futura lo requiere, se usará una captura/restauración síncrona del contenedor concreto, no de toda la ventana.

3. **Usar un componente de grupo reutilizable.** `ActivityTable` se convertirá en un bloque que encapsule encabezado, filtros, contador y tabla, con una variante semántica para operating/stopped/backlog. Los filtros vivirán junto al encabezado del grupo, lo que hace visible qué conjunto modifican.

4. **Ordenar la página por decisión operativa.** El flujo será: selector de semana/especialidad → resumen compacto de capacidad → programación actual/seleccionada → actividades disponibles por grupo → acciones de guardado. La implementación puede conservar el orden que minimice cambios visuales en la primera entrega, siempre que la selección y las acciones sigan siendo localizables.

5. **Reducir duplicación CSS antes de añadir adornos.** Se identificará una única fuente para tokens y clases V2. Los estilos específicos de la pantalla se agruparán bajo nombres explícitos y se retirarán overrides equivalentes de `backlog.css` solo cuando no cambie la apariencia esperada. No se alterarán reglas de negocio desde CSS.

6. **Extraer por slices, no reescribir App completo.** Primero se extraerán tipos de filtro, barra de filtro/grupo y resumen/acciones si resulta útil; después se moverá la composición de `WeeklyProgramming`. Cada slice conservará las funciones API existentes y permitirá revisar diffs pequeños.

## Risks / Trade-offs

- **[Riesgo]** Quitar la restauración manual podría revelar otro salto causado por un elemento que recibe foco. → **Mitigación:** pruebas de selección con posición inicial en ventana y tabla, y revisión manual en desktop/móvil.
- **[Riesgo]** Los overrides CSS pueden producir cambios visuales involuntarios en otras vistas. → **Mitigación:** limitar selectores al alcance V2, comparar build y realizar una comprobación visual de Resumen, Cierre y PMP.
- **[Riesgo]** Tres filtros separados ocupan más espacio horizontal en pantallas estrechas. → **Mitigación:** cada grupo tendrá una barra responsive que colapsa a una columna, manteniendo su estado.
- **[Riesgo]** Extraer componentes puede alterar cierres sobre `rowMap`, selección o capacidad. → **Mitigación:** mantener esos cálculos en el contenedor de programación y pasar datos/handlers explícitos.
- **[Riesgo]** El scroll suave puede ser una preferencia global usada por otra vista. → **Mitigación:** verificar usos antes de retirarlo globalmente; si no puede eliminarse de inmediato, neutralizarlo solo durante interacciones de programación.

## Migration Plan

1. Implementar filtros por grupo y la corrección de selección sin cambiar API.
2. Extraer los componentes visuales de Programación semanal y consolidar estilos afectados.
3. Ejecutar build, pruebas de interacción y comprobación responsive.
4. Si la revisión visual detecta regresiones, revertir solo el slice CSS/componente correspondiente; no requiere migración de datos ni rollback backend.

## Open Questions

- Ninguna decisión bloqueante. El orden exacto de los bloques puede ajustarse durante la revisión visual mientras se mantenga la jerarquía y el contrato definidos en la especificación.
