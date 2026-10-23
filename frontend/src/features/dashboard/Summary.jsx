const number = (value, fallback = 0) => Number.isFinite(Number(value)) ? Number(value) : fallback;
const fmt = (value, digits = 1) => number(value).toLocaleString("es-CO", {minimumFractionDigits: digits, maximumFractionDigits: digits});
function ControlIcon({ type }) {
  const common = {
    viewBox: "0 0 48 48",
    "aria-hidden": "true",
    focusable: "false",
  };
  if (type === "calendar") {
    return <svg {...common}><path d="M10 8h28a4 4 0 0 1 4 4v26a4 4 0 0 1-4 4H10a4 4 0 0 1-4-4V12a4 4 0 0 1 4-4Zm0 12v18h28V20H10Zm5-16v9m18-9v9M15 26h7v7h-7Zm11 0h7v7h-7Z" /></svg>;
  }
  if (type === "clock") {
    return <svg {...common}><path d="M24 5a19 19 0 1 1 0 38 19 19 0 0 1 0-38Zm0 6a13 13 0 1 0 0 26 13 13 0 0 0 0-26Zm3 3v9.8l7 4-3 5-10-6V14h6Z" /></svg>;
  }
  if (type === "team") {
    return <svg {...common}><path d="M18 23a8 8 0 1 1 0-16 8 8 0 0 1 0 16Zm17-2a6 6 0 1 1 0-12 6 6 0 0 1 0 12ZM4 42v-6c0-6.1 5-11 11-11h6c6 0 11 4.9 11 11v6H4Zm27 0v-6c0-3.2-1-6.1-2.9-8.4A10.8 10.8 0 0 1 33 26h4c4.9 0 9 4 9 9v7H31Z" /></svg>;
  }
  if (type === "check") {
    return <svg {...common}><path d="M10 7h28a4 4 0 0 1 4 4v26a4 4 0 0 1-4 4H10a4 4 0 0 1-4-4V11a4 4 0 0 1 4-4Zm6 17-4 4 8 8 17-17-4-4-13 13-4-4Z" /></svg>;
  }
  if (type === "alert") {
    return <svg {...common}><path d="M24 5 45 42H3L24 5Zm-3 13v12h6V18h-6Zm0 15v6h6v-6h-6Z" /></svg>;
  }
  if (type === "tools") {
    return <svg {...common}><path d="M35.5 6a11 11 0 0 0-13.7 13.7L7 34.5A5.3 5.3 0 1 0 14.5 42l14.8-14.8A11 11 0 0 0 43 13.5l-7 7-8.5-8.5 8-6Z" /></svg>;
  }
  if (type === "report") {
    return <svg {...common}><path d="M10 5h20l9 9v29H10V5Zm19 4v7h7l-7-7ZM16 24h17v5H16v-5Zm0 9h17v5H16v-5Zm0-18h8v5h-8v-5Z" /></svg>;
  }
  if (type === "bars") {
    return <svg {...common}><path d="M7 39h35v4H3V6h4v33Zm6-4h6V23h-6v12Zm11 0h6V14h-6v21Zm11 0h6V8h-6v27Z" /></svg>;
  }
  return <svg {...common}><path d="M8 8h32v32H8z" /></svg>;
}

export default function Summary({ data, onNavigate, year, month }) {
  if (!data) return <section className="v2-panel" role="status">Cargando Panel de control del período…</section>;
  const s = data?.summary || {};
  const workload = data?.workload || {};
  const progress = data?.tracking_progress || {};
  const pmpPending = number(workload.pmp_pending_count);
  const backlogAvailable = number(workload.backlog_available_count);
  const totalToProgram = number(workload.total_pending_count);
  const progressPct = Math.max(0, Math.min(100, number(progress.progress_pct)));
  const finalizedOrders = number(progress.finalized_orders);
  const scheduledFinalizedOrders = number(progress.scheduled_finalized_orders);
  const unplannedFinalizedOrders = number(progress.unplanned_finalized_orders);
  const totalOrders = number(progress.total_orders);
  const pendingOrders = Math.max(0, number(progress.pending_orders));
  const pmpOrders = number(progress.pmp_orders);
  const backlogOrders = number(progress.backlog_orders);
  const totalWorkloadHh = number(progress.total_workload_hh);
  const finalizedWorkloadHh = number(progress.finalized_workload_hh);
  const pendingWorkloadHh = number(progress.pending_workload_hh);
  const progressHhPct = Math.max(0, Math.min(100, number(progress.progress_hh_pct)));

  const quickActions = [
    {
      id: "advanceStops",
      title: "Preparar paradas",
      text: "Identificar y preparar actividades con equipo detenido",
      icon: "calendar",
    },
    {
      id: "technicians",
      title: "Programación de técnicos",
      text: "Turnos, especialidades y H-H disponibles",
      icon: "team",
    },
    {
      id: "programming",
      title: "Programación semanal",
      text: "Seleccionar PMP y Backlog según capacidad",
      icon: "tools",
    },
    {
      id: "tracking",
      title: "Seguimiento de programación",
      text: "Actualizar avance y detectar órdenes finalizadas",
      icon: "report",
    },
  ];

  return (
    <div className="v2-stack v2-control-dashboard">
      <div className="v2-control-counter-heading">
        <span>CONTADORES DINÁMICOS</span>
        <small>Los dos primeros disminuyen a medida que avanzas la programación. Técnicos muestra la capacidad mensual disponible para preventivo.</small>
      </div>

      <section className="v2-control-primary v2-control-primary-3">
        <article>
          <div className="v2-control-icon"><ControlIcon type="report" /></div>
          <div>
            <span>PMP PARA PROGRAMAR</span>
            <strong>{totalToProgram}</strong>
            <small>{pmpPending} PMP + {backlogAvailable} Backlog disponibles</small>
            <small className="v2-control-total-ref">Total de referencia: {totalOrders} actividades</small>
          </div>
        </article>

        <article className="workload">
          <div className="v2-control-icon"><ControlIcon type="clock" /></div>
          <div>
            <span>H-H ESTIMADAS PMP + BACKLOG</span>
            <strong>{fmt(workload.total_pending_hh, 1)}</strong>
            <small>PMP pendiente + Backlog disponible</small>
            <small className="v2-control-total-ref">Total de referencia: {fmt(totalWorkloadHh, 1)} H-H</small>
          </div>
        </article>

        <article>
          <div className="v2-control-icon"><ControlIcon type="team" /></div>
          <div>
            <span>H-H TÉCNICOS PROGRAMACIÓN</span>
            <strong>{fmt(s.hh_tecnicos_preventivo_mes, 1)}</strong>
            <small>H-H disponibles para preventivo (80% efectivo × 80% preventivo)</small>
            <small className="v2-control-total-ref">H-H brutas del mes: {fmt(s.hh_tecnicos_mes, 1)}</small>
          </div>
        </article>
      </section>

      <section className="v2-control-body v2-control-body-main">
        <div className="v2-control-shortcuts v2-control-shortcuts-main">
          <div className="v2-control-panel-head">
            <div>
              <span className="v2-kicker">FLUJO DE TRABAJO</span>
              <h3>Procesos principales</h3>
            </div>
          </div>

          <div className="v2-control-action-list v2-control-action-list-main">
            {quickActions.map((action, index) => (
              <button
                type="button"
                key={action.id}
                className="v2-control-action-button"
                onClick={() => onNavigate(action.id)}
              >
                <span className="v2-control-action-step">{String(index + 1).padStart(2, "0")}</span>
                <span className="v2-control-action-icon"><ControlIcon type={action.icon} /></span>
                <span className="v2-control-action-copy">
                  <b>{action.title}</b>
                  <small>{action.text}</small>
                </span>
                <span className="v2-control-arrow">→</span>
              </button>
            ))}

            <article className="v2-control-action-card v2-control-action-close v2-control-action-close-wide">
              <div className="v2-control-action-main">
                <span className="v2-control-action-step">05</span>
                <span className="v2-control-action-icon"><ControlIcon type="check" /></span>
                <span className="v2-control-action-copy">
                  <b>Cierre de programa</b>
                  <small>Formalizar el resultado semanal o consolidar el período completo</small>
                </span>
              </div>
              <div className="v2-control-close-options">
                <button type="button" onClick={() => onNavigate("closure")}>
                  <span>Cierre semanal</span>
                  <b>→</b>
                </button>
                <button type="button" onClick={() => onNavigate("monthly")}>
                  <span>Cierre mensual</span>
                  <b>→</b>
                </button>
              </div>
            </article>
          </div>
        </div>

        <button
          type="button"
          className="v2-dashboard-progress-card"
          onClick={() => onNavigate("indicators")}
          aria-label="Abrir Indicadores y seguimiento"
        >
          <div className="v2-dashboard-progress-head">
            <div>
              <span className="v2-kicker">AVANCE GENERAL</span>
              <h3>Indicadores y seguimiento</h3>
            </div>
            <span className="v2-dashboard-progress-arrow">→</span>
          </div>

          <div className="v2-dashboard-progress-dual">
            <div className="v2-dashboard-progress-unit">
              <div
                className="v2-dashboard-progress-ring"
                style={{ "--progress-angle": `${progressPct * 3.6}deg` }}
              >
                <div>
                  <strong>{fmt(progressPct, 1)}%</strong>
                  <span>avance OT</span>
                </div>
              </div>
              <div className="v2-dashboard-progress-unit-copy">
                <strong>{finalizedOrders} de {totalOrders}</strong>
                <small>órdenes finalizadas</small>
              </div>
            </div>

            <div className="v2-dashboard-progress-unit">
              <div
                className="v2-dashboard-progress-ring v2-dashboard-progress-ring-hh"
                style={{ "--progress-angle": `${progressHhPct * 3.6}deg` }}
              >
                <div>
                  <strong>{fmt(progressHhPct, 1)}%</strong>
                  <span>avance H-H</span>
                </div>
              </div>
              <div className="v2-dashboard-progress-unit-copy">
                <strong>{fmt(finalizedWorkloadHh, 1)} de {fmt(totalWorkloadHh, 1)}</strong>
                <small>H-H estimadas finalizadas del mes</small>
              </div>
            </div>
          </div>

          <div className="v2-dashboard-progress-stats">
            <span><b>{finalizedOrders}</b><small>OT finalizadas</small></span>
            <span><b>{pendingOrders}</b><small>OT pendientes</small></span>
            <span><b>{totalOrders}</b><small>Total OT</small></span>
          </div>

          <div className="v2-dashboard-progress-stats v2-dashboard-progress-stats-hh">
            <span><b>{fmt(finalizedWorkloadHh, 1)}</b><small>H-H finalizadas</small></span>
            <span><b>{fmt(pendingWorkloadHh, 1)}</b><small>H-H pendientes</small></span>
            <span><b>{fmt(totalWorkloadHh, 1)}</b><small>Total H-H mes</small></span>
          </div>

          <div className="v2-dashboard-progress-source">
            <span><b>{pmpOrders}</b> PMP del mes</span>
            <span><b>{backlogOrders}</b> Backlog</span>
            <span><b>{unplannedFinalizedOrders}</b> finalizadas fuera de programación</span>
          </div>
          <small className="tf-portfolio-count-note">Cada actividad o registro de la cartera se cuenta una vez; una OT puede tener varias actividades y varias programaciones.</small>
        </button>
      </section>
    </div>
  );
}


