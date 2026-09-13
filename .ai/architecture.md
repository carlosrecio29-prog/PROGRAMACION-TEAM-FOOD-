# Mapa de arquitectura y salud actual

## Current architecture

El producto es React/Vite (`frontend/src`) servido junto a FastAPI (`api/index.py`) en Vercel, con PostgreSQL/Supabase y migraciones SQL versionadas. Excel entra por parsers en `backend/parsers`; los servicios V2 persisten y consultan el modelo `programacion`.

## Active runtime

Las rutas V2 de `api/index.py` llaman principalmente a `v2_import_service.py`, `v2_programming_service.py`/`v2_programming_runtime.py` y `v2_closure_service.py`/`v2_close_service.py`. La UI principal está en `frontend/src/App.jsx` y consume `frontend/src/api.js`.

## Legacy paths

V1 incluye los servicios sin prefijo `v2_` en `backend/services/` y `supabase/migrations/`. Se conservan para contexto/compatibilidad, pero no son destino de trabajo nuevo.

## Data flow

Sistema externo → XLSX → parser/normalización → importación V2 → activos, planes, PMP, OT, técnicos y turnos → capacidad → programación semanal → Excel/PDF → exportación externa → cierre/reconciliación → backlog.

## Current technical risks

- `backend/services/v2_import_service.py` contiene `TRUNCATE ... RESTART IDENTITY CASCADE`; puede destruir datos históricos y debe ser reemplazado bajo una especificación aprobada.
- La lógica de programación/capacidad está duplicada entre `v2_programming_service.py` y `v2_programming_runtime.py`.
- El cierre está dividido entre `v2_closure_service.py` y `v2_close_service.py`, con varias migraciones de cierre/backlog.
- La UI concentra navegación y bastante lógica en `App.jsx`; debe modularizarse por feature gradualmente.
- `package.json` no tiene lockfile; la instalación no es reproducible aún.
- No se observa autenticación/actoría completa en las mutaciones actuales.
- Las migraciones V2 más recientes usan varias columnas de origen/cierre que requieren consolidación de modelo.

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
