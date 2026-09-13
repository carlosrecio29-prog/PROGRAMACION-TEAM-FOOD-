## Why

La pantalla de Programación semanal concentra demasiada información y acciones en un flujo vertical difícil de recorrer. Además, al seleccionar o quitar una OT la vista puede desplazarse inesperadamente, interrumpiendo la revisión de actividades. Este cambio mejora la claridad y continuidad del trabajo del planeador sin alterar la identidad visual CEK ni los contratos de backend.

## What Changes

- Evitar cualquier salto de `window` o del scroll interno de las tablas al seleccionar o quitar una OT.
- Reorganizar Programación semanal en una jerarquía más compacta: contexto de semana/especialidad, capacidad resumida, actividades disponibles, selección actual y acciones.
- Proporcionar filtros independientes para Equipo operando, Parada requerida y Backlog.
- Mantener separado el estado de búsqueda y área de cada grupo para que filtrar un grupo no modifique los demás.
- Hacer más accesibles y persistentes las acciones de guardar, cancelar y exportar durante la revisión.
- Extraer gradualmente la pantalla semanal y sus piezas visuales desde `App.jsx`, sin reescritura masiva.
- Consolidar los overrides visuales V2 para reducir inconsistencias entre `styles.css` y `backlog.css`.
- Añadir pruebas de interacción para selección, eliminación, filtros independientes y estabilidad de scroll.

## Capabilities

### New Capabilities

- `frontend/weekly-programming-ux`: comportamiento de interacción y organización visual de la pantalla de Programación semanal.

### Modified Capabilities

No se modifican requisitos de dominio existentes; el cambio se limita al comportamiento y la presentación del frontend.

## Impact

- Frontend: `frontend/src/App.jsx`, nuevos componentes de planificación y estilos V2 en `frontend/src/styles.css` y `frontend/src/backlog.css`.
- QA: pruebas de interacción/renderizado del frontend y verificación responsive.
- API/backend: sin cambios previstos; se conservan los contratos y la autoridad backend para capacidad y HH.
- Datos y dominio: no se modifican persistencia, backlog, cierres ni reglas de capacidad.
