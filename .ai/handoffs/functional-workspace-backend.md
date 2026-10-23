# Backend — functional workspace

Rol backend. Cartera centralizada en v2_portfolio_service; dashboard aprobado conservado y campos aditivos. ANULADA terminal en backlog, conciliación y elegibilidad de programación; filas históricas conservadas. Antigüedad/fecha gerencial usan America/Bogota. Sin cambios de capacidad, importación integral, cierres ni esquema.

Contrato: tracking_progress.pending_workload_hh, portfolio_progress_by_specialty en dashboard/progreso, management_insights, backlog.filtered_summary. Conteo por actividad orden_mantenimiento.id; fuentes programada/no programada pueden solaparse y no se suman.

Regresión local completa de integración: 113 pruebas pasan. SQL PostgreSQL de cartera validado solo lectura: 1020 actividades/517 finalizadas, 27 sin fecha, 1 sin H-H, 531 excluidas. El QA funcional usa SQLite aislado/adaptaciones de dialecto; no se aplican migraciones ni se prueba escritura contra producción.
