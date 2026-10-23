import {useEffect, useState} from "react";
import {getV2Pmp} from "../../api";
import Badge from "../../shared/Badge";
const SPEC_NAMES = {MEC: "Mecánica", ELE: "Eléctrica", MET: "Metrología", SER: "Servicios"};
const SPECS = Object.keys(SPEC_NAMES);
const fmt = (value, digits = 1) => Number(value || 0).toLocaleString("es-CO", {minimumFractionDigits: digits, maximumFractionDigits: digits});
export default function Pmp({ year, month, dashboard }) {
  const [filters, setFilters] = useState({
    specialty: "",
    area: "",
    search: "",
  });
  const [data, setData] = useState(null);
  const [loading, setLoading] = useState(false);
  const [error, setError] = useState("");
  const load = async () => {
    try {
      setLoading(true);
      setError("");
      setData(await getV2Pmp({ year, month, ...filters, limit: 400 }));
    } catch (e) {
      setError(e.message);
    } finally {
      setLoading(false);
    }
  };
  useEffect(() => {
    let active = true;
    setLoading(true);
    setError("");
    setData(null);
    getV2Pmp({year, month, ...filters, limit: 400})
      .then(result => { if (active) setData(result); })
      .catch(cause => { if (active) setError(cause.message); })
      .finally(() => { if (active) setLoading(false); });
    return () => {active = false;};
  }, [year, month]);
  return (
    <section className="v2-panel">
      <div className="v2-section-head">
        <div>
          <span className="v2-kicker">PMP DEL MES</span>
          <h3>Órdenes y planes exportados por el software</h3>
          <p>
            El día de ejecución del software no gobierna nuestra programación
            interna; aquí usamos el mes como cartera de trabajo.
          </p>
        </div>
        <Badge>
          {loading
            ? "Consultando..."
            : (data?.rows?.length || 0) + " registros visibles"}
        </Badge>
      </div>
      <div className="v2-toolbar v2-toolbar-4">
        <select
          aria-label="Especialidad del PMP"
          value={filters.specialty}
          onChange={(e) =>
            setFilters((f) => ({ ...f, specialty: e.target.value }))
          }
        >
          <option value="">Todas las especialidades</option>
          {SPECS.map((s) => (
            <option key={s} value={s}>
              {SPEC_NAMES[s]}
            </option>
          ))}
        </select>
        <select
          aria-label="Área del PMP"
          value={filters.area}
          onChange={(e) => setFilters((f) => ({ ...f, area: e.target.value }))}
        >
          <option value="">Todas las áreas</option>
          {(dashboard?.areas || []).map((a) => (
            <option key={a.codigo} value={a.codigo}>
              {a.codigo} · {a.nombre || "Sin nombre raíz"}
            </option>
          ))}
        </select>
        <input
          aria-label="Buscar OT, equipo o plan en PMP"
          placeholder="OT, equipo o plan..."
          value={filters.search}
          onChange={(e) =>
            setFilters((f) => ({ ...f, search: e.target.value }))
          }
        />
        <button className="v2-primary" onClick={load} disabled={loading}>
          {loading ? "Consultando…" : "Aplicar filtros"}
        </button>
      </div>
      <p className="tf-scope-note">Se muestran hasta 400 registros de la consulta. Cada fila corresponde a un registro del PMP; una OT puede tener varios registros. Aplica filtros para consultar una selección más precisa.</p>
      {error && <div className="v2-error" role="alert">{error}<button type="button" onClick={load}>Reintentar</button></div>}
      <div className="v2-table-wrap v2-pmp-table" tabIndex={0} role="region" aria-label="Registros del PMP" aria-busy={loading}>
        <table>
          <thead>
            <tr>
              <th>OT</th>
              <th>Área</th>
              <th>Equipo</th>
              <th>Plan</th>
              <th>Esp.</th>
              <th>Personas</th>
              <th>Parada</th>
              <th>Tiempo</th>
              <th>H-H</th>
              <th>Dato</th>
            </tr>
          </thead>
          <tbody>
            {(data?.rows || []).map((r) => (
              <tr key={r.id}>
                <td>
                  <b>{r.numero_ot || "SIN ASIGNAR"}</b>
                </td>
                <td>
                  <Badge>{r.area_codigo || "—"}</Badge>
                  <small>{r.area_nombre || ""}</small>
                </td>
                <td>
                  <b>{r.activo_codigo}</b>
                  <small>{r.activo_descripcion}</small>
                </td>
                <td>
                  <span className="v2-plan">
                    {r.plan_trabajo || r.plan_clave_software}
                  </span>
                  <small>{r.descripcion_grupo || ""}</small>
                </td>
                <td>
                  <Badge>{r.especialidad || "—"}</Badge>
                </td>
                <td>{r.numero_personas_efectivo ?? "—"}</td>
                <td>
                  {r.requiere_parada == null ? (
                    <Badge tone="warn">Falta</Badge>
                  ) : r.requiere_parada ? (
                    <Badge tone="stop">Sí</Badge>
                  ) : (
                    <Badge tone="ok">No</Badge>
                  )}
                </td>
                <td>
                  {r.tiempo_min != null ? fmt(r.tiempo_min, 0) + " min" : "—"}
                </td>
                <td>
                  <b>{r.hh != null ? fmt(r.hh, 1) : "—"}</b>
                </td>
                <td>
                  <Badge tone={r.calidad_dato === "LISTO" ? "ok" : "warn"}>
                    {r.calidad_dato}
                  </Badge>
                </td>
              </tr>
            ))}
            {loading && <tr><td colSpan="10" className="v2-empty" role="status">Consultando cartera…</td></tr>}
            {!data?.rows?.length && !loading && !error && (
              <tr>
                <td colSpan="10" className="v2-empty">
                  No hay registros para estos filtros.
                </td>
              </tr>
            )}
          </tbody>
        </table>
      </div>
    </section>
  );
}


