# PROGRAMACIÓN TEAM FOOD — Arquitectura preservada para reinicio V2

## Objetivo

Aplicación para programación semanal de mantenimiento de TEAM FOOD. La base de datos puede reconstruirse desde cero, pero se conserva la arquitectura funcional de la aplicación y el conocimiento del flujo operativo.

## Stack

- Frontend: React + Vite.
- Backend: FastAPI / Python.
- Base de datos: Supabase PostgreSQL.
- Hosting: Vercel.
- Repositorio: GitHub `carlosrecio29-prog/PROGRAMACION-TEAM-FOOD-`.
- Producción: rama `main` despliega automáticamente en Vercel.
- Migraciones V2: `supabase/migrations_v2/`.
- Las migraciones anteriores en `supabase/migrations/` quedan como referencia histórica y NO deben reaplicarse al nuevo modelo.

## Estructura de aplicación que se conserva

### Frontend

- `frontend/src/App.jsx`: navegación y flujo principal.
- `frontend/src/api.js`: cliente del backend.
- `frontend/src/components/ImportPanel.jsx`: cargas operativas.
- `frontend/src/components/MasterImportPanel.jsx`: carga del maestro TEAM FOOD.
- `frontend/src/components/PendingDefinitions.jsx`: aprendizaje de datos faltantes del PlanTrabajo.
- `frontend/src/components/SpecialtyPlanner.jsx`: selección/programación por especialidad.
- `frontend/src/components/SavedProgramming.jsx`: programación guardada.
- `frontend/src/styles.css`: estilo corporativo blanco/azul/gris.

### Backend

- `api/index.py`: entrada de FastAPI en Vercel.
- `backend/database.py`: conexión PostgreSQL.
- `backend/parsers/team_food.py`: parser del archivo maestro TEAM FOOD.
- `backend/parsers/masters.py`: parsers de maestros auxiliares.
- `backend/parsers/operational.py`: parsers de archivos operativos.
- `backend/services/team_food_service.py`: importación/sincronización del maestro.
- `backend/services/import_service.py`: importaciones.
- `backend/services/definition_service.py`: aprendizaje de NumeroPersonas / EquipoDetenido.
- `backend/services/query_service.py`: consultas y KPI.
- `backend/services/programming_service.py`: programación semanal, cierres y exportaciones.

## Reglas de negocio que NO deben olvidarse

### Maestro PLAN DE TRABAJO

La hoja `PLAN DE TRABAJO` de TEAM FOOD es la referencia para los planes.

Campos principales identificados:

- `Grupo`
- `DescripcionGrupo`
- `PlanTrabajo`
- `DescripcionPlanTrabajo` / equivalente del maestro
- `Especialidad`
- `TiempoEjecucion`
- `TiempoParada`
- `NumeroPersonas`
- `Estado`
- `EquipoDetenido` añadido al maestro conceptual

### Aprendizaje progresivo

NO se llena todo el maestro de una vez.

Cuando un PMP del mes usa un PlanTrabajo:

1. Buscar el PlanTrabajo en el historial maestro.
2. Si ya tiene `NumeroPersonas`, reutilizarlo.
3. Si no tiene `NumeroPersonas`, pedirlo al usuario y guardarlo.
4. Si ya se conoce `EquipoDetenido`, reutilizarlo.
5. Si no se conoce, preguntar:
   - SI = requiere equipo detenido.
   - NO = puede ejecutarse con equipo operando.
6. Cuando el mismo PlanTrabajo vuelva a aparecer otro mes, no volver a preguntar.

`TiempoParada` NO determina automáticamente si el equipo debe detenerse.

### Cálculo H-H

`HH = TiempoEjecucion_min / 60 × NumeroPersonas`.

### PMP mensual

El usuario entrega los PMP del mes. Para el reinicio V2 comenzaremos por septiembre de 2026.

Los PMP deben relacionarse con:

- PlanTrabajo.
- Activo/equipo.
- Especialidad.
- Número de OT.
- Estado PENDIENTE / FINALIZADA.
- Tiempo planeado cuando corresponda.

### Programación semanal

- Especialidades: MEC, ELE, MET, SER.
- H-H objetivo: 80 % programable.
- Standby: 20 %.
- La aplicación bloquea programación si supera la capacidad objetivo.
- Solo los planes que se utilicen y tengan datos faltantes deben pedir aprendizaje.

### Personal / turnos

Se conserva la lógica de técnicos, turnos, ausencias y H-H disponibles.

Turnos base:
- T1 06:00–14:00
- T2 14:00–22:00
- T3 22:00–06:00

También existen códigos adicionales y ausencias (VA, IN, DE, COMP, PERM).

## Regla de área de equipos

En los códigos de activos de Barranquilla, el segundo segmento identifica el área:

`BA-<AREA>-...`

Ejemplo: `BA-EM-X-X-X` → `area_codigo = EM`.

Este dato se calcula automáticamente y NO reemplaza `ubicacion`, porque `ubicacion` representa una referencia física más específica del equipo.

## Principio de diseño V2

La nueva base debe ser mínima y comprensible.

Primero se construirá únicamente:

1. Maestro PlanTrabajo.
2. Activos.
3. Relación Activo ↔ PlanTrabajo.
4. Técnicos y turnos.
5. PMP mensual y órdenes.
6. Disponibilidad de técnicos.
7. Después de validar septiembre, programación semanal y cierres.

No crear tablas auxiliares, historiales o vistas hasta que exista una necesidad real.

## Estado del reinicio

El 2 de septiembre de 2026 se decidió borrar todas las tablas y schemas personalizados de Supabase y reconstruir la base desde cero.

No borrar ni modificar schemas internos administrados por Supabase como `auth`, `storage`, `extensions`, `realtime` o `supabase_migrations`.
