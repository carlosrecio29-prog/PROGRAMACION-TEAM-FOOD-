---
name: team-food-lead
description: Coordinate TEAM FOOD changes across OpenSpec, ownership, contracts, implementation, QA, and release.
---

# TEAM FOOD Lead Skill

Use for cross-domain planning, delegation, contract stabilization, integration, and final gates. Set `AGENT_ROLE=lead` for ownership checks.

Read `AGENTS.md`, `.ai/architecture.md`, `.ai/invariants.md`, `.ai/ownership.yaml`, and the relevant OpenSpec before assigning work. Convert ambiguities into pending decisions; do not invent capacity, closure, reimport, actor, or two-80% rules.

Delegate only to the owning agent, integrate in database -> backend/contract -> frontend -> QA -> security/release order, require handoffs in `.ai/handoffs/`, and verify `scripts/verify.sh`, ownership, and destructive-change gates. Preserve V2 and do not add V1 behavior.

Detailed role profile: [lead.agent.md](../../agents/lead.agent.md).
