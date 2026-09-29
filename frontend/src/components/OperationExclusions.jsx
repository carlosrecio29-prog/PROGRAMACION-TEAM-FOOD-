import { useEffect, useMemo, useState } from "react";
import { getOperationExclusions } from "../api";
import Badge from "../shared/Badge";

const SPEC_NAMES = {
  MEC: "Mecánica",
  ELE: "Eléctrica",
  MET: "Metrología",
  SER: "Servicios",
};

function normalize(value) {
  return String(value || "").normalize("NFD").replace(/[\u0300-\u036f]/g, "").toUpperCase();
}

export default function OperationExclusions({ year, month }) {
  const [data, setData] = useState(null);
  const [specialty, setSpecialty] = useState("");
  const [search, setSearch] = useState("");
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState("");

  async function load() {
    try {
      setLoading(true);
      setError("");
      setData(await getOperationExclusions(year, month));
    } catch (cause) {
      setError(cause.message || "No se pudieron consultar las actividades excluidas.");
    } finally {
      setLoading(false);
    }
  }

  useEffect(() => {
    load();
  }, [year, month]);

  const query = normalize(search);
  const catalog = useMemo(
    () => (data?.catalog || []).filter((row) => {
      if (specialty && row.especialidad !== specialty) return false;
      if (!query) return true;
      return normalize([
        row.grupo,
        row.plan_trabajo,
        row.descripcion_plan_trabajo,
        row.especialidad,
      ].join(" ")).includes(query);
    }),
    [data, specialty, query],
  );

  const periodRows = useMemo(
    () => (data?.period_exclusions || []).filter((row) => {
      if (specialty && row.especialidad !== specialty) return false;
      if (!query) return true;
      return normalize([
        row.grupo,
        row.plan_clave_software,
        row.plan_maestro,
        row.descripcion_maestro,
        row.especialidad,
      ].join(" ")).includes(query);
    }),
    [data, specialty, query],
  );

  const filteredPeriodTotal = periodRows.reduce(
    (sum, row) => sum + Number(row.cantidad || 0),
    0,
  );

  return (
    <div className="v2-stack operation-exclusions">
      <section className="v2-panel operation-exclusions-hero">
        <div className="v2-section-head">
          <div>
            <span className="v2-kicker">CONTROL DE EXCLUSIONES</span>
            <h3>Actividades excluidas por OPERACIÓN</h3>
            <p>
              Consulta los planes que no entran al PMP de mantenimiento porque su nombre
              comienza con OPERACIÓN y revisa cuántas filas fueron retiradas en el período.
            </p>
          </div>
          <Badge tone="warn">Regla automática</Badge>
        </div>

        <div className="operation-exclusion-kpis">
          <article>
            <span>Planes excluidos del maestro</span>
            <b>{data?.catalog_total ?? "—"}</b>
            <small>marcados como OPERACIÓN</small>
          </article>
          <article className="period">
            <span>Exclusiones del período</span>
            <b>{data?.period_total ?? "—"}</b>
            <small>filas retiradas del PMP seleccionado</small>
          </article>
          <article>
            <span>Mecánica</span>
            <b>{data?.catalog_by_specialty?.MEC ?? 0}</b>
            <small>planes en catálogo</small>
          </article>
          <article>
            <span>Eléctrica</span>
            <b>{data?.catalog_by_specialty?.ELE ?? 0}</b>
            <small>planes en catálogo</small>
          </article>
        </div>
      </section>

      <section className="v2-panel">
        <div className="v2-section-head">
          <div>
            <span className="v2-kicker">FILTROS</span>
            <h3>Buscar actividades excluidas</h3>
          </div>
          <button type="button" onClick={load} disabled={loading}>
            {loading ? "Actualizando..." : "Actualizar"}
          </button>
        </div>
        <div className="operation-exclusion-filters">
          <label>
            <span>Especialidad</span>
            <select value={specialty} onChange={(event) => setSpecialty(event.target.value)}>
              <option value="">Todas</option>
              {Object.entries(SPEC_NAMES).map(([code, name]) => (
                <option key={code} value={code}>{code} · {name}</option>
              ))}
            </select>
          </label>
          <label className="search">
            <span>Buscar</span>
            <input
              value={search}
              onChange={(event) => setSearch(event.target.value)}
              placeholder="Grupo, plan o descripción..."
            />
          </label>
        </div>
        {error && <div className="v2-error">{error}</div>}
      </section>

      <section className="v2-panel">
        <div className="v2-section-head">
          <div>
            <span className="v2-kicker">PERÍODO SELECCIONADO</span>
            <h3>Exclusiones aplicadas al PMP</h3>
            <p>
              Estas cantidades corresponden a filas que fueron detectadas como OPERACIÓN
              y por eso no entraron a la cartera preventiva del período.
            </p>
          </div>
          <Badge tone={filteredPeriodTotal ? "warn" : "ok"}>
            {filteredPeriodTotal} excluida{filteredPeriodTotal === 1 ? "" : "s"}
          </Badge>
        </div>

        <div className="v2-table-wrap operation-exclusions-table">
          <table>
            <thead>
              <tr>
                <th>Especialidad</th>
                <th>Grupo</th>
                <th>Plan detectado en calendario</th>
                <th>Plan maestro</th>
                <th>Cantidad</th>
                <th>Origen del registro</th>
              </tr>
            </thead>
            <tbody>
              {periodRows.map((row, index) => (
                <tr key={`${row.plan_clave_software}-${row.especialidad}-${index}`}>
                  <td><Badge>{row.especialidad || "—"}</Badge></td>
                  <td><b>{row.grupo || "—"}</b></td>
                  <td><span className="operation-plan-name">{row.plan_clave_software}</span></td>
                  <td>
                    <b>{row.plan_maestro || "—"}</b>
                    {row.descripcion_maestro && row.descripcion_maestro !== row.plan_maestro && (
                      <small>{row.descripcion_maestro}</small>
                    )}
                  </td>
                  <td><strong>{Number(row.cantidad || 0)}</strong></td>
                  <td>
                    <span className="operation-origin">
                      {row.origen === "SANEAMIENTO_PRE_PILOTO"
                        ? "Saneamiento pre-piloto"
                        : "Carga de Lista de Calendario"}
                    </span>
                  </td>
                </tr>
              ))}
              {!periodRows.length && (
                <tr>
                  <td colSpan={6} className="v2-empty">
                    No hay exclusiones registradas para este período con los filtros seleccionados.
                  </td>
                </tr>
              )}
            </tbody>
          </table>
        </div>
      </section>

      <section className="v2-panel">
        <div className="v2-section-head">
          <div>
            <span className="v2-kicker">CATÁLOGO MAESTRO</span>
            <h3>Planes clasificados como OPERACIÓN</h3>
            <p>
              Este catálogo define qué actividades deben permanecer fuera de la programación
              preventiva de mantenimiento.
            </p>
          </div>
          <Badge>{catalog.length} visibles</Badge>
        </div>

        <div className="v2-table-wrap operation-exclusions-table">
          <table>
            <thead>
              <tr>
                <th>Especialidad</th>
                <th>Grupo</th>
                <th>Plan de trabajo</th>
                <th>Descripción</th>
                <th>Estado</th>
              </tr>
            </thead>
            <tbody>
              {catalog.map((row) => (
                <tr key={row.id}>
                  <td><Badge>{row.especialidad || "—"}</Badge></td>
                  <td><b>{row.grupo}</b></td>
                  <td><span className="operation-plan-name">{row.plan_trabajo}</span></td>
                  <td>{row.descripcion_plan_trabajo || "—"}</td>
                  <td>
                    <Badge tone={row.habilitado ? "ok" : "warn"}>
                      {row.habilitado ? "Habilitado" : "No habilitado"}
                    </Badge>
                  </td>
                </tr>
              ))}
              {!catalog.length && (
                <tr>
                  <td colSpan={5} className="v2-empty">
                    No hay planes OPERACIÓN con los filtros seleccionados.
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
