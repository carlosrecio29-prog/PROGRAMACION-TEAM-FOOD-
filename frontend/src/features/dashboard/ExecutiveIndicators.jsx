const count = value => value == null ? "—" : Number(value).toLocaleString("es-CO", {maximumFractionDigits: 0});
const percent = value => value == null ? "—" : `${Number(value).toLocaleString("es-CO", {maximumFractionDigits: 1})}%`;

export default function ExecutiveIndicators({data, onNavigate}) {
  const progress = data?.tracking_progress;
  const insights = data?.management_insights;
  const backlog = insights?.backlog;
  const portfolio = data?.portfolio_progress_by_specialty || [];
  if (!data) return <section className="v2-panel" role="status">Cargando indicadores de la cartera…</section>;
  const items = [
    ["Actividades de cartera", progress?.total_orders, "Registros del período: PMP y backlog de referencia.", "pmp", "Ver cartera"],
    ["Actividades finalizadas", progress?.finalized_orders, `${percent(progress?.progress_pct)} de avance de la cartera.`, "tracking", "Ver seguimiento"],
    ["Actividades pendientes", progress?.pending_orders, "Pendientes de la cartera mensual.", "programming", "Programar semana"],
    ["Excluidas por operación", insights?.operation_excluded_count, "Separadas del cumplimiento de mantenimiento.", "operationExclusions", "Ver exclusiones"],
    ["Sin H-H calculables", insights?.missing_hh_count, "Revisar los datos necesarios para dimensionar la carga.", "pending", "Completar datos"],
    ["Finalizadas sin fecha real", insights?.unknown_completion_date_count, "La finalización no acredita una fecha real de ejecución.", "tracking", "Revisar fuente"],
  ];
  return <div className="v2-stack">
    <section className="v2-panel">
      <div className="v2-section-head"><div><span className="v2-kicker">ACTIVIDADES DE LA CARTERA DEL MES</span><h3>Lectura ejecutiva</h3><p>Misma base y criterio que el Panel de control.</p></div></div>
      <div className="tf-insight-grid">{items.map(([label, value, detail, route, action]) => <article key={label}><span>{label}</span><strong>{count(value)}</strong><small>{detail}</small><button type="button" onClick={() => onNavigate(route)}>{action} →</button></article>)}</div>
      <p className="tf-scope-note">Cada actividad de la cartera se cuenta una vez; una OT puede tener varias actividades y varias programaciones. El cumplimiento semanal cuenta ejecuciones. Las H-H son estimadas; no representan horas reales trabajadas.</p>
      <div className="v2-table-wrap" tabIndex={0} role="region" aria-label="Cartera por especialidad"><table><thead><tr><th>Especialidad</th><th>Actividades</th><th>Finalizadas</th><th>Pendientes</th><th>Avance</th></tr></thead><tbody>{portfolio.map(row => <tr key={row.especialidad}><td><b>{row.name || row.especialidad}</b></td><td>{count(row.total_orders)}</td><td>{count(row.finalized_orders)}</td><td>{count(row.pending_orders)}</td><td>{percent(row.progress_pct)}</td></tr>)}{!portfolio.length && <tr><td colSpan={5} className="v2-empty">Sin desglose de cartera para este período.</td></tr>}</tbody></table></div>
    </section>
    <section className="v2-panel"><div className="v2-section-head"><div><span className="v2-kicker">BACKLOG ACTIVO ACTUAL · TODOS LOS PERÍODOS</span><h3>Prioridad y antigüedad</h3><p>La cola acumulada es independiente del mes seleccionado.{insights?.as_of ? ` Corte: ${insights.as_of}.` : ""}</p></div></div>
      <div className="tf-insight-grid tf-insight-grid-backlog">{[["Activas", backlog?.active_count], ["Disponibles", backlog?.available_count], ["Programadas", backlog?.scheduled_count], ["Prioridad A", backlog?.critical_a_count], ["Hasta 30 días", backlog?.aging_buckets?.up_to_30], ["31 a 60 días", backlog?.aging_buckets?.days_31_60], ["61 a 90 días", backlog?.aging_buckets?.days_61_90], ["Más de 90 días", backlog?.aging_buckets?.over_90]].map(([label, value]) => <article key={label}><span>{label}</span><strong>{count(value)}</strong></article>)}</div>
      <button type="button" className="v2-primary" onClick={() => onNavigate("backlog")}>Revisar cola de trabajo →</button>
    </section>
  </div>;
}


