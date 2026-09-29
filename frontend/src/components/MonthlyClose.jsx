import { useEffect, useMemo, useState } from "react";
import {
  closeV2Month,
  downloadV2ProgressPdf,
  getV2MonthlyClose,
  getV2ProgressPdfUrl,
} from "../api";
import Badge from "../shared/Badge";
import "./monthlyClose.css";

const MONTHS = [
  "Enero","Febrero","Marzo","Abril","Mayo","Junio",
  "Julio","Agosto","Septiembre","Octubre","Noviembre","Diciembre",
];

const NAMES = { MEC: "Mecánica", ELE: "Eléctrica", MET: "Metrología", SER: "Servicios" };
const number = (value) => Number(value || 0);
const count = (value) => number(value).toLocaleString("es-CO", { maximumFractionDigits: 0 });
const hh = (value) => number(value).toLocaleString("es-CO", { minimumFractionDigits: 1, maximumFractionDigits: 2 });
const pct = (value) => number(value).toLocaleString("es-CO", { maximumFractionDigits: 1 }) + "%";
const dateLabel = (value) => value ? String(value).split("-").reverse().join("/") : "—";

export default function MonthlyClose({ year, month }) {
  const [data, setData] = useState(null);
  const [loading, setLoading] = useState(true);
  const [closing, setClosing] = useState(false);
  const [downloading, setDownloading] = useState(false);
  const [error, setError] = useState("");
  const [message, setMessage] = useState("");

  async function load() {
    try {
      setLoading(true);
      setError("");
      setData(await getV2MonthlyClose(year, month));
    } catch (cause) {
      setError(cause.message || "No se pudo consultar el cierre mensual.");
    } finally {
      setLoading(false);
    }
  }

  useEffect(() => {
    setMessage("");
    load();
  }, [year, month]);

  const progress = data?.progress || {};
  const monthly = progress.monthly || {};
  const totals = progress.weekly_totals || {};
  const unresolved = progress.unresolved || [];
  const requirements = data?.requirements || [];
  const weeks = progress.weeks || [];

  const specialtySummary = useMemo(() => {
    return (progress.specialties || []).map((row) => ({
      ...row,
      name: NAMES[row.especialidad] || row.especialidad,
    }));
  }, [progress.specialties]);

  async function handleCloseMonth() {
    if (!data?.ready_to_close || closing) return;
    const confirmed = window.confirm(
      "Vas a registrar el cierre formal de " + MONTHS[month - 1] + " " + year +
      ". Las OT pendientes continuarán en backlog. ¿Deseas continuar?"
    );
    if (!confirmed) return;
    try {
      setClosing(true);
      setError("");
      setMessage("");
      const result = await closeV2Month(year, month, "Aplicación");
      setData(result);
      setMessage("Cierre mensual registrado correctamente.");
    } catch (cause) {
      setError(cause.message || "No fue posible cerrar el mes.");
    } finally {
      setClosing(false);
    }
  }

  async function handleDownload() {
    try {
      setDownloading(true);
      setError("");
      await downloadV2ProgressPdf(year, month);
    } catch (cause) {
      setError(cause.message || "No fue posible descargar el informe mensual.");
    } finally {
      setDownloading(false);
    }
  }

  if (loading && !data) {
    return <section className="v2-panel">Cargando validaciones del cierre mensual...</section>;
  }

  const closed = !!data?.is_closed;
  const progressPct = number(monthly.progress_ot_pct);
  const pendingCarryover = number(monthly.pending);

  return (
    <div className="v2-stack monthly-close">
      {error && <div className="v2-error">{error}</div>}
      {message && <div className="v2-success">{message}</div>}

      <section className={"v2-panel monthly-close-status " + (closed ? "closed" : data?.ready_to_close ? "ready" : "blocked")}>
        <div className="monthly-close-status-main">
          <div className="monthly-close-status-icon" aria-hidden="true">
            {closed ? "✓" : data?.ready_to_close ? "→" : "!"}
          </div>
          <div>
            <span className="v2-kicker">ESTADO DEL CIERRE</span>
            <h3>
              {closed
                ? MONTHS[month - 1] + " " + year + " · CERRADO"
                : data?.ready_to_close
                  ? "Mes listo para cierre formal"
                  : "Mes todavía en proceso"}
            </h3>
            <p>
              {closed
                ? "El período quedó registrado como cierre mensual formal."
                : data?.ready_to_close
                  ? "Todas las validaciones obligatorias están completas. Puedes formalizar el cierre."
                  : "Completa las validaciones pendientes antes de cerrar oficialmente el período."}
            </p>
          </div>
        </div>
        <div className="monthly-close-status-side">
          <Badge tone={closed ? "ok" : data?.ready_to_close ? "ok" : "warn"}>
            {closed ? "CERRADO" : data?.ready_to_close ? "LISTO" : "EN PROCESO"}
          </Badge>
          {closed && data?.record?.cerrado_en && (
            <small>Cerrado {new Date(data.record.cerrado_en).toLocaleString("es-CO")}</small>
          )}
        </div>
      </section>

      <section className="v2-panel">
        <div className="v2-section-head">
          <div>
            <span className="v2-kicker">VALIDACIÓN PREVIA</span>
            <h3>Requisitos para cerrar el mes</h3>
            <p>El cierre solo se habilita cuando todas estas condiciones estén cumplidas.</p>
          </div>
          <Badge tone={requirements.every((item) => item.ok) ? "ok" : "warn"}>
            {requirements.filter((item) => item.ok).length}/{requirements.length} completos
          </Badge>
        </div>

        <div className="monthly-close-checklist">
          {requirements.map((item) => (
            <article key={item.id} className={item.ok ? "ok" : "pending"}>
              <span className="monthly-close-check-icon">{item.ok ? "✓" : "!"}</span>
              <div>
                <b>{item.label}</b>
                <small>{item.detail}</small>
              </div>
            </article>
          ))}
        </div>
      </section>

      <section className="v2-panel">
        <div className="v2-section-head">
          <div>
            <span className="v2-kicker">CONSOLIDADO FINAL</span>
            <h3>Cómo termina el período</h3>
            <p>Resultado mensual consolidado por OT única según su última programación registrada.</p>
          </div>
          <div className="monthly-close-progress-badge">
            <strong>{pct(progressPct)}</strong>
            <span>cumplimiento OT</span>
          </div>
        </div>

        <div className="monthly-close-kpis">
          <article>
            <span>PMP mantenimiento</span>
            <b>{count(monthly.pmp_count)}</b>
            <small>registros del período</small>
          </article>
          <article>
            <span>OT programadas</span>
            <b>{count(monthly.programmed)}</b>
            <small>OT únicas</small>
          </article>
          <article className="success">
            <span>OT finalizadas</span>
            <b>{count(monthly.finalized)}</b>
            <small>{pct(progressPct)} de las programadas</small>
          </article>
          <article className="warning">
            <span>Pendientes a backlog</span>
            <b>{count(monthly.pending)}</b>
            <small>continúan al siguiente período</small>
          </article>
          <article>
            <span>PMP sin programar</span>
            <b>{count(monthly.not_programmed)}</b>
            <small>cartera no incluida en programación</small>
          </article>
          <article className={number(monthly.not_found) ? "danger" : "success"}>
            <span>No encontradas</span>
            <b>{count(monthly.not_found)}</b>
            <small>deben quedar conciliadas antes del cierre</small>
          </article>
        </div>

        <div className="monthly-close-hh">
          <div><span>H-H programadas</span><b>{hh(totals.hh_programmed)} H-H</b></div>
          <div><span>H-H finalizadas estimadas</span><b>{hh(totals.hh_finalized)} H-H</b></div>
          <div><span>Cumplimiento H-H estimado</span><b>{pct(totals.progress_hh_pct)}</b></div>
        </div>
      </section>

      <section className="v2-panel">
        <div className="v2-section-head">
          <div>
            <span className="v2-kicker">CIERRES SEMANALES</span>
            <h3>Estado de los cortes del mes</h3>
            <p>Resumen formal de las programaciones semanales que alimentan este cierre.</p>
          </div>
          <Badge tone={monthly.all_weeks_closed ? "ok" : "warn"}>
            {count(monthly.weeks_closed)} / {count(monthly.weeks_total)} cerradas
          </Badge>
        </div>

        <div className="monthly-close-weeks">
          {weeks.map((week) => (
            <article key={week.programming_id} className={week.estado === "CERRADA" ? "closed" : "open"}>
              <div>
                <b>{NAMES[week.especialidad] || week.especialidad}</b>
                <small>{dateLabel(week.week_from)} – {dateLabel(week.week_to)}</small>
              </div>
              <span>{week.estado === "CERRADA" ? "CERRADA" : "ABIERTA"}</span>
              <strong>{week.estado === "CERRADA" ? pct(week.progress_ot_pct) : "—"}</strong>
            </article>
          ))}
          {!weeks.length && <div className="v2-empty">Aún no existen programaciones semanales en este período.</div>}
        </div>
      </section>

      <section className="v2-panel">
        <div className="v2-section-head">
          <div>
            <span className="v2-kicker">ARRASTRE AL SIGUIENTE MES</span>
            <h3>Pendientes y backlog</h3>
            <p>
              Las OT pendientes no impiden cerrar el mes cuando fueron conciliadas correctamente;
              permanecen disponibles para reprogramación posterior.
            </p>
          </div>
          <Badge tone={pendingCarryover ? "warn" : "ok"}>{pendingCarryover} pendientes</Badge>
        </div>

        <div className="v2-table-wrap monthly-close-unresolved">
          <table>
            <thead>
              <tr><th>OT</th><th>Especialidad</th><th>Equipo</th><th>Plan</th><th>Resultado</th><th>H-H est.</th></tr>
            </thead>
            <tbody>
              {unresolved.slice(0, 60).map((row, index) => (
                <tr key={row.numero_ot + "-" + index}>
                  <td><b>{row.numero_ot}</b></td>
                  <td>{NAMES[row.especialidad] || row.especialidad}</td>
                  <td>{row.activo}</td>
                  <td>{row.plan}</td>
                  <td><Badge tone={row.resultado === "PENDIENTE" ? "warn" : "danger"}>{row.resultado}</Badge></td>
                  <td>{hh(row.hh_estimada)}</td>
                </tr>
              ))}
              {!unresolved.length && (
                <tr><td colSpan={6} className="v2-empty">No hay pendientes ni actividades sin conciliar en los últimos cierres.</td></tr>
              )}
            </tbody>
          </table>
        </div>
      </section>

      {!!specialtySummary.length && (
        <section className="v2-panel">
          <div className="v2-section-head">
            <div>
              <span className="v2-kicker">RESULTADO POR ESPECIALIDAD</span>
              <h3>Consolidado de cierre</h3>
            </div>
          </div>
          <div className="monthly-close-specialties">
            {specialtySummary.map((row) => (
              <article key={row.especialidad}>
                <span>{row.name}</span>
                <b>{pct(row.progress_ot_pct)}</b>
                <small>{count(row.finalized)} de {count(row.programmed)} OT finalizadas</small>
              </article>
            ))}
          </div>
        </section>
      )}

      <section className="v2-panel monthly-close-actions">
        <div>
          <span className="v2-kicker">CIERRE FORMAL E INFORME</span>
          <h3>{closed ? "Período cerrado" : "Formalizar cierre mensual"}</h3>
          <p>
            El PDF conserva el consolidado mensual. El botón de cierre registra formalmente
            que el período completó todas las validaciones.
          </p>
        </div>
        <div className="monthly-close-action-buttons">
          <button type="button" onClick={handleDownload} disabled={downloading || !weeks.length}>
            {downloading ? "Generando..." : "Descargar PDF mensual"}
          </button>
          <a href={getV2ProgressPdfUrl(year, month)} target="_blank" rel="noopener noreferrer">
            Abrir PDF
          </a>
          <button
            type="button"
            className="v2-primary monthly-close-finalize"
            onClick={handleCloseMonth}
            disabled={!data?.ready_to_close || closing || closed}
          >
            {closed ? "Mes cerrado" : closing ? "Cerrando..." : "Cerrar mes"}
          </button>
        </div>
      </section>
    </div>
  );
}
