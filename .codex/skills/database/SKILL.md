---
name: team-food-database
description: Design and safely migrate TEAM FOOD PostgreSQL/Supabase schema, constraints, indexes, RLS, and history.
---

# TEAM FOOD Database Skill

Use for schema, migration, constraint, index, RLS, seed, and database-test work. Set `AGENT_ROLE=database` for ownership checks.

Read the relevant OpenSpec and invariants first. Add new migrations only; never edit applied migrations or create V1 migrations. Preserve programming, closures, manual complements, and source-batch identity across imports. Model canonical states, closed-week immutability, and auditability explicitly.

Reject unapproved `TRUNCATE`, `DROP`, broad `DELETE`, `CASCADE`, or replacement imports. Test a fresh migration chain with representative reimport, closure, backlog, duplicate, and constraint cases. Escalate unresolved domain/API decisions to Lead.

Detailed role profile: [database.agent.md](../../agents/database.agent.md).
