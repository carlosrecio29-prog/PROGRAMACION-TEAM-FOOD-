## 1. Contract and migration design

- [x] 1.1 Review the active V2 closure runtime and record the backend/database/frontend handoff for accumulated backlog work.
- [x] 1.2 Add a new additive V2 migration for backlog active status, first origin, last scheduling/closure references, reprogramming count, finalization outcome and supporting indexes.
- [x] 1.3 Backfill existing active backlog records idempotently without modifying closed programming history or applied migrations.
- [x] 1.4 Preserve one tracking record per OT and valid backlog lifecycle states with database constraints.

## 2. Backlog lifecycle and API

- [x] 2.1 Replace backlog deletion-on-scheduling behavior with transactional transitions between PENDIENTE_DISPONIBLE and PENDIENTE_PROGRAMADA.
- [x] 2.2 Update weekly closure transitions so PENDIENTE and NO_ENCONTRADA create or update a Pending backlog record, while FINALIZADA records finalization and closes active tracking.
- [x] 2.3 Preserve first origin and increment reprogramming traceability across repeated scheduling and closure cycles.
- [x] 2.4 Add a V2 Backlog read contract with OT, state, specialty, area, age and text filters, active rows and indicators for moved and engineer-finalized OT.
- [x] 2.5 Keep weekly programming candidate responses limited to PENDIENTE_DISPONIBLE and retain conflict validation for overlapping open programming.

## 3. Platform UX foundation

- [x] 3.1 Extract the V2 application shell, navigation and shared visual primitives from App.jsx while preserving existing module access and active-period context.
- [x] 3.2 Reorganize navigation into Inicio, Planificacion, Cierre, Backlog and Administracion, mapping every existing view without removing functionality.
- [x] 3.3 Establish consistent responsive patterns for headers, indicators, filters, tables, empty/loading/error states, focus and keyboard operation.

## 4. Redesign operational modules

- [x] 4.1 Redesign Inicio/Resumen as an operational overview with actionable states while retaining dashboard data and navigation to existing workflows.
- [x] 4.2 Integrate Programacion semanal into Planificacion, preserving separate group filters, stable selection context, backend capacity authority and candidate eligibility.
- [x] 4.3 Redesign Cierre semanal with programadas, finalizadas, pendientes and compliance H-H indicators sourced from V2 results.
- [x] 4.4 Add the result-row action that opens Backlog filtered to PENDIENTE and NO_ENCONTRADA OT, and omit it for FINALIZADA rows.
- [x] 4.5 Build the dedicated Backlog workspace with moved and engineer-finalized indicators, active pending list, lifecycle badges, traceability and independent filters.
- [x] 4.6 Re-style Completar datos, PMP del mes and Tecnicos with the shared patterns without changing their data flows or mutations.

## 5. Integration handoff

- [x] 5.1 Record backend/database/frontend handoff for integration.
