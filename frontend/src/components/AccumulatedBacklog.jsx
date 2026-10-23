import { useEffect, useState } from "react";
import { getV2Backlog } from "../api";
import Badge from "../shared/Badge";

function number(value) {
  const parsed = Number(value);
  return Number.isFinite(parsed) ? parsed : 0;
}
function fmt(value) {
  return number(value).toLocaleString("es-CO", {
    minimumFractionDigits: 1,
    maximumFractionDigits: 1,
  });
}
const MONTH_NAMES = [
  "ENERO","FEBRERO","MARZO","ABRIL","MAYO","JUNIO",
  "JULIO","AGOSTO","SEPTIEMBRE","OCTUBRE","NOVIEMBRE","DICIEMBRE",
];

function originMonth(row) {
  const raw = String(
    row.periodo_origen
      || row.primera_semana_origen_inicio
      || row.semana_origen_inicio
      || "",
  ).slice(0, 10);
  const match = raw.match(/^(\d{4})-(\d{2})/);
  if (!match) return "SIN PERÍODO";
  const year = Number(match[1]);
  const month = Number(match[2]);
  return `${MONTH_NAMES[month - 1] || "MES"} ${year}`;
}

function backlogReason(row) {
  const reason = String(row.motivo || "").toUpperCase();
  if (reason.includes("CONCILIACI") || reason.includes("RECONCILIACI") || reason.includes("EXCEL")) {
    return {label: "CONCILIACIÓN DE FUENTE", detail: "Incorporada al contrastar órdenes con el archivo de mantenimiento", tone: "backlog"};
  }
  if (reason.includes("ARRASTRE INICIAL")) {
    return {
      label: "BACKLOG INICIAL",
      detail: reason.includes("SEPTIEMBRE 2026")
        ? "Pendiente heredada del cierre de septiembre 2026"
        : "Pendiente heredada del cierre del mes anterior",
      tone: "backlog",
    };
  }
  if (reason.includes("RETIRADA DE PROGRAMACIÓN")) {
    return {
      label: "CAMBIO DE PROGRAMACIÓN",
      detail: "Retirada al modificar la programación asignada",
      tone: "backlog",
    };
  }
  if (reason.includes("NO ENCONTRADA")) {
    return {
      label: "NO ENCONTRADA EN CIERRE",
      detail: "La OT no apareció en el archivo usado para cerrar",
      tone: "warn",
    };
  }
  if (reason.includes("PENDIENTE DE CIERRE")) {
    return {
      label: "NO FINALIZADA",
      detail: "Programada, pero no terminó al cierre semanal",
      tone: "warn",
    };
  }
  return {
    label: "SEGUIMIENTO",
    detail: "Registro conservado en la cola de mantenimiento",
    tone: "backlog",
  };
}
function originText(row) {
  if (String(row.motivo || "").toUpperCase().includes("ARRASTRE INICIAL") && row.periodo_origen) {
    return `Cierre ${originMonth(row)}`;
  }
  return row.primera_semana_origen_inicio || row.semana_origen_inicio || "Sin fecha";
}

export default function AccumulatedBacklog({
  areas = [],
  initialOrderId,
  onClearOrder,
}) {
  const [filters, setFilters] = useState({
    state: "",
    area: "",
    specialty: "",
    search: "",
    age_min: "",
    age_max: "",
    order_id: initialOrderId || "",
  });
  const [data, setData] = useState({ rows: [], summary: {} });
  const [loading, setLoading] = useState(false);
  const [error, setError] = useState("");
  const [revision, setRevision] = useState(0);

  useEffect(() => {
    setFilters((current) => ({ ...current, order_id: initialOrderId || "" }));
  }, [initialOrderId]);

  useEffect(() => {
    let active = true;
    setLoading(true);
    setError("");
    getV2Backlog(filters)
      .then((result) => {
        if (active) setData(result);
      })
      .catch((cause) => {
        if (active) setError(cause.message);
      })
      .finally(() => {
        if (active) setLoading(false);
      });
    return () => {
      active = false;
    };
  }, [filters, revision]);

  const rows = data.rows || [];
  const summary = data.summary || {};
  const filtered = data.filtered_summary;
  function update(name, value) {
    setFilters((current) => ({ ...current, [name]: value }));
  }

  return (
    <div className="v2-stack v2-backlog-workspace">
      <section className="v2-backlog-indicators" aria-label="Indicadores de backlog">
        <div>
          <span>OT movidas a Backlog</span>
          <b>{number(summary.movidas)}</b>
          <small>histórico global · sin filtros</small>
        </div>
        <div className="september">
          <span>Arrastre inicial</span>
          <b>{number(summary.carga_inicial)}</b>
          <small>carga inicial conservada en historial</small>
        </div>
        <div className="finalized">
          <span>Finalizadas por ingeniero</span>
          <b>{number(summary.finalizadas_por_ingeniero)}</b>
          <small>confirmadas en cierre semanal</small>
        </div>
        <div className="pending">
          <span>Pendientes activas</span>
          <b>{number(summary.pendientes_activas)}</b>
          <small>requieren nueva programación o cierre</small>
        </div>
        <div className="hours">
          <span>H-H Backlog activo</span>
          <b>{fmt(summary.hh_backlog_activo)}</b>
          <small>
            solo OT activas de Backlog
            {number(summary.backlog_sin_hh) > 0 ? ` · ${number(summary.backlog_sin_hh)} sin H-H calculables` : ""}
          </small>
        </div>
      </section>

      <section className="v2-panel">
        <div className="v2-section-head">
          <div>
            <span className="v2-kicker">COLA OPERATIVA</span>
            <h3>{filters.state === "FINALIZADA" ? "Historial de finalizadas" : filters.state === "ANULADA" ? "Historial de anuladas" : "Órdenes pendientes"}</h3>
            <p>Acumulado de todos los períodos. Los contadores superiores son globales; la tabla aplica los filtros seleccionados.</p>
          </div>
          <Badge tone="backlog">{loading ? "Consultando..." : `${rows.length} visibles`}</Badge>
        </div>
        <div className="v2-toolbar v2-toolbar-6">
          <select aria-label="Estado de backlog" value={filters.state} onChange={(e) => update("state", e.target.value)}>
            <option value="">Pendientes activas</option>
            <option value="PENDIENTE_DISPONIBLE">Pendiente disponible</option>
            <option value="PENDIENTE_PROGRAMADA">Pendiente programada</option>
            <option value="FINALIZADA">Finalizadas</option>
            <option value="ANULADA">Anuladas · historial</option>
          </select>
          <select aria-label="Area de backlog" value={filters.area} onChange={(e) => update("area", e.target.value)}>
            <option value="">Todas las areas</option>
            {areas.map((a) => <option key={a.codigo} value={a.codigo}>{a.codigo} · {a.nombre || a.codigo}</option>)}
          </select>
          <select aria-label="Especialidad de backlog" value={filters.specialty} onChange={(e) => update("specialty", e.target.value)}>
            <option value="">Todas las especialidades</option>
            {["MEC", "ELE", "MET", "SER", "SOL"].map((s) => <option key={s} value={s}>{s}</option>)}
          </select>
          <input aria-label="Buscar en backlog" placeholder="Buscar OT, equipo o plan..." value={filters.search} onChange={(e) => update("search", e.target.value)} />
          <input type="number" min="0" aria-label="Antigüedad mínima en días" placeholder="Edad mín. (días)" value={filters.age_min} onChange={(e) => update("age_min", e.target.value)} />
          <input type="number" min="0" aria-label="Antigüedad máxima en días" placeholder="Edad máx. (días)" value={filters.age_max} onChange={(e) => update("age_max", e.target.value)} />
        </div>
        <div className="tf-backlog-filter-summary" aria-live="polite">
          <span><b>{loading ? "Consultando…" : rows.length}</b> órdenes visibles</span>
          {filtered && <><span><b>{number(filtered.pendientes_activas)}</b> pendientes activas con estos filtros</span><span><b>{fmt(filtered.hh_backlog_activo)}</b> H-H activas filtradas</span></>}
          <button type="button" onClick={() => {setFilters({state:"", area:"", specialty:"", search:"", age_min:"", age_max:"", order_id:""}); onClearOrder?.();}}>Limpiar filtros</button>
          <button type="button" disabled={loading} onClick={() => setRevision(value => value + 1)}>Actualizar</button>
        </div>
        {filters.order_id && (
          <div className="v2-filter-context">
            Mostrando la OT seleccionada desde Cierre{" "}
            <button type="button" onClick={() => { update("order_id", ""); onClearOrder?.(); }}>Ver toda la cola</button>
          </div>
        )}
        {error && <div className="v2-error" role="alert">{error}<button type="button" onClick={() => setRevision(value => value + 1)}>Reintentar</button></div>}
        <div className="v2-table-wrap" role="region" aria-label="Órdenes de backlog" tabIndex={0} aria-busy={loading}>
          <table>
            <thead>
              <tr>
                <th>Estado</th><th>Mes origen</th><th>Motivo de ingreso</th><th>OT</th><th>Area</th><th>Equipo</th><th>Plan</th><th>H-H</th><th>Origen</th><th>Antiguedad</th><th>Reprog.</th>
              </tr>
            </thead>
            <tbody>
              {rows.map((r) => {
                const reason = backlogReason(r);
                return (
                  <tr key={r.id}>
                    <td>
                      <Badge tone={r.estado_seguimiento === "ANULADA" ? "neutral" : r.estado_seguimiento === "PENDIENTE_PROGRAMADA" ? "warn" : r.estado_seguimiento === "FINALIZADA" ? "ok" : "backlog"}>
                        {String(r.estado_seguimiento || "SIN ESTADO").replaceAll("_", " ")}
                      </Badge>
                      <small>{r.ultimo_resultado_cierre || "Sin cierre registrado"}</small>
                    </td>
                    <td>
                      <div className={String(r.motivo || "").toUpperCase().includes("SEPTIEMBRE 2026") ? "v2-backlog-month september" : "v2-backlog-month"}>
                        <b>{originMonth(r)}</b>
                        {String(r.motivo || "").toUpperCase().includes("SEPTIEMBRE 2026") && <small>ARRASTRE INICIAL</small>}
                      </div>
                    </td>
                    <td><div className="v2-backlog-reason"><Badge tone={reason.tone}>{reason.label}</Badge><small>{reason.detail}</small></div></td>
                    <td><b>{r.numero_ot || "SIN ASIGNAR"}</b></td>
                    <td><Badge>{r.area_codigo || "—"}</Badge></td>
                    <td><b>{r.activo_codigo}</b><small>{r.activo_descripcion}</small></td>
                    <td><span className="v2-plan">{r.plan_trabajo || "—"}</span><small>{r.descripcion_grupo || ""}</small></td>
                    <td><b>{fmt(r.hh)}</b></td>
                    <td><small>{originText(r)}</small></td>
                    <td><b>{number(r.antiguedad_dias)}</b><small>dias</small></td>
                    <td><b>{number(r.reprogramaciones)}</b></td>
                  </tr>
                );
              })}
              {loading && <tr><td colSpan="11" className="v2-empty" role="status">Consultando órdenes…</td></tr>}
              {!rows.length && !loading && !error && <tr><td colSpan="11" className="v2-empty">No hay OT de Backlog con estos filtros.</td></tr>}
            </tbody>
          </table>
        </div>
      </section>
    </div>
  );
}
