## 1. Contract and migration design

- [ ] 1.1 Review the active V2 closure runtime and record the backend/database/frontend handoff for accumulated backlog work.
- [ ] 1.2 Add a new additive V2 migration for backlog active status, first origin, last scheduling/closure references, reprogramming count, finalization outcome and supporting indexes.
- [ ] 1.3 Backfill existing active backlog records idempotently without modifying closed programming history or applied migrations.
- [ ] 1.4 Add database-level constraints and tests that preserve one active tracking record per OT and prevent invalid lifecycle states.

## 2. Backlog lifecycle and API

- [ ] 2.1 Replace backlog deletion-on-scheduling behavior with transactional transitions between PENDIENTE_DISPONIBLE and PENDIENTE_PROGRAMADA.
- [ ] 2.2 Update weekly closure transitions so PENDIENTE and NO_ENCONTRADA create or update a Pending backlog record, while FINALIZADA records finalization and closes active tracking.
- [ ] 2.3 Preserve first origin and increment reprogramming traceability across repeated scheduling and closure cycles.
- [ ] 2.4 Add a V2 Backlog read contract with OT, state, specialty, area, age and text filters, active rows and indicators for moved and engineer-finalized OT.
- [ ] 2.5 Keep weekly programming candidate responses limited to PENDIENTE_DISPONIBLE and retain conflict validation for overlapping open programming.
- [ ] 2.6 Add API/service tests for pending -> reprogrammed -> pending -> finalized, no-match handling, finalization, filtering and duplicate-assignment rejection.

## 3. Platform UX foundation

- [ ] 3.1 Extract the V2 application shell, navigation and shared visual primitives from App.jsx while preserving existing module access and active-period context.
- [ ] 3.2 Reorganize navigation into Inicio, Planificacion, Cierre, Backlog and Administracion, mapping every existing view without removing functionality.
- [ ] 3.3 Establish consistent responsive patterns for headers, indicators, filters, tables, empty/loading/error states, focus and keyboard operation.
- [ ] 3.4 Add frontend tests for navigation, accessible controls and local filter state preservation.

## 4. Redesign operational modules

- [ ] 4.1 Redesign Inicio/Resumen as an operational overview with actionable states while retaining dashboard data and navigation to existing workflows.
- [ ] 4.2 Integrate Programacion semanal into Planificacion, preserving separate group filters, stable selection context, backend capacity authority and candidate eligibility.
- [ ] 4.3 Redesign Cierre semanal with programadas, finalizadas, pendientes and compliance H-H indicators sourced from V2 results.
- [ ] 4.4 Add the result-row action that opens Backlog filtered to PENDIENTE and NO_ENCONTRADA OT, and omit it for FINALIZADA rows.
- [ ] 4.5 Build the dedicated Backlog workspace with moved and engineer-finalized indicators, active pending list, lifecycle badges, traceability and independent filters.
- [ ] 4.6 Re-style Completar datos, PMP del mes and Tecnicos with the shared patterns without changing their data flows or mutations.
- [ ] 4.7 Verify desktop and narrow viewport workflows do not hide actions, reset unrelated filters or introduce page-scroll jumps.

## 5. Integration and quality gates

- [ ] 5.1 Add or update frontend unit tests for backlog indicators, lifecycle rendering, closure-to-backlog navigation and filter entry context.
- [ ] 5.2 Add backend/API regression tests confirming H-H and capacity remain backend-authoritative throughout scheduling and closure.
- [ ] 5.3 Perform visual QA of Inicio, Planificacion, Cierre, Backlog and Administracion in desktop and narrow viewports.
- [ ] 5.4 Run OpenSpec strict validation, frontend build/tests, backend tests, ownership and destructive-change checks, and the repository verification suite.
- [ ] 5.5 Record QA evidence and cross-domain handoffs before integration.
