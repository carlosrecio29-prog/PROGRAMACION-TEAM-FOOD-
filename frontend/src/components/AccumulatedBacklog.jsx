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
function backlogReason(row) {
  const reason = String(row.motivo || "").toUpperCase();
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
  }, [filters]);
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
            cambios de programación de trabajos que el ingeniero no finalizó.
          </p>
        </div>
      </section>
      <section
        className="v2-backlog-indicators"
        aria-label="Indicadores de backlog"
      >
        <div>
          <span>OT movidas a Backlog</span>
          <b>{number(summary.movidas)}</b>
          <small>pendientes activas de seguimiento</small>
        </div>
        <div className="finalized">
          <span>Finalizadas por ingeniero</span>
          <b>{number(summary.finalizadas_por_ingeniero)}</b>
          <small>confirmadas en cierre semanal</small>
        </div>
        <div className="pending">
          <span>Pendientes activas</span>
          <b>{number(summary.pendientes_activas)}</b>
          <small>requieren nueva programacion o cierre</small>
        </div>
      </section>
      <section className="v2-panel">
        <div className="v2-section-head">
          <div>
            <span className="v2-kicker">COLA OPERATIVA</span>
            <h3>OT pendientes no finalizadas</h3>
            <p>Filtra la cola sin depender de una semana.</p>
          </div>
          <Badge tone="backlog">
            {loading ? "Consultando..." : `${rows.length} visibles`}
          </Badge>
        </div>
        <div className="v2-toolbar v2-toolbar-6">
          <select
            aria-label="Estado de backlog"
            value={filters.state}
            onChange={(e) => update("state", e.target.value)}
          >
            <option value="">Pendientes activas</option>
            <option value="PENDIENTE_DISPONIBLE">Pendiente disponible</option>
            <option value="PENDIENTE_PROGRAMADA">Pendiente programada</option>
            <option value="FINALIZADA">Finalizadas</option>
          </select>
          <select
            aria-label="Area de backlog"
            value={filters.area}
            onChange={(e) => update("area", e.target.value)}
          >
            <option value="">Todas las areas</option>
            {areas.map((a) => (
              <option key={a.codigo} value={a.codigo}>
                {a.codigo} · {a.nombre || a.codigo}
              </option>
            ))}
          </select>
          <select
            aria-label="Especialidad de backlog"
            value={filters.specialty}
            onChange={(e) => update("specialty", e.target.value)}
          >
            <option value="">Todas las especialidades</option>
            {["MEC", "ELE", "MET", "SER"].map((s) => (
              <option key={s} value={s}>
                {s}
              </option>
            ))}
          </select>
          <input
            aria-label="Buscar en backlog"
            placeholder="Buscar OT, equipo o plan..."
            value={filters.search}
            onChange={(e) => update("search", e.target.value)}
          />
          <input
            type="number"
            min="0"
            aria-label="Antigüedad mínima en días"
            placeholder="Edad mín. (días)"
            value={filters.age_min}
            onChange={(e) => update("age_min", e.target.value)}
          />
          <input
            type="number"
            min="0"
            aria-label="Antigüedad máxima en días"
            placeholder="Edad máx. (días)"
            value={filters.age_max}
            onChange={(e) => update("age_max", e.target.value)}
          />
        </div>
        {filters.order_id && (
          <div className="v2-filter-context">
            Mostrando la OT seleccionada desde Cierre{" "}
            <button
              type="button"
              onClick={() => {
                update("order_id", "");
                onClearOrder?.();
              }}
            >
              Ver toda la cola
            </button>
          </div>
        )}
        {error && <div className="v2-error">{error}</div>}
        <div className="v2-table-wrap">
          <table>
            <thead>
              <tr>
                <th>Estado</th>
                <th>Motivo de ingreso</th>
                <th>OT</th>
                <th>Area</th>
                <th>Equipo</th>
                <th>Plan</th>
                <th>H-H</th>
                <th>Semana origen</th>
                <th>Antiguedad</th>
                <th>Reprog.</th>
              </tr>
            </thead>
            <tbody>
              {rows.map((r) => {
                const reason = backlogReason(r);
                return (
                  <tr key={r.id}>
                    <td>
                      <Badge
                        tone={
                          r.estado_seguimiento === "PENDIENTE_PROGRAMADA"
                            ? "warn"
                            : r.estado_seguimiento === "FINALIZADA"
                              ? "ok"
                              : "backlog"
                        }
                      >
                        {r.estado_seguimiento.replaceAll("_", " ")}
                      </Badge>
                      <small>{r.ultimo_resultado_cierre || "PENDIENTE"}</small>
                    </td>
                    <td>
                      <div className="v2-backlog-reason">
                        <Badge tone={reason.tone}>{reason.label}</Badge>
                        <small>{reason.detail}</small>
                      </div>
                    </td>
                    <td><b>{r.numero_ot || "SIN ASIGNAR"}</b></td>
                    <td><Badge>{r.area_codigo || "—"}</Badge></td>
                    <td>
                      <b>{r.activo_codigo}</b>
                      <small>{r.activo_descripcion}</small>
                    </td>
                    <td>
                      <span className="v2-plan">{r.plan_trabajo || "—"}</span>
                      <small>{r.descripcion_grupo || ""}</small>
                    </td>
                    <td><b>{fmt(r.hh)}</b></td>
                    <td>
                      <small>
                        {r.primera_semana_origen_inicio ||
                          r.semana_origen_inicio ||
                          "Sin fecha"}
                      </small>
                    </td>
                    <td>
                      <b>{number(r.antiguedad_dias)}</b>
                      <small>dias</small>
                    </td>
                    <td><b>{number(r.reprogramaciones)}</b></td>
                  </tr>
                );
              })}
              {!rows.length && !loading && (
                <tr>
                  <td colSpan="10" className="v2-empty">
                    No hay OT de Backlog con estos filtros.
                  </td>
                </tr>
              )}
            </tbody>
          </table>
        </div>
      </section>
    </div>
  );
}
