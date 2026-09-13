# ADR-001: Fuente de verdad

Status: Accepted

## Decision
El sistema externo es fuente de verdad de datos operativos importados. TEAM FOOD es fuente de verdad de complementos, decisiones de programación, backlog, cierres y auditoría de esas decisiones.

## Consequences
Los imports actualizan datos fuente sin borrar historia app-owned. Cada batch debe ser identificable.
