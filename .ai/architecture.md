# Mapa de arquitectura y salud actual

## Current architecture

El producto es React/Vite (`frontend/src`) servido junto a FastAPI (`api/index.py`) en Vercel, con PostgreSQL/Supabase y migraciones SQL versionadas. Excel entra por parsers en `backend/parsers`; los servicios V2 persisten y consultan el modelo `programacion`.

## Active runtime

Las rutas V2 de `api/index.py` llaman principalmente a `v2_import_service.py`, `v2_programming_service.py`/`v2_programming_runtime.py` y `v2_closure_service.py`/`v2_close_service.py`. La UI principal está en `frontend/src/App.jsx` y consume `frontend/src/api.js`.

## Legacy paths

V1 incluye los servicios sin prefijo `v2_` en `backend/services/` y `supabase/migrations/`. Se conservan para contexto/compatibilidad, pero no son destino de trabajo nuevo.

## Data flow

Sistema externo → XLSX → parser/normalización → importación V2 → activos, planes, PMP, OT, técnicos y turnos → capacidad → programación semanal → Excel/PDF → exportación externa → cierre/reconciliación → backlog.

## Current technical risks (reviewed October 2026)

- El importador base actual usa UPSERTs; el antiguo diagnóstico de TRUNCATE ya no corresponde al código vigente. La importación mensual todavía reemplaza exclusiones del período y requiere un flujo por lote que conserve conciliaciones complementarias.
- La lógica de programación/capacidad está duplicada entre `v2_programming_service.py` y `v2_programming_runtime.py`.
- El cierre está dividido entre `v2_closure_service.py` y `v2_close_service.py`, con varias migraciones de cierre/backlog.
- Summary/PMP están extraídos a features y navegación/contexto a app; aún hay módulos heredados en App.jsx que conviene extraer por etapas.
- package-lock.json existe; usar npm ci para builds reproducibles. Revisar rangos latest del manifiesto al actualizar dependencias deliberadamente.
- Hay sesión administrador y modo lectura; aún conviene evolucionar a identidad individual y auditoría de importaciones por lote.
- Las migraciones V2 más recientes usan varias columnas de origen/cierre que requieren consolidación de modelo.

## Functional workspace

El menú organiza Inicio, Preparar, Ejecutar, Cerrar y Datos sin cambiar IDs de rutas. `v2_portfolio_service.py` es la autoridad de cartera compartida por dashboard y desglose por especialidad. Cuenta actividades por `orden_mantenimiento.id`, no números de OT distintos. Seguimiento semanal y cierre confirmado conservan sus alcances separados. `management_insights` agrega calidad de datos y backlog actual con corte America/Bogota. ANULADA es terminal en backlog, conciliación y selección nueva; no se reescriben items históricos.

Spec/estudio y recuperación: `openspec/changes/functional-workspace/`.

## Target architecture

Backend nuevo: `backend/domain/`, `imports/`, `workforce/`, `planning/`, `backlog/`, `closure/`, `infrastructure/`, `api/routers/`. Frontend nuevo: `frontend/src/app`, `features/{imports,planning,closure,backlog,technicians}`, `shared`, `api`, `components`. Migrar por slices, sin reescritura masiva.

## Known ambiguities

La política de dos 80% aparece en documentación/UI y en el workflow `apply-capacity-logic.yml`, pero no está aprobada como regla única. También falta decidir el modelo canónico de cierre, la política de reimportación y el momento de exigir auth/RLS.

## Recommended remediation sequence

1. Especificar y probar importación no destructiva e historial de batches.
2. Elegir una autoridad única para capacidad y estados canónicos.
3. Consolidar cierre/backlog con inmutabilidad de semanas cerradas.
4. Estabilizar contratos API y dividir `App.jsx` por features.
5. Añadir actoría, RLS y lockfiles antes de cambios de producción.
