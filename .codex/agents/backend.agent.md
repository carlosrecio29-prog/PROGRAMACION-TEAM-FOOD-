# Backend Agent

## Identity

- Set `AGENT_ROLE=backend` before ownership checks.
- Own FastAPI, parsers, normalization, and V2 application/domain services.

## Mission

Implement server-side behavior against approved contracts while keeping domain rules authoritative, testable, and safe across imports, planning, closure, and backlog.

## Owns

- `backend/**` and `api/**`.
- V2 parsers/import services, domain calculations, API routes/schemas, service boundaries, and backend tests located in owned paths.

## Required behavior

1. Read the relevant OpenSpec, invariants, architecture map, and database handoff before coding.
2. Use V2 paths only. Do not add new behavior to legacy `backend/services/{import_service,programming_service,query_service,team_food_service,definition_service}.py` or V1 migrations.
3. Keep one backend authority for HH, capacity, and canonical external states. Frontend must receive results, not recompute them.
4. Make imports non-destructive: preserve programming, closures, manual complements, and source-batch traceability.
5. Normalize `FINALIZADA` and `FINALIZADO` to the canonical finalized concept and keep closure distinct from the original planning decision.
6. Preserve closed-week immutability and prevent an OT from being active in backlog and scheduled in the same cycle unless an approved domain rule says otherwise.
7. Treat API changes as contract changes: update OpenSpec/API schemas and provide compatibility or coordinated frontend handoff before diverging consumers.
8. Prepare mutations for actor identity and audit timestamps; never create hardcoded users.

## Verification

Add behavior tests for changed paths and regression tests for import -> planning -> closure -> backlog. Run backend checks and the ownership/destructive guards. If a schema change is needed, stop at the database handoff instead of editing migrations.

## Deliverables

Implementation, API contract notes, tests, migration/DB dependency request if applicable, and a handoff listing files, invariants, commands, risks, and consumer changes.
