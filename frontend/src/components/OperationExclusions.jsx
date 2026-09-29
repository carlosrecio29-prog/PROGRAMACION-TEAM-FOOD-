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

function fmt(value) {
  const number = Number(value || 0);
  return Number.isFinite(number)
    ? number.toLocaleString("es-CO", { maximumFractionDigits: 1 })
    : "0";
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

  const details = useMemo(
    () => (data?.period_details || []).filter((row) => {
      if (specialty && row.especialidad !== specialty) return false;
      if (!query) return true;
      return normalize([
        row.numero_ot,
        row.activo_codigo,
        row.descripcion_activo,
        row.plan_clave_software,
        row.titulo,
        row.cronograma_planeacion,
        row.especialidad,
      ].join(" ")).includes(query);
    }),
    [data, specialty, query],
  );

  const summaryRows = useMemo(
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

  const visibleEquipment = new Set(details.map((row) => row.activo_codigo).filter(Boolean)).size;
  const visiblePlans = new Set(details.map((row) => row.plan_clave_software).filter(Boolean)).size;

  return (
    <div className="v2-stack operation-exclusions">
      <section className="v2-panel operation-exclusions-hero">
        <div className="v2-section-head">
          <div>
            <span className="v2-kicker">CONTROL DE EXCLUSIONES</span>
            <h3>Equipos y PMP excluidos por OPERACIÓN</h3>
            <p>
              Aquí puedes auditar exactamente qué actividades de la Lista de Calendario
              fueron retiradas del PMP de mantenimiento, incluyendo el equipo y el plan
              que originó la exclusión.
            </p>
          </div>
          <Badge tone="warn">Regla automática</Badge>
        </div>

        <div className="operation-exclusion-kpis">
          <article className="period">
            <span>Actividades excluidas</span>
            <b>{data?.period_total ?? "—"}</b>
            <small>filas retiradas del período</small>
          </article>
          <article>
            <span>Equipos afectados</span>
            <b>{data?.period_unique_equipment ?? "—"}</b>
            <small>equipos distintos</small>
          </article>
          <article>
            <span>PMP excluidos</span>
            <b>{data?.period_unique_plans ?? "—"}</b>
            <small>planes distintos</small>
          </article>
          <article>
            <span>Planes OPERACIÓN maestro</span>
            <b>{data?.catalog_total ?? "—"}</b>
            <small>regla maestra de exclusión</small>
          </article>
        </div>
      </section>

      <section className="v2-panel">
        <div className="v2-section-head">
          <div>
            <span className="v2-kicker">FILTROS</span>
            <h3>Buscar por equipo, OT o PMP</h3>
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
              placeholder="Código de equipo, nombre, OT o PMP..."
            />
          </label>
        </div>
        {error && <div className="v2-error">{error}</div>}
      </section>

      <section className="v2-panel">
        <div className="v2-section-head">
          <div>
            <span className="v2-kicker">DETALLE DEL PERÍODO</span>
            <h3>Actividades retiradas de la Lista de Calendario</h3>
            <p>
              Cada fila corresponde a una actividad real del archivo mensual que no entró
              a programación porque su plan fue identificado como OPERACIÓN.
            </p>
          </div>
          <div className="operation-detail-badges">
            <Badge tone={details.length ? "warn" : "ok"}>{details.length} visibles</Badge>
            <Badge>{visibleEquipment} equipos</Badge>
            <Badge>{visiblePlans} PMP</Badge>
          </div>
        </div>

        <div className="v2-table-wrap operation-exclusions-table operation-detail-table">
          <table>
            <thead>
              <tr>
                <th>OT</th>
                <th>Especialidad</th>
                <th>Equipo</th>
                <th>Descripción del equipo</th>
                <th>PMP excluido</th>
                <th>Actividad</th>
                <th>Tiempo</th>
                <th>Estado</th>
              </tr>
            </thead>
            <tbody>
              {details.map((row) => (
                <tr key={row.id}>
                  <td>
                    <b className="operation-ot">{row.numero_ot || "SIN OT"}</b>
                    {row.fila_origen && <small>Fila {row.fila_origen}</small>}
                  </td>
                  <td><Badge>{row.especialidad || "—"}</Badge></td>
                  <td><b className="operation-equipment-code">{row.activo_codigo}</b></td>
                  <td>{row.descripcion_activo || "—"}</td>
                  <td><span className="operation-plan-name">{row.plan_clave_software}</span></td>
                  <td>
                    <b>{row.titulo || "—"}</b>
                    {row.cronograma_planeacion && row.cronograma_planeacion !== row.titulo && (
                      <small>{row.cronograma_planeacion}</small>
                    )}
                  </td>
                  <td>{fmt(row.tiempo_planeado_min)} min</td>
                  <td><Badge tone="warn">{row.estado || "—"}</Badge></td>
                </tr>
              ))}
              {!details.length && (
                <tr>
                  <td colSpan={8} className="v2-empty">
                    {loading
                      ? "Cargando detalle de exclusiones..."
                      : "No hay actividades excluidas registradas para este período con los filtros seleccionados."}
                  </td>
                </tr>
              )}
            </tbody>
          </table>
        </div>
      </section>

      {!!summaryRows.length && (
        <section className="v2-panel">
          <div className="v2-section-head">
            <div>
              <span className="v2-kicker">RESUMEN POR PMP</span>
              <h3>Cuántas actividades fueron retiradas por cada plan</h3>
            </div>
            <Badge>{summaryRows.length} planes</Badge>
          </div>
          <div className="v2-table-wrap operation-exclusions-table">
            <table>
              <thead>
                <tr>
                  <th>Especialidad</th>
                  <th>PMP detectado en calendario</th>
                  <th>Plan maestro</th>
                  <th>Cantidad</th>
                </tr>
              </thead>
              <tbody>
                {summaryRows.map((row, index) => (
                  <tr key={`${row.plan_clave_software}-${row.especialidad}-${index}`}>
                    <td><Badge>{row.especialidad || "—"}</Badge></td>
                    <td><span className="operation-plan-name">{row.plan_clave_software}</span></td>
                    <td>
                      <b>{row.plan_maestro || "—"}</b>
                      {row.descripcion_maestro && row.descripcion_maestro !== row.plan_maestro && (
                        <small>{row.descripcion_maestro}</small>
                      )}
                    </td>
                    <td><strong>{Number(row.cantidad || 0)}</strong></td>
                  </tr>
                ))}
              </tbody>
            </table>
          </div>
        </section>
      )}

      <details className="v2-panel operation-catalog-details">
        <summary>
          <span>
            <b>Catálogo maestro de planes OPERACIÓN</b>
            <small>Ver los {data?.catalog_total ?? 0} planes que definen la regla de exclusión.</small>
          </span>
        </summary>
        <div className="v2-section-head" style={{ marginTop: 14 }}>
          <div>
            <span className="v2-kicker">CATÁLOGO MAESTRO</span>
            <h3>Planes clasificados como OPERACIÓN</h3>
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
            </tbody>
          </table>
        </div>
      </details>
    </div>
  );
}
