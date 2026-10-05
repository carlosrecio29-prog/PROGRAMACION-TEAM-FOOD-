import { useEffect, useMemo, useState } from "react";
import { monthWeeks, initialWeekIndex } from "../features/planning/monthWeeks.js";
import {
  downloadV2WeekTrackingExcel,
  getV2WeekProgramming,
  getV2WeekTracking,
  uploadV2WeekTracking,
} from "../api";
import Badge from "../shared/Badge";

const SPEC_NAMES = {
  MEC: "Mecánica",
  ELE: "Eléctrica",
  MET: "Metrología",
  SER: "Servicios",
};
const SPECS = ["MEC", "ELE", "MET", "SER"];

function number(value) {
  const parsed = Number(value);
  return Number.isFinite(parsed) ? parsed : 0;
}
function fmt(value, decimals = 1) {
  return number(value).toLocaleString("es-CO", {
    minimumFractionDigits: decimals,
    maximumFractionDigits: decimals,
  });
}
function when(value) {
  if (!value) return "—";
  try {
    return new Date(value).toLocaleString("es-CO", {
      day: "2-digit",
      month: "short",
      hour: "2-digit",
      minute: "2-digit",
    });
  } catch {
    return String(value);
  }
}

export default function WeeklyTracking({ year, month, onOpenClosure }) {
  const weeks = useMemo(() => monthWeeks(year, month), [year, month]);
  const [weekIndex, setWeekIndex] = useState(() => initialWeekIndex(weeks));
  const [specialty, setSpecialty] = useState("MEC");
  const [programming, setProgramming] = useState(null);
  const [tracking, setTracking] = useState(null);
  const [file, setFile] = useState(null);
  const [loading, setLoading] = useState(false);
  const [uploading, setUploading] = useState(false);
  const [error, setError] = useState("");
  const [message, setMessage] = useState("");
  const [areaFilter, setAreaFilter] = useState("");
  const [search, setSearch] = useState("");
  const [downloading, setDownloading] = useState(false);

  const week = weeks[Math.min(weekIndex, weeks.length - 1)] || weeks[0];

  async function load() {
    if (!week) return;
    try {
      setLoading(true);
      setError("");
      const programmed = await getV2WeekProgramming(week.from, week.to, specialty);
      setProgramming(programmed);
      if (programmed?.programming?.id) {
        setTracking(await getV2WeekTracking(programmed.programming.id));
      } else {
        setTracking(null);
      }
    } catch (cause) {
      setError(cause.message || "No se pudo consultar el seguimiento semanal.");
      setProgramming(null);
      setTracking(null);
    } finally {
      setLoading(false);
    }
  }

  useEffect(() => {
    setWeekIndex(initialWeekIndex(weeks));
  }, [month]);
  useEffect(() => {
    setFile(null);
    setMessage("");
    setAreaFilter("");
    setSearch("");
    load();
  }, [week?.from, week?.to, specialty]);

  async function registerProgress() {
    const programmingId = programming?.programming?.id;
    if (!programmingId || !file) {
      setError("Selecciona una semana programada y la Lista de Calendario actualizada.");
      return;
    }
    try {
      setUploading(true);
      setError("");
      setMessage("");
      const result = await uploadV2WeekTracking(programmingId, file);
      setTracking(result);
      setFile(null);
      const saved = result.saved || {};
      setMessage(
        `Avance registrado sin cerrar la semana: ${number(saved.finalizadas)} finalizadas · ${fmt(saved.avance_ot_pct)}% por OT · ${fmt(saved.avance_hh_pct)}% por H-H.`,
      );
    } catch (cause) {
      setError(cause.message || "No se pudo registrar el avance semanal.");
    } finally {
      setUploading(false);
    }
  }

  const id = programming?.programming?.id;
  const closed = programming?.programming?.estado === "CERRADA";
  const latest = tracking?.latest;
  const programmed = latest ? number(latest.total_items) : number(tracking?.rows?.length, programming?.selected_ids?.length || 0);
  const finalized = number(latest?.finalizados);
  const remaining = Math.max(0, programmed - finalized);
  const unmatched = number(latest?.sin_coincidencia);
  const otPct = number(latest?.avance_ot_pct);
  const hhPct = number(latest?.avance_hh_pct);
  const liveRows = tracking?.rows || [];
  const areas = useMemo(() => {
    const unique = new Map();
    liveRows.forEach((row) => {
      const code = row.area_codigo || "SIN ÁREA";
      if (!unique.has(code)) unique.set(code, row.area_nombre || "");
    });
    return [...unique.entries()].sort((a, b) => String(a[0]).localeCompare(String(b[0])));
  }, [liveRows]);
  const visibleRows = useMemo(() => {
    const term = search.trim().toLowerCase();
    return liveRows.filter((row) => {
      if (areaFilter && String(row.area_codigo || "") !== areaFilter) return false;
      if (!term) return true;
      return [
        row.numero_ot, row.area_codigo, row.area_nombre,
        row.activo_codigo, row.activo_descripcion,
        row.plan_trabajo, row.descripcion_grupo, row.estado_calendario,
      ].some((value) => String(value || "").toLowerCase().includes(term));
    });
  }, [liveRows, areaFilter, search]);

  async function downloadTracking() {
    if (!id) return;
    try {
      setDownloading(true);
      setError("");
      await downloadV2WeekTrackingExcel(id, areaFilter);
    } catch (cause) {
      setError(cause.message || "No se pudo descargar el Excel de seguimiento.");
    } finally {
      setDownloading(false);
    }
  }

  return (
    <div className="v2-stack weekly-tracking">
      <section className="v2-panel weekly-tracking-context">
        <div className="v2-section-head">
          <div>
            <span className="v2-kicker">SEGUIMIENTO DURANTE LA SEMANA</span>
            <h3>Avance de la programación sin realizar el cierre</h3>
            <p>
              Puedes cargar la Lista de Calendario varias veces. Cada carga queda guardada
              como una fotografía del avance y no modifica Backlog ni cierra la programación.
            </p>
          </div>
          <Badge tone={closed ? "ok" : latest ? "warn" : undefined}>
            {loading
              ? "Consultando..."
              : closed
                ? "SEMANA CERRADA"
                : latest
                  ? `Última carga · ${when(latest.registrado_en)}`
                  : "Sin seguimiento"}
          </Badge>
        </div>

        <div className="weekly-tracking-selectors">
          <label>
            <span>Semana</span>
            <select value={weekIndex} onChange={(event) => setWeekIndex(Number(event.target.value))}>
              {weeks.map((item, index) => (
                <option key={item.from} value={index}>
                  {item.transition ? "Transición" : `Semana ${item.weekNumber}`} · {item.label}
                </option>
              ))}
            </select>
          </label>
          <label>
            <span>Especialidad</span>
            <select value={specialty} onChange={(event) => setSpecialty(event.target.value)}>
              {SPECS.map((code) => (
                <option value={code} key={code}>{code} · {SPEC_NAMES[code]}</option>
              ))}
            </select>
          </label>
          <div className="weekly-tracking-program">
            <span>Programación</span>
            <b>{id ? `#${id}` : "No creada"}</b>
            <small>{week?.label || ""}</small>
          </div>
        </div>
      </section>

      {!id && !loading && (
        <section className="v2-panel v2-alert-panel">
          <span className="v2-kicker">SIN PROGRAMACIÓN</span>
          <h3>No hay actividades guardadas para hacer seguimiento</h3>
          <p>Primero guarda la Programación semanal de {SPEC_NAMES[specialty]}.</p>
        </section>
      )}

      {id && (
        <>
          {!closed && (
            <section className="v2-panel weekly-tracking-upload">
              <div>
                <span className="v2-kicker">NUEVA FOTOGRAFÍA DE AVANCE</span>
                <h3>Cargar Lista de Calendario actualizada</h3>
                <p>
                  Detectaremos únicamente el estado de las OT programadas. Este proceso
                  no cambia estados definitivos, no mueve OT a Backlog y no realiza el cierre.
                </p>
              </div>
              <div className="weekly-tracking-upload-actions">
                <input
                  type="file"
                  accept=".xlsx"
                  onChange={(event) => setFile(event.target.files?.[0] || null)}
                />
                <button
                  type="button"
                  className="v2-primary"
                  disabled={!file || uploading}
                  onClick={registerProgress}
                >
                  {uploading ? "Analizando..." : "Registrar avance"}
                </button>
              </div>
            </section>
          )}

          {error && <div className="v2-error">{error}</div>}
          {message && <div className="v2-success">{message}</div>}

          <section className="weekly-tracking-kpis">
            <article><span>OT programadas</span><b>{programmed}</b><small>alcance de la semana</small></article>
            <article className="ok"><span>Finalizadas detectadas</span><b>{finalized}</b><small>{fmt(otPct)}% por OT</small></article>
            <article className="pending"><span>Por finalizar</span><b>{remaining}</b><small>incluye OT por validar</small></article>
            <article className={unmatched ? "warn" : "ok"}><span>Sin coincidencia</span><b>{unmatched}</b><small>revisar antes del cierre</small></article>
            <article><span>Avance por H-H</span><b>{fmt(hhPct)}%</b><small>{fmt(latest?.hh_finalizadas)} / {fmt(latest?.hh_programadas)} H-H</small></article>
            <article><span>Última actualización</span><b className="tracking-date">{latest ? when(latest.registrado_en) : "—"}</b><small>{latest?.archivo_nombre || "Aún sin carga"}</small></article>
          </section>

          <section className="v2-panel weekly-tracking-board">
            <div className="v2-section-head weekly-tracking-board-head">
              <div>
                <span className="v2-kicker">PROGRAMACIÓN EN SEGUIMIENTO</span>
                <h3>Programación de la semana</h3>
                <p>Las OT finalizadas permanecen visibles y se tachan automáticamente. Las pendientes continúan activas para seguimiento.</p>
              </div>
              <div className="weekly-tracking-board-actions">
                <Badge tone="ok">{liveRows.filter((row) => row.finalizado === true).length} tachadas</Badge>
                <button type="button" onClick={downloadTracking} disabled={downloading}>
                  {downloading ? "Generando..." : "Descargar Excel"}
                </button>
              </div>
            </div>

            <div className="weekly-tracking-filters">
              <label>
                <span>Área</span>
                <select value={areaFilter} onChange={(event) => setAreaFilter(event.target.value)}>
                  <option value="">Todas las áreas</option>
                  {areas.map(([code, name]) => (
                    <option key={code} value={code}>{code}{name ? ` · ${name}` : ""}</option>
                  ))}
                </select>
              </label>
              <label className="search">
                <span>Buscar</span>
                <input
                  value={search}
                  onChange={(event) => setSearch(event.target.value)}
                  placeholder="OT, equipo o plan..."
                />
              </label>
              <div className="weekly-tracking-visible">
                <span>Visibles</span>
                <b>{visibleRows.length} / {liveRows.length}</b>
              </div>
            </div>

            <div className="v2-table-wrap weekly-tracking-board-table">
              <table>
                <thead>
                  <tr>
                    <th>Estado</th>
                    <th>OT</th>
                    <th>Área</th>
                    <th>Equipo</th>
                    <th>Plan de trabajo</th>
                    <th>Condición</th>
                    <th>Origen</th>
                    <th>H-H</th>
                    <th>Estado calendario</th>
                  </tr>
                </thead>
                <tbody>
                  {visibleRows.map((row) => {
                    const done = row.finalizado === true;
                    const pendingRow = row.finalizado === false;
                    return (
                      <tr
                        key={row.programacion_item_id}
                        className={done ? "tracking-row-finished" : pendingRow ? "tracking-row-pending" : "tracking-row-unchecked"}
                      >
                        <td>
                          {done
                            ? <Badge tone="ok">FINALIZADA ✓</Badge>
                            : pendingRow
                              ? <Badge tone="warn">PENDIENTE</Badge>
                              : <Badge>SIN VALIDAR</Badge>}
                        </td>
                        <td><b>{row.numero_ot || "SIN ASIGNAR"}</b></td>
                        <td><Badge>{row.area_codigo || "—"}</Badge><small>{row.area_nombre || ""}</small></td>
                        <td><b>{row.activo_codigo || "—"}</b><small>{row.activo_descripcion || ""}</small></td>
                        <td><span className="v2-plan">{row.plan_trabajo || "—"}</span><small>{row.descripcion_grupo || ""}</small></td>
                        <td>{row.requiere_parada ? <Badge tone="stop">Equipo detenido</Badge> : <Badge tone="ok">Equipo operando</Badge>}</td>
                        <td>{row.origen === "BACKLOG" || row.origen_backlog ? <Badge tone="backlog">BACKLOG</Badge> : <Badge>PMP DEL MES</Badge>}</td>
                        <td><b>{fmt(row.hh_programadas)}</b></td>
                        <td><span>{row.estado_calendario || (latest ? "Sin coincidencia" : "Aún sin carga")}</span></td>
                      </tr>
                    );
                  })}
                  {!visibleRows.length && (
                    <tr><td colSpan="9" className="v2-empty">No hay actividades con estos filtros.</td></tr>
                  )}
                </tbody>
              </table>
            </div>
          </section>

          <section className="v2-panel">
            <div className="v2-section-head">
              <div>
                <span className="v2-kicker">AVANCE POR ÁREA</span>
                <h3>Estado de la programación en la última carga</h3>
                <p>El porcentaje se calcula sobre las OT y H-H programadas de cada área.</p>
              </div>
              <Badge>{tracking?.by_area?.length || 0} áreas</Badge>
            </div>
            <div className="v2-table-wrap">
              <table>
                <thead>
                  <tr>
                    <th>Área</th>
                    <th>Programadas</th>
                    <th>Finalizadas</th>
                    <th>Pendientes</th>
                    <th>Sin coincidencia</th>
                    <th>Avance OT</th>
                    <th>Avance H-H</th>
                  </tr>
                </thead>
                <tbody>
                  {(tracking?.by_area || []).map((row) => (
                    <tr key={row.area_codigo}>
                      <td><Badge>{row.area_codigo}</Badge><small>{row.area_nombre || ""}</small></td>
                      <td><b>{number(row.programadas)}</b></td>
                      <td><b>{number(row.finalizadas)}</b></td>
                      <td><b>{number(row.pendientes)}</b></td>
                      <td><b>{number(row.sin_coincidencia)}</b></td>
                      <td><b>{fmt(row.avance_ot_pct)}%</b></td>
                      <td><b>{fmt(row.avance_hh_pct)}%</b><small>{fmt(row.hh_finalizadas)} / {fmt(row.hh_programadas)} H-H</small></td>
                    </tr>
                  ))}
                  {!tracking?.by_area?.length && (
                    <tr><td colSpan="7" className="v2-empty">No hay actividades disponibles para esta programación.</td></tr>
                  )}
                </tbody>
              </table>
            </div>
          </section>

          <section className="v2-panel">
            <div className="v2-section-head">
              <div>
                <span className="v2-kicker">HISTORIAL DE CARGAS</span>
                <h3>Evolución de la semana</h3>
                <p>Cada registro conserva el resultado observado en ese momento.</p>
              </div>
              <button type="button" className="weekly-tracking-close-link" onClick={onOpenClosure}>
                Ir a Cierre semanal →
              </button>
            </div>
            <div className="v2-table-wrap">
              <table>
                <thead>
                  <tr>
                    <th>Fecha</th>
                    <th>Archivo</th>
                    <th>Finalizadas</th>
                    <th>Pendientes</th>
                    <th>Sin coincidencia</th>
                    <th>Avance OT</th>
                    <th>Avance H-H</th>
                  </tr>
                </thead>
                <tbody>
                  {(tracking?.history || []).map((row) => (
                    <tr key={row.id}>
                      <td><b>{when(row.registrado_en)}</b></td>
                      <td><span className="v2-plan">{row.archivo_nombre}</span></td>
                      <td><b>{number(row.finalizados)}</b></td>
                      <td>{number(row.pendientes)}</td>
                      <td>{number(row.sin_coincidencia)}</td>
                      <td><b>{fmt(row.avance_ot_pct)}%</b></td>
                      <td><b>{fmt(row.avance_hh_pct)}%</b></td>
                    </tr>
                  ))}
                  {!tracking?.history?.length && (
                    <tr><td colSpan="7" className="v2-empty">Todavía no hay fotografías de avance guardadas.</td></tr>
                  )}
                </tbody>
              </table>
            </div>
          </section>
        </>
      )}
    </div>
  );
}
