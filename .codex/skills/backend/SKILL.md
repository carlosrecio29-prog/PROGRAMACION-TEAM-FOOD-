---
name: team-food-backend
description: Implement TEAM FOOD FastAPI, parsers, normalization, V2 domain services, and API behavior.
---

# TEAM FOOD Backend Skill

Use for `backend/**` and `api/**`. Set `AGENT_ROLE=backend` for ownership checks. Read the relevant OpenSpec, invariants, architecture, and database handoff first.

Use V2 paths only; do not add new behavior to legacy services. Keep one backend authority for HH, capacity, and canonical states. Imports must preserve programming, closures, manual complements, and source batches. Treat API changes as contract changes and prepare mutations for actor/timestamp auditability.

Add behavior and lifecycle regression tests. If schema work is needed, stop and hand off to Database instead of editing migrations.

Detailed role profile: [backend.agent.md](../../agents/backend.agent.md).
