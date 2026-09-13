# Invariantes de dominio

- **INV-001** Un import no elimina programación semanal ni cierres históricos.
- **INV-002** Los complementos manuales sobreviven reimportaciones.
- **INV-003** `FINALIZADA` y `FINALIZADO` se mapean a un concepto interno `FINALIZADO`.
- **INV-004** Una semana cerrada es inmutable salvo workflow explícito de reapertura.
- **INV-005** Una OT no está simultáneamente activa en backlog y programada en el mismo ciclo, salvo decisión de dominio explícita.
- **INV-006** HH tiene una fórmula canónica y una única autoridad.
- **INV-007** Capacidad se calcula en backend/dominio.
- **INV-008** Frontend presenta resultados; no inventa reglas de capacidad.
- **INV-009** Migraciones aplicadas son inmutables.
- **INV-010** Mutaciones deben tener actor y timestamp auditables.
- **INV-011** Cierre es resultado observado/reconciliado, distinto de la decisión de programación original.
- **INV-012** Cada import permite identificar el batch fuente que generó los datos actuales.

La fórmula exacta de la política “doble 80%” es una decisión pendiente, no una invariante aprobada.
