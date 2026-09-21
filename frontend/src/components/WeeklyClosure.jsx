import { useEffect, useMemo, useState } from "react";
import {monthWeeks,initialWeekIndex} from "../features/planning/monthWeeks.js";
import {
  getV2WeekProgramming,
  getV2WeekClosure,
  previewV2WeekClosure,
  uploadV2WeekClosure,
} from "../api";
import Badge from "../shared/Badge";

const MONTHS = [
  "Enero",
  "Febrero",
  "Marzo",
  "Abril",
  "Mayo",
  "Junio",
  "Julio",
  "Agosto",
  "Septiembre",
  "Octubre",
  "Noviembre",
  "Diciembre",
];
const SPEC_NAMES = {
  MEC: "Mecánica",
  ELE: "Eléctrica",
  MET: "Metrología",
  SER: "Servicios",
};
const SPECS = ["MEC", "ELE", "MET", "SER"];

function number(v, d = 0) {
  const n = Number(v);
  return Number.isFinite(n) ? n : d;
}
function fmt(v, d = 1) {
  return number(v).toLocaleString("es-CO", {
    minimumFractionDigits: d,
    maximumFractionDigits: d,
  });
}
export default function WeeklyClosure({ year, month, onOpenBacklog }) {
  const weeks = useMemo(() => monthWeeks(year, month), [year, month]);
  const [weekIndex, setWeekIndex] = useState(() => initialWeekIndex(weeks));
  const [specialty, setSpecialty] = useState("MEC");
  const [programming, setProgramming] = useState(null);
  const [closure, setClosure] = useState(null);
  const [file, setFile] = useState(null);
  const [preview, setPreview] = useState(null);
  const [acceptMissing, setAcceptMissing] = useState(false);
  const problemRows = (preview?.rows || []).filter(row => row.finalizado === null);
  const missingRows = problemRows.filter(row => ["NO_ENCONTRADA", "SIN_NUMERO_OT"].includes(row.coincidencia));
  const conflictingRows = problemRows.filter(row => !["NO_ENCONTRADA", "SIN_NUMERO_OT"].includes(row.coincidencia));
  const closureBlocked = conflictingRows.length > 0 || (missingRows.length > 0 && !acceptMissing);
  const [loading, setLoading] = useState(false);
  const [uploading, setUploading] = useState(false);
  const [error, setError] = useState("");
  const [message, setMessage] = useState("");
  const week = weeks[Math.min(weekIndex, weeks.length - 1)] || weeks[0];

  async function load() {
    if (!week) return;
    try {
      setLoading(true);
      setError("");
      setMessage("");
      const p = await getV2WeekProgramming(week.from, week.to, specialty);
      setProgramming(p);
      if (p.programming?.id) {
        setClosure(await getV2WeekClosure(p.programming.id));
      } else {
        setClosure(null);
      }
    } catch (e) {
      setError(e.message);
      setProgramming(null);
      setClosure(null);
    } finally {
      setLoading(false);
    }
  }
  useEffect(() => {
    setWeekIndex(initialWeekIndex(weeks));
  }, [month]);
  useEffect(() => {
    setPreview(null);
    setAcceptMissing(false);
    setFile(null);
    load();
  }, [week?.from, week?.to, specialty]);

  async function previewWeek() {
    const id = programming?.programming?.id;
    if (!id || !file) {
      setError("Selecciona una semana programada y la Lista de Calendario actualizada.");
      return;
    }
    try {
      setUploading(true);
      setError("");
      setPreview(null);
      setAcceptMissing(false);
      const result = await previewV2WeekClosure(id, file);
      setPreview(result);
    } catch (e) {
      setError(e.message || "No se pudo comparar el calendario.");
    } finally {
      setUploading(false);
    }
  }

  async function closeWeek() {
    const id = programming?.programming?.id;
    if (!id) {
      setError(
        "Primero debe existir una programación guardada para esta semana.",
      );
      return;
    }
    if (!file) {
      setError("Selecciona el archivo Excel del calendario/PMP actualizado.");
      return;
    }
    if (!preview || Number(preview.programming?.id) !== Number(id)) {
      setError("Primero compara el Excel con las OT guardadas; el cierre no se ha procesado.");
      return;
    }
    if (missingRows.length > 0 && !acceptMissing) {
      setError("Marca la casilla para autorizar exclusivamente las OT verdaderamente ausentes.");
      return;
    }
    if (conflictingRows.length > 0) {
      setError(`El Excel tiene ${conflictingRows.length} OT con conflicto. Revisa el detalle resaltado; no se envían a backlog como si estuvieran ausentes.`);
      return;
    }
    if (closure?.programming?.estado === "CERRADA") {
      setError("Esta semana ya fue cerrada. Consulta el resultado; no se reemplazará su cierre.");
      return;
    }
    try {
      setUploading(true);
      setError("");
      setMessage("");
      const result = await uploadV2WeekClosure(id, file);
      setClosure(result);
      await load();
      const s = result.summary || {};
      setMessage(
        `Cierre realizado: ${number(s.finalized)} finalizadas, ${number(s.pending)} pendientes y ${number(s.not_found)} no encontradas. ${number(s.moved_to_backlog)} OT quedaron en BACKLOG.`,
      );
      setFile(null);
      setPreview(null);
      setAcceptMissing(false);
    } catch (e) {
      setError(e.message);
    } finally {
      setUploading(false);
    }
  }

  const rows = closure?.rows || [];
  const summary = closure?.summary || {};
  const finalized = number(summary.finalized);
  const pending = number(summary.pending);
  const notFound = number(summary.not_found);
  const unchecked = number(summary.unchecked, rows.length);
  const verified = summary.verified === true;
  const hhTotal = number(summary.hh_programmed);
  const hhFinalized = number(summary.hh_finalized);
  const hhPending = number(summary.hh_pending);
  const pct = number(summary.compliance_pct);

  return (
    <div className="v2-stack">
      <section className="v2-panel">
        <div className="v2-section-head">
          <div>
            <span className="v2-kicker">CIERRE SEMANAL</span>
            <h3>Selecciona la semana que vas a verificar</h3>
            <p>
              Sube nuevamente la lista de calendario/PMP exportada del software.
              La app compara solo las OT que programaste en esa semana.
            </p>
          </div>
          <Badge>
            {loading
              ? "Consultando..."
              : programming?.programming?.id
                ? `Programación #${programming.programming.id}`
                : "Sin programación"}
          </Badge>
        </div>
        <div className="v2-week-selector">
          <div className="v2-week-buttons">
            {weeks.map((w, i) => (
              <button
                type="button"
                key={w.from}
                className={weekIndex === i ? "active" : ""}
                onClick={() => setWeekIndex(i)}
              >
                <b>{w.transition ? 'Transición' : `Semana ${w.weekNumber}`}</b>
                <span>{w.label}</span>
              </button>
            ))}
          </div>
          <div className="v2-specialty-buttons">
            {SPECS.map((s) => (
              <button
                type="button"
                key={s}
                className={specialty === s ? "active" : ""}
                onClick={() => setSpecialty(s)}
              >
                <b>{s}</b>
                <span>{SPEC_NAMES[s]}</span>
              </button>
            ))}
          </div>
        </div>
      </section>

      {!programming?.programming?.id && !loading && (
        <section className="v2-panel v2-alert-panel">
          <div className="v2-section-head">
            <div>
              <span className="v2-kicker">SIN PROGRAMACIÓN</span>
              <h3>No hay una semana guardada para cerrar</h3>
              <p>
                Primero genera y guarda la programación de{" "}
                {SPEC_NAMES[specialty]} para {week?.label}.
              </p>
            </div>
          </div>
        </section>
      )}

      {programming?.programming?.id && (
        <>
          <section className="v2-capacity-panel">
            <div className="v2-capacity-cards">
              <div>
                <span>H-H programadas</span>
                <b>{fmt(hhTotal, 1)}</b>
                <small>{rows.length} actividades de la semana</small>
              </div>
              <div className="target">
                <span>H-H finalizadas</span>
                <b>{verified ? fmt(hhFinalized, 1) : "—"}</b>
                <small>{verified ? `${finalized} finalizadas` : "pendiente de verificación"}</small>
              </div>
              <div>
                <span>H-H pendientes</span>
                <b>{verified ? fmt(hhPending, 1) : "—"}</b>
                <small>{verified ? `${pending + notFound} OT pasan a backlog` : "pendiente de verificación"}</small>
              </div>
              <div>
                <span>No encontradas</span>
                <b>{verified ? notFound : "—"}</b>
                <small>{verified ? "también se conservan en backlog" : "pendiente de verificación"}</small>
              </div>
              <div className={unchecked ? "remaining" : "complete"}>
                <span>{unchecked ? "Sin verificar" : "Cierre"}</span>
                <b>{verified ? fmt(pct, 0) + "%" : unchecked}</b>
                <small>
                  {unchecked
                    ? "carga el calendario actualizado"
                    : "de OT finalizadas"}
                </small>
              </div>
            </div>
            <div className="v2-progress-block">
              <div className="v2-progress-copy">
                <span>Cumplimiento semanal por H-H</span>
                <b>{verified ? `${fmt(pct, 1)}%` : "Pendiente"}</b>
              </div>
              <div className="v2-progress-track">
                <i style={{ width: `${verified ? Math.min(100, pct) : 0}%` }} />
              </div>
              <div className="v2-progress-foot">
                <span>{finalized} finalizadas</span>
                <span>
                  {rows.length} programadas · {fmt(hhTotal, 1)} H-H
                </span>
              </div>
            </div>
          </section>

          <section className="v2-panel">
            <div className="v2-section-head">
              <div>
                <span className="v2-kicker">ACTUALIZAR ESTADO</span>
                <h3>Cargar calendario/PMP para cerrar la semana</h3>
                <p>
                  El archivo debe contener las columnas de la exportación del
                  software, incluyendo Orden, Activo, PlanTrabajo y Estado. Las
                  OT que no estén FINALIZADAS quedarán disponibles como BACKLOG
                  para la siguiente semana.
                </p>
              </div>
              {closure?.programming?.estado === "CERRADA" ? (
                <Badge tone="ok">Semana cerrada</Badge>
              ) : (
                <Badge tone="warn">Pendiente de cierre</Badge>
              )}
            </div>
            <div className="v2-toolbar">
              <input
                type="file"
                accept=".xlsx"
                onChange={(e) => {
                  setFile(e.target.files?.[0] || null);
                  setPreview(null);
                  setAcceptMissing(false);
                  setError("");
                }}
              />
              <button type="button" className="v2-primary"
                disabled={!file || uploading || closure?.programming?.estado === "CERRADA"}
                onClick={previewWeek}>
                {uploading ? "Comparando..." : "1. Comparar Excel (sin cerrar)"}
              </button>
              <button type="button"
                disabled={!file || !preview || uploading || closureBlocked ||
                  closure?.programming?.estado === "CERRADA"}
                onClick={closeWeek}>
                {uploading ? "Procesando..." : "2. Confirmar cierre semanal"}
              </button>
            </div>
            {preview && (
              <div className="v2-panel" style={{ marginTop: 12 }}>
                <span className="v2-kicker">VISTA PREVIA · NO MODIFICA LA BASE</span>
                <h3>Conciliación de la programación #{preview.programming?.id}</h3>
                <p><b>{preview.summary?.programmed}</b> OT programadas · <b>{preview.summary?.finalized}</b> finalizadas ·
                  <b> {preview.summary?.pending}</b> abiertas/pendientes ·
                  <b> {preview.summary?.missing}</b> realmente no encontradas ·
                  <b> {preview.summary?.conflicts}</b> con conflicto de OT, equipo o plan ·
                  <b> {preview.summary?.blank_states}</b> sin estado.
                  Archivo: {preview.summary?.calendar_rows} filas.</p>
                <p>H-H: {fmt(preview.summary?.hh_programmed,2)} programadas · {fmt(preview.summary?.hh_finalized,2)} finalizadas ·
                  {fmt(preview.summary?.hh_pending,2)} pendientes. Cumplimiento estimado: {fmt(preview.summary?.compliance_pct,1)}%.</p>
                {conflictingRows.length > 0 && (
                  <div className="v2-error" role="alert" style={{ marginBottom: 12 }}>
                    El cierre está bloqueado por <b>{conflictingRows.length} OT con discrepancias reales</b>.
                    Marcar la casilla de backlog no resuelve conflictos de equipo, plan, duplicidad
                    ni estados vacíos. Revisa la tabla de abajo y corrige el archivo de origen.
                  </div>
                )}
                {missingRows.length > 0 && (
                  <label style={{ display:"block", marginBottom:12 }}>
                    <input type="checkbox" checked={acceptMissing}
                      onChange={e=>setAcceptMissing(e.target.checked)} />
                    He revisado las {missingRows.length} OT realmente ausentes y acepto conservarlas
                    como no encontradas en BACKLOG.
                  </label>
                )}
                {missingRows.length > 0 && !acceptMissing && conflictingRows.length === 0 && (
                  <div className="v2-warning" role="status">Para habilitar Confirmar cierre semanal, marca la casilla anterior.</div>
                )}
                {conflictingRows.length === 0 && (missingRows.length === 0 || acceptMissing) && (
                  <div className="v2-success" role="status">Conciliación revisada: puedes confirmar el cierre semanal.</div>
                )}
                <details open={problemRows.length > 0}>
                  <summary>Ver las {problemRows.length} OT que requieren atención (y el detalle de toda la semana)</summary>
                  {problemRows.length > 0 && <div className="v2-error" style={{ marginTop:8 }}>
                    OT a revisar: {problemRows.map(row => row.numero_ot || "SIN OT").join(" · ")}
                  </div>}
                  <div className="v2-table-wrap"><table>
                    <thead><tr><th>OT programada</th><th>Equipo</th><th>Plan</th><th>H-H</th><th>Estado en Excel</th><th>Coincidencia</th><th>Resultado</th></tr></thead>
                    <tbody>{(preview.rows||[]).map((row,i)=>(
                      <tr key={i} style={row.finalizado === null ? { background: "rgba(234, 179, 8, 0.12)" } : undefined}>
                        <td><b>{row.numero_ot || "SIN OT"}</b></td><td>{row.activo}</td><td>{row.plan}</td>
                        <td>{fmt(row.hh,2)}</td><td>{row.estado_excel || "NO ENCONTRADA"}</td>
                        <td><b>{row.coincidencia}</b>
                          {row.alternativas_en_excel?.length > 0 && row.finalizado === null &&
                            <small>Excel: {row.alternativas_en_excel.map(a =>
                              [a.activo || "SIN EQUIPO", a.plan || "SIN PLAN", a.estado || "SIN ESTADO"].join(" / ")
                            ).join(" | ")}</small>}
                        </td>
                        <td>{row.finalizado === true ? "FINALIZADA" : row.finalizado === false ? "PENDIENTE → BACKLOG" : "REVISAR"}</td>
                      </tr>
                    ))}</tbody>
                  </table></div>
                </details>
              </div>
            )}
            {file && (
              <div className="v2-success">
                Archivo seleccionado: {file.name}
              </div>
            )}
            {error && <div className="v2-error">{error}</div>}
            {message && <div className="v2-success">{message}</div>}
          </section>

          <section className="v2-panel">
            <div className="v2-section-head">
              <div>
                <span className="v2-kicker">RESULTADO DEL CIERRE</span>
                <h3>OT programadas vs. estado del software</h3>
                <p>
                  El origen queda guardado para distinguir lo que se programó
                  desde el PMP del mes de lo que fue recuperado desde backlog.
                </p>
              </div>
              <Badge>{rows.length} actividades</Badge>
            </div>
            <div className="v2-table-wrap">
              <table>
                <thead>
                  <tr>
                    <th>Origen</th>
                    <th>OT</th>
                    <th>Área</th>
                    <th>Equipo</th>
                    <th>Plan de trabajo</th>
                    <th>H-H</th>
                    <th>Estado cierre</th>
                    <th>Resultado</th>
                  </tr>
                </thead>
                <tbody>
                  {rows.map((r) => (
                    <tr key={r.programacion_item_id}>
                      <td>
                        {r.origen_backlog ? (
                          <Badge tone="backlog">BACKLOG</Badge>
                        ) : (
                          <Badge>PMP DEL MES</Badge>
                        )}
                      </td>
                      <td>
                        <b>{r.numero_ot || "SIN ASIGNAR"}</b>
                        {r.finalizado !== true && r.estado_cierre && (
                          <button type="button" className="v2-backlog-link" onClick={() => onOpenBacklog?.(r.orden_mantenimiento_id)}>
                            Ver en Backlog
                          </button>
                        )}
                      </td>
                      <td>
                        <Badge>{r.area_codigo || "—"}</Badge>
                      </td>
                      <td>
                        <b>{r.activo_codigo}</b>
                        <small>{r.activo_descripcion}</small>
                      </td>
                      <td>
                        <span className="v2-plan">{r.plan_trabajo || "—"}</span>
                        <small>{r.descripcion_grupo || ""}</small>
                      </td>
                      <td>
                        <b>{fmt(r.hh_programadas, 1)}</b>
                      </td>
                      <td>{r.estado_cierre || "SIN VERIFICAR"}</td>
                      <td>
                        {r.finalizado === true ? (
                          <Badge tone="ok">FINALIZADA</Badge>
                        ) : r.finalizado === false ? (
                          <Badge tone="warn">PENDIENTE → BACKLOG</Badge>
                        ) : r.estado_cierre ? (
                          <Badge tone="warn">NO ENCONTRADA → BACKLOG</Badge>
                        ) : (
                          <Badge>POR VERIFICAR</Badge>
                        )}
                      </td>
                    </tr>
                  ))}
                  {!rows.length && (
                    <tr>
                      <td colSpan="8" className="v2-empty">
                        La programación no tiene actividades.
                      </td>
                    </tr>
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
