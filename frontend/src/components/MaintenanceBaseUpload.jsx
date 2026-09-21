import { useState } from "react";

function readError(payload, status) {
  if (payload?.detail) return payload.detail;
  return `No se pudo actualizar la base (HTTP ${status})`;
}

export default function MaintenanceBaseUpload({ year, month }) {
  const [operationMaster, setOperationMaster] = useState(null);
  const [monthlyOnly, setMonthlyOnly] = useState(null);
  const [operationResult, setOperationResult] = useState(null);
  const [monthlyResult, setMonthlyResult] = useState(null);
  const [plans, setPlans] = useState(null);
  const [activities, setActivities] = useState(null);
  const [monthly, setMonthly] = useState(null);
  const [busy, setBusy] = useState(false);
  const [error, setError] = useState("");
  const [result, setResult] = useState(null);

  async function postOperationMaster() {
    if (!operationMaster) return setError("Selecciona el Excel Plan de Trabajo.");
    setBusy(true); setError(""); setOperationResult(null);
    try {
      const form = new FormData();
      form.append("plans", operationMaster);
      const response = await fetch("/api/v2/import-operation-master", {
        method: "POST", body: form,
      });
      const payload = await response.json();
      if (!response.ok) throw new Error(readError(payload, response.status));
      setOperationResult(payload);
    } catch (e) { setError(e.message); }
    finally { setBusy(false); }
  }

  async function postMonthlyOnly() {
    if (!monthlyOnly) return setError("Selecciona la Lista de Calendario del mes.");
    setBusy(true); setError(""); setMonthlyResult(null);
    try {
      const form = new FormData();
      form.append("monthly", monthlyOnly);
      const params = new URLSearchParams({ year, month });
      const response = await fetch(`/api/v2/import-monthly-calendar?${params}`, {
        method: "POST", body: form,
      });
      const payload = await response.json();
      if (!response.ok) throw new Error(readError(payload, response.status));
      setMonthlyResult(payload);
    } catch (e) { setError(e.message); }
    finally { setBusy(false); }
  }

  async function upload() {
    if (!plans || !activities || !monthly) {
      setError("Selecciona los tres Excel antes de actualizar la base.");
      return;
    }
    setBusy(true);
    setError("");
    setResult(null);
    try {
      const form = new FormData();
      form.append("plans", plans);
      form.append("activities", activities);
      form.append("monthly", monthly);
      const params = new URLSearchParams({ year, month });
      const response = await fetch(`/api/v2/import-maintenance?${params}`, {
        method: "POST",
        body: form,
      });
      let payload = null;
      try {
        payload = await response.json();
      } catch {
        payload = null;
      }
      if (!response.ok) throw new Error(readError(payload, response.status));
      setResult(payload);
    } catch (e) {
      setError(e.message || "Error actualizando la base de mantenimiento");
    } finally {
      setBusy(false);
    }
  }

  return (
    <details className="v2-panel" style={{ marginBottom: 18 }} open>
      <summary style={{ cursor: "pointer", listStyle: "none" }}>
        <div className="v2-section-head" style={{ marginBottom: 0 }}>
          <div>
            <span className="v2-kicker">ACTUALIZAR BASE DE MANTENIMIENTO</span>
            <h3 style={{ marginBottom: 4 }}>Cargar los 3 Excel del software</h3>
            <p style={{ margin: 0 }}>
              Plan de Trabajo + Actividades + Lista de Calendario / PMP.
            </p>
          </div>
          <span className="v2-primary" style={{ pointerEvents: "none" }}>
            Cargador de archivos
          </span>
        </div>
      </summary>

      <div className="v2-panel" style={{ marginTop: 18 }}>
        <span className="v2-kicker">ETAPA 1 · MAESTRO</span>
        <h3>Clasificar planes de OPERACIÓN</h3>
        <p>Sube solo Plan de Trabajo. Los planes cuyo nombre empieza con OPERACIÓN se excluyen de mantenimiento. No se borran OT ni semanas históricas.</p>
        <input type="file" accept=".xlsx" onChange={(e) => setOperationMaster(e.target.files?.[0] || null)} />
        <div className="v2-program-review-actions" style={{ marginTop: 12 }}>
          <button type="button" className="v2-primary" onClick={postOperationMaster} disabled={busy}>Actualizar maestro y exclusiones</button>
        </div>
        {operationResult && <div className="v2-success" style={{ marginTop: 12 }}>
          <b>{operationResult.planes_archivo} planes analizados · {operationResult.planes_operacion_archivo} de OPERACIÓN · {operationResult.planes_mantenimiento_archivo} restantes.</b>
          <details style={{ marginTop: 8 }}><summary>Ver los {operationResult.planes_operacion_archivo} planes excluidos</summary>
            <ul>{(operationResult.excluidos_detalle || []).map((x, i) => <li key={i}>{x.grupo} · {x.plan_trabajo} ({x.especialidad})</li>)}</ul>
          </details>
        </div>}
      </div>

      <div className="v2-panel" style={{ marginTop: 18 }}>
        <span className="v2-kicker">ETAPA 2 · MENSUAL</span>
        <h3>Cargar Lista de Calendario</h3>
        <p>Usa el maestro guardado. Las órdenes de OPERACIÓN no entran al PMP de mantenimiento. La reimportación actualiza OT existentes sin borrar programación ni cierres.</p>
        <input type="file" accept=".xlsx" onChange={(e) => setMonthlyOnly(e.target.files?.[0] || null)} />
        <div className="v2-program-review-actions" style={{ marginTop: 12 }}>
          <button type="button" className="v2-primary" onClick={postMonthlyOnly} disabled={busy}>Importar calendario {String(month).padStart(2, "0")}/{year}</button>
        </div>
        {monthlyResult && <div className="v2-success" style={{ marginTop: 12 }}>
          <b>{monthlyResult.pmp_archivo} registros del archivo · {monthlyResult.pmp_excluidos_operacion} excluidos por OPERACIÓN · {monthlyResult.pmp_importados_o_actualizados} importados/actualizados.</b>
          <p>{monthlyResult.registros_mantenimiento_periodo} registros de mantenimiento vigentes en base. {monthlyResult.registros_operacion_historicos} de OPERACIÓN conservados solo como historia.</p>
          {monthlyResult.warnings?.length > 0 && <details><summary>Advertencias ({monthlyResult.warnings.length})</summary><ul>{monthlyResult.warnings.map((x,i)=><li key={i}>{x}</li>)}</ul></details>}
          <button type="button" onClick={() => window.location.reload()}>Actualizar indicadores</button>
        </div>}
      </div>
      <details style={{ marginTop: 18 }}><summary>Carga inicial de los tres Excel (opcional)</summary>
      <div className="v2-quality-grid" style={{ marginTop: 18 }}>
        <label>
          <b>1. Plan de Trabajo</b>
          <small>Maestro de planes, personas, tiempos y condición de parada.</small>
          <input
            type="file"
            accept=".xlsx"
            onChange={(e) => setPlans(e.target.files?.[0] || null)}
          />
        </label>
        <label>
          <b>2. Plan de Trabajo - Actividades</b>
          <small>Pasos o actividades internas de cada plan.</small>
          <input
            type="file"
            accept=".xlsx"
            onChange={(e) => setActivities(e.target.files?.[0] || null)}
          />
        </label>
        <label>
          <b>3. Lista de Calendario / PMP</b>
          <small>Órdenes del período que aparecerán en PMP DEL MES.</small>
          <input
            type="file"
            accept=".xlsx"
            onChange={(e) => setMonthly(e.target.files?.[0] || null)}
          />
        </label>
      </div>

      <div className="v2-program-review-actions" style={{ marginTop: 18 }}>
        <button
          type="button"
          className="v2-primary"
          onClick={upload}
          disabled={busy}
        >
          {busy ? "Actualizando base..." : "Actualizar datos"}
        </button>
        <small>
          Período seleccionado: {String(month).padStart(2, "0")}/{year}. No se
          modifican activos ni técnicos.
        </small>
      </div>

      {error && <div className="v2-error" style={{ marginTop: 14 }}>{error}</div>}
      {result && (
        <div className="v2-success" style={{ marginTop: 14 }}>
          Base actualizada: {result.planes} planes · {result.actividades} actividades · {result.pmp_excluidos_operacion} registros excluidos por OPERACIÓN · {result.registros_pmp} registros PMP · {result.pmp_mecanica} registros MEC.
        </div>
      )}
      </details>
    </details>
  );
}
