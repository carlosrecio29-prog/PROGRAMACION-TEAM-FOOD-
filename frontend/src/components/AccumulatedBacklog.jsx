import { useEffect, useState } from "react";
import { bootstrapV2Backlog, getV2Backlog } from "../api";
import Badge from "../shared/Badge";

const MONTHS = [
  "Enero","Febrero","Marzo","Abril","Mayo","Junio",
  "Julio","Agosto","Septiembre","Octubre","Noviembre","Diciembre",
];

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
function previousPeriod(year, month) {
  return month === 1 ? { year: year - 1, month: 12 } : { year, month: month - 1 };
}
function backlogReason(row) {
  const reason = String(row.motivo || "").toUpperCase();
  if (reason.includes("ARRASTRE INICIAL")) {
    return {
      label: "BACKLOG INICIAL",
      detail: "Pendiente heredada del cierre del mes anterior al inicio del piloto",
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
    label: reason || "PENDIENTE",
    detail: "Pendiente de seguimiento",
    tone: "backlog",
  };
}
function originText(row) {
  if (String(row.motivo || "").toUpperCase().includes("ARRASTRE INICIAL") && row.periodo_origen) {
    const [year, month] = String(row.periodo_origen).slice(0, 7).split("-").map(Number);
    return `Cierre ${MONTHS[(month || 1) - 1]} ${year}`;
  }
  return row.primera_semana_origen_inicio || row.semana_origen_inicio || "Sin fecha";
}

export default function AccumulatedBacklog({
  areas = [],
  initialOrderId,
  onClearOrder,
  year = 2026,
  month = 10,
}) {
  const initialPeriod = previousPeriod(year, month);
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
  const [bootstrapFile, setBootstrapFile] = useState(null);
  const [bootstrapYear, setBootstrapYear] = useState(initialPeriod.year);
  const [bootstrapMonth, setBootstrapMonth] = useState(initialPeriod.month);
  const [bootstrapBusy, setBootstrapBusy] = useState(false);
  const [bootstrapResult, setBootstrapResult] = useState(null);

  useEffect(() => {
    setFilters((current) => ({ ...current, order_id: initialOrderId || "" }));
  }, [initialOrderId]);
  useEffect(() => {
    const previous = previousPeriod(year, month);
    setBootstrapYear(previous.year);
    setBootstrapMonth(previous.month);
  }, [year, month]);

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

  async function loadInitialBacklog() {
    if (!bootstrapFile) {
      setError("Selecciona la Lista de Calendario definitiva del mes que vas a arrastrar.");
      return;
    }
    try {
      setBootstrapBusy(true);
      setError("");
      setBootstrapResult(null);
      const result = await bootstrapV2Backlog(bootstrapFile, bootstrapYear, bootstrapMonth);
      setBootstrapResult(result);
      setBootstrapFile(null);
      setRevision((value) => value + 1);
    } catch (cause) {
      setError(cause.message || "No se pudo construir el backlog inicial.");
    } finally {
      setBootstrapBusy(false);
    }
  }

  const rows = data.rows || [];
  const summary = data.summary || {};
  function update(name, value) {
    setFilters((current) => ({ ...current, [name]: value }));
  }

  return (
    <div className="v2-stack v2-backlog-workspace">
      <section className="v2-hero v2-backlog-hero">
        <div>
          <span className="v2-kicker">SEGUIMIENTO ACUMULADO</span>
          <h2>Backlog activo hasta finalizar</h2>
          <p>
            Cada OT conserva el motivo por el que entró al backlog para separar
            el arrastre inicial, los cambios de programación y los pendientes de cierres semanales.
          </p>
        </div>
      </section>

      <section className="v2-panel v2-backlog-bootstrap">
        <div className="v2-section-head">
          <div>
            <span className="v2-kicker">ARRANQUE DEL PILOTO</span>
            <h3>Cargar pendientes del cierre mensual anterior</h3>
            <p>
              Usa esta carga para iniciar el Backlog con las OT que quedaron abiertas en septiembre.
              Después de esto, los cierres semanales alimentarán la misma cola automáticamente.
            </p>
          </div>
          <Badge tone="backlog">{number(summary.carga_inicial)} del arrastre inicial</Badge>
        </div>
        <div className="v2-backlog-bootstrap-controls">
          <label>
            <span>Año</span>
            <input type="number" min="2020" max="2100" value={bootstrapYear} onChange={(e) => setBootstrapYear(Number(e.target.value))} />
          </label>
          <label>
            <span>Mes</span>
            <select value={bootstrapMonth} onChange={(e) => setBootstrapMonth(Number(e.target.value))}>
              {MONTHS.map((name, index) => <option key={name} value={index + 1}>{name}</option>)}
            </select>
          </label>
          <label className="file">
            <span>Lista de Calendario definitiva</span>
            <input type="file" accept=".xlsx" onChange={(e) => setBootstrapFile(e.target.files?.[0] || null)} />
          </label>
          <button type="button" className="v2-primary" disabled={!bootstrapFile || bootstrapBusy} onClick={loadInitialBacklog}>
            {bootstrapBusy ? "Analizando..." : "Cargar pendientes al Backlog"}
          </button>
        </div>
        <div className="v2-backlog-bootstrap-note">
          Esta operación no crea una programación semanal. Importa el período histórico y lleva al Backlog únicamente las OT que no estén finalizadas.
        </div>
        {bootstrapResult && (
          <div className="v2-backlog-bootstrap-result">
            <b>{bootstrapResult.backlog_inicial_activo} OT pendientes cargadas</b>
            <span>{bootstrapResult.importacion?.pmp_finalizados_archivo || 0} finalizadas detectadas en el archivo · {bootstrapResult.importacion?.pmp_excluidos_operacion || 0} registros OPERACIÓN excluidos.</span>
            {!!bootstrapResult.por_especialidad?.length && (
              <small>{bootstrapResult.por_especialidad.map((row) => `${row.especialidad}: ${row.cantidad}`).join(" · ")}</small>
            )}
          </div>
        )}
      </section>

      <section className="v2-backlog-indicators" aria-label="Indicadores de backlog">
        <div>
          <span>OT movidas a Backlog</span>
          <b>{number(summary.movidas)}</b>
          <small>histórico total de la cola</small>
        </div>
        <div className="initial">
          <span>Arrastre inicial</span>
          <b>{number(summary.carga_inicial)}</b>
          <small>pendientes heredadas del cierre mensual</small>
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
      </section>

      <section className="v2-panel">
        <div className="v2-section-head">
          <div>
            <span className="v2-kicker">COLA OPERATIVA</span>
            <h3>OT pendientes no finalizadas</h3>
            <p>Filtra la cola sin depender de una semana.</p>
          </div>
          <Badge tone="backlog">{loading ? "Consultando..." : `${rows.length} visibles`}</Badge>
        </div>
        <div className="v2-toolbar v2-toolbar-6">
          <select aria-label="Estado de backlog" value={filters.state} onChange={(e) => update("state", e.target.value)}>
            <option value="">Pendientes activas</option>
            <option value="PENDIENTE_DISPONIBLE">Pendiente disponible</option>
            <option value="PENDIENTE_PROGRAMADA">Pendiente programada</option>
            <option value="FINALIZADA">Finalizadas</option>
          </select>
          <select aria-label="Area de backlog" value={filters.area} onChange={(e) => update("area", e.target.value)}>
            <option value="">Todas las areas</option>
            {areas.map((a) => <option key={a.codigo} value={a.codigo}>{a.codigo} · {a.nombre || a.codigo}</option>)}
          </select>
          <select aria-label="Especialidad de backlog" value={filters.specialty} onChange={(e) => update("specialty", e.target.value)}>
            <option value="">Todas las especialidades</option>
            {["MEC", "ELE", "MET", "SER"].map((s) => <option key={s} value={s}>{s}</option>)}
          </select>
          <input aria-label="Buscar en backlog" placeholder="Buscar OT, equipo o plan..." value={filters.search} onChange={(e) => update("search", e.target.value)} />
          <input type="number" min="0" aria-label="Antigüedad mínima en días" placeholder="Edad mín. (días)" value={filters.age_min} onChange={(e) => update("age_min", e.target.value)} />
          <input type="number" min="0" aria-label="Antigüedad máxima en días" placeholder="Edad máx. (días)" value={filters.age_max} onChange={(e) => update("age_max", e.target.value)} />
        </div>
        {filters.order_id && (
          <div className="v2-filter-context">
            Mostrando la OT seleccionada desde Cierre{" "}
            <button type="button" onClick={() => { update("order_id", ""); onClearOrder?.(); }}>Ver toda la cola</button>
          </div>
        )}
        {error && <div className="v2-error">{error}</div>}
        <div className="v2-table-wrap">
          <table>
            <thead>
              <tr>
                <th>Estado</th><th>Motivo de ingreso</th><th>OT</th><th>Area</th><th>Equipo</th><th>Plan</th><th>H-H</th><th>Origen</th><th>Antiguedad</th><th>Reprog.</th>
              </tr>
            </thead>
            <tbody>
              {rows.map((r) => {
                const reason = backlogReason(r);
                return (
                  <tr key={r.id}>
                    <td>
                      <Badge tone={r.estado_seguimiento === "PENDIENTE_PROGRAMADA" ? "warn" : r.estado_seguimiento === "FINALIZADA" ? "ok" : "backlog"}>
                        {r.estado_seguimiento.replaceAll("_", " ")}
                      </Badge>
                      <small>{r.ultimo_resultado_cierre || "PENDIENTE"}</small>
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
              {!rows.length && !loading && <tr><td colSpan="10" className="v2-empty">No hay OT de Backlog con estos filtros.</td></tr>}
            </tbody>
          </table>
        </div>
      </section>
    </div>
  );
}
