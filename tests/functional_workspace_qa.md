# QA — espacio funcional

## Alcance y evidencia

Spec: `openspec/changes/functional-workspace/spec.md`. QA solo modifica `tests/**`.

Comando reproducible desde la raíz del repositorio en Windows:

```powershell
.venv/Scripts/python.exe -X utf8 -m pytest -q
```

Resultado integrado: **109 passed in 0.92s**, incluidos **26 casos nuevos** en
`tests/test_functional_workspace.py`. El modo UTF-8 es necesario porque pruebas
anteriores leen fuentes UTF-8 sin indicar encoding y Windows usa cp1252.

Los casos nuevos ejecutan las consultas SELECT reales sobre tablas SQLite
aisladas: filtros, joins, agregaciones, fronteras de antigüedad y deduplicación.
Se adaptan únicamente diferencias de dialecto (`ILIKE`, casts `::int`, resta
de fechas y agregación `bool_and`). Las escrituras PostgreSQL de conciliación
se capturan para verificar sus IDs y parámetros; nunca se ejecutan contra una
base externa. La prueba detectó que el resumen filtrado omitía el JOIN de activo
para filtros de área/búsqueda. Backend lo corrigió y quedó regresión reproducible.

Cobertura nueva:

- ANULADA histórica consultable y excluida de activos, incluido maestro anulado
  con backlog que todavía parece pendiente.
- Conciliación no finaliza/reactiva terminales ni operación aunque otro archivo
  los marque finalizados.
- Resumen global de historial separado del activo; resumen filtrado por estado,
  especialidad, área, búsqueda y antigüedad, incluyendo combinaciones y vacíos.
- H-H desconocidas contadas explícitamente, sin inventar horas.
- Cartera PMP/backlog sin doble conteo; repetición de seguimiento/cierre no
  duplica finalizaciones; observaciones de otro mes no finalizan el mes actual.
- Desglose de especialidad consistente con totales, especialidades vacías,
  desconocidas y denominadores cero.
- Indicadores gerenciales con período y alcance explícitos; exclusiones del mes,
  prioridad A y antigüedad actual del backlog.
- Fronteras 0/30/31/60/61/90/91 días y fecha futura: cada activo entra en un solo
  rango, con cero como mínimo.

## Baseline y tratamiento de fallos

Antes de integrar implementación y con UTF-8, excluyendo el archivo nuevo:
**75 passed, 8 failed**. Sin UTF-8 se sumaban errores de decodificación de Windows.
No se eliminaron ni marcaron xfail las pruebas que fallaban.

| Caso baseline | Clasificación y resolución |
|---|---|
| `test_advance_stops.py::test_plan_spacing_variation_matches_and_operation_is_excluded` | Producto: el espacio entre código y guion impedía resolver el plan. Backend corrigió normalización; se conserva prueba. |
| `test_operation_plan_exclusions.py::test_operation_prefix_accepts_missing_space_after_separator` | Producto/contrato de clasificación: OPERACIÓN sin espacio debe reconocerse aun cuando su familia tenga alias canónico. Backend corrigió; se conserva prueba. |
| `test_september_trial_contract.py::test_monthly_initial_import_is_non_destructive_and_guarded` | Assert genérico prohibía incluso refrescar exclusiones derivadas por período. Ahora permite únicamente las dos tablas de exclusiones con `WHERE periodo=:period`, mantiene prohibición de borrados adicionales/TRUNCATE y exige UPSERT de órdenes. |
| `test_technician_specialty_override.py::test_capacity_copy_explains_first_twenty_percent_as_operational_time` | UI: faltaba explicar los dos descuentos en la vista semanal. Frontend añadió ayuda; assertions originales conservadas. |
| `test_v2_backlog_contract.py::test_mechanical_week_is_valid_and_finalized_orders_are_excluded` | Contrato obsoleto: fuente finalizada no debe borrar demanda histórica de primera semana. Lead confirmó conservar universo semanal y descontar cierres anteriores confirmados. Ahora verifica período/semana anterior, estado CERRADA, finalizada/anulada y exclusión mediante `resolved_before_week`. Terminales backlog se prueban aparte. |
| `test_v2_progress_pdf.py::test_weekly_pdf_removed_explanatory_labels_and_bar` | Prueba dependía de una variable interna `kind` eliminada. Ahora genera PDF real y verifica ausencia de los mismos textos removidos, presencia de resultados, detalle y OT. |
| `test_visual_report_pagination.py::test_render_has_vector_graphs_and_branding` | Nombre esperado anterior no incluía especialidad ni fechas. Ahora exige nombre exacto con especialidad, corte e ID; mantiene branding, imágenes, gráficos y paginación. |
| `test_week_closure_matching.py::test_frontend_shares_week_label_and_previews_before_close` | Variable de iteración cambió de `w` a `item`. Mantiene comprobación de transición, número/etiqueta de semana y vista previa/confirmación. |

Además, el assert antiguo de backlog activo (`estado <> FINALIZADA`) se actualizó
a los dos estados pendientes, rechazando también maestro anulado/finalizado,
con cobertura relacional independiente de las cadenas SQL.

## Guards y límites

- `scripts/check_destructive_changes.py`: **sin patrones peligrosos**.
- `AGENT_ROLE=qa scripts/check_agent_ownership.py`: detecta cambios backend/frontend
  y spec de los otros agentes en el workspace compartido. Es esperado; el Lead
  debe ejecutar la verificación de integración. Los cambios de este agente
  permanecen en `tests/**`.
- No se ejecutó una cadena de migración PostgreSQL nueva: no hay instancia local
  efímera disponible y esta entrega no cambia esquema. SQLite no acredita locks,
  casts, índices ni todas las diferencias de tipos PostgreSQL.
- Las pruebas previas preservan importaciones no destructivas, complementos,
  límites de cierre y parsers. El ciclo completo import A → programar → cerrar →
  import B contra PostgreSQL nuevo todavía requiere un entorno de integración;
  las comprobaciones estáticas existentes no sustituyen ese recorrido.
- Validación visual desktop/móvil y lectura de producción a cargo del Lead;
  QA no abrió producción, hizo cargas/cierres, deploy ni commit.

Recomendación: integrar con checks verdes y completar revisión visual y lectura
del contrato PostgreSQL antes de publicar. No atribuir a estas pruebas una
validación transaccional completa de PostgreSQL.
