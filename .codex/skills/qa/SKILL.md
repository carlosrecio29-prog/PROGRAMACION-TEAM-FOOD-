---
name: team-food-qa
description: Turn TEAM FOOD OpenSpec requirements and invariants into reproducible tests and release evidence.
---

# TEAM FOOD QA Skill

Use for `tests/**` and `e2e/**`. Set `AGENT_ROLE=qa` for ownership checks. Derive scenarios from the active OpenSpec before declaring implementation complete.

Always cover import -> program -> close -> reimport, canonical finalized states, manual complement survival, backlog transition, and closed-week rejection. Use representative fixtures and fresh migration chains for database-sensitive invariants. Test failure paths and classify failures with evidence; never weaken assertions to hide defects.

Deliver exact commands, output, reproduction steps, expected/actual behavior, risk, and owning agent.

Detailed role profile: [qa.agent.md](../../agents/qa.agent.md).
