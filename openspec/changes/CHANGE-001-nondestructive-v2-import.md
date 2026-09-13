# Change

ID: CHANGE-001-nondestructive-v2-import
Status: Proposed
Owner: Lead / Database / Backend / QA

## Problem

The V2 importer currently resets source tables with broad destructive SQL. That can invalidate stable surrogate IDs and cascade into TEAM FOOD programming, backlog and closure records.

## Current behavior

`backend/services/v2_import_service.py` parses a workbook and, inside a transaction, truncates V2 source tables before inserting the new snapshot. The exact dependency impact is being verified in this change; no missing source row will be treated as permission to delete historical data.

## Desired behavior

Each valid source entity is reconciled by a stable business key in one transaction. Existing source rows are updated, new rows inserted, and absent rows retained or safely retired without deleting TEAM FOOD-owned history or complements. Repeating a snapshot is idempotent.

## Non-goals

No capacity redesign, closure-service consolidation, authentication implementation, V1 rewrite, frontend rewrite or double-80% decision.

## Domain rules

Source-owned fields may change on re-import. App-owned complements and historical decisions must not be overwritten or deleted by source reconciliation. Failed imports roll back.

## Affected invariants

INV-001, INV-002, INV-009, INV-010, INV-011, INV-012.

## Data ownership and identity

Source-owned V2 tables are `programacion.activo`, `plan_trabajo`, `planeacion`, `orden_mantenimiento`, `tecnico`, `turno` and `programacion_tecnico`. TEAM FOOD-owned tables include `programacion_semanal_v2`, `programacion_item_v2`, `backlog_v2`, `cierre_semanal_v2` and closure items. Plan complements are `numero_personas_app` and `tiempo_parada_app` (plus existing complement fields). Current stable keys are: asset `codigo`; plan `(especialidad, nombre_canonico)` where available; technician `nombre_normalizado`/external code; shift `codigo`; planning row `source_key`; order `numero_orden` plus its planning context. These keys must be verified against constraints before migration.

## Identity note

V2 unique keys verified in the schema are asset `codigo`, plan `(grupo,plan_trabajo)`, technician `nombre_normalizado`, daily schedule `(tecnico_id,fecha)` and planning `id_cronograma_planeacion`. Orders use `periodo + numero_ot` when present; unassigned rows use period plus asset/plan/planning context and occurrence. Surrogate IDs remain stable because rows are upserted rather than recreated.

## API contract

Keep the existing import response shape; improve summary diagnostics only additively. Do not introduce fake actor identity.

## Migration strategy

Prefer a new additive V2 migration only if existing uniqueness/index constraints are insufficient. Never edit applied migrations. Validate fresh and existing-data paths.

## Acceptance scenarios

Given an import containing OT-001 and a weekly programming, when a later import runs, then the programming and item remain valid.

Given a closed week and closure items, when a later import runs, then both remain.

Given an unresolved OT in backlog, when a later import runs, then its backlog relationship remains.

Given a plan complement, when the same plan is imported again, then the complement is unchanged.

Given changed source fields and new records, when imported, then changed fields update and new rows appear without duplicating repeated imports.

## Verification

Dedicated import reconciliation tests; existing backend tests; migration checks; destructive guard; full `bash scripts/verify.sh`.

## Rollback / recovery

Application rollback is the previous service version; database changes, if any, are additive. No destructive fallback is permitted. Existing data must be backed up and representative existing-data verification documented before production rollout.
