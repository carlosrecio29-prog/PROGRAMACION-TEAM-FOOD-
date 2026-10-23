import {MONTHS, NAV_GROUPS} from "./navigation";

const GUIDE = {
  summary: ["Consulta la cartera del mes y abre el proceso que necesita atención.", "indicators", "Analizar indicadores"],
  indicators: ["Distingue cartera mensual, ejecuciones semanales y resultados de cierre confirmado.", "tracking", "Revisar seguimiento"],
  pmp: ["Revisa la cartera importada; completa los datos pendientes antes de programar.", "pending", "Completar datos"],
  advanceStops: ["Prepara las actividades con equipo detenido y coordina la ventana de parada.", "programming", "Programar actividades"],
  technicians: ["Define turnos y ausencias para disponer de capacidad antes de asignar órdenes.", "programming", "Programar semana"],
  programming: ["Selecciona la semana y especialidad; asigna PMP y backlog según la capacidad disponible.", "tracking", "Seguir ejecución"],
  tracking: ["Concilia la Lista de Calendario para conocer el avance antes de formalizar el cierre.", "closure", "Preparar cierre semanal"],
  backlog: ["Prioriza pendientes disponibles; consulta finalizadas y anuladas como historial.", "programming", "Programar pendientes"],
  closure: ["Verifica el resultado y las diferencias de cada semana antes de confirmar el cierre.", "monthly", "Revisar cierre mensual"],
  monthly: ["Revisa los cierres semanales, las diferencias y los pendientes antes de formalizar el período.", "indicators", "Consultar resultados"],
  imports: ["Actualiza las fuentes del sistema externo y revisa el resultado de la carga.", "pending", "Revisar datos pendientes"],
  pending: ["Completa los datos manuales que faltan para que los planes puedan programarse.", "pmp", "Consultar cartera PMP"],
  operationExclusions: ["Consulta las actividades de operación separadas de la cartera de mantenimiento y su cumplimiento.", "pmp", "Ver mantenimiento del mes"],
};

export default function WorkflowContext({view, year, month, onNavigate}) {
  const group = NAV_GROUPS.find(item => item.items.some(page => page.id === view));
  const guide = GUIDE[view];
  if (!guide || view === "summary") return null;
  return <section className="tf-workflow-context" aria-label="Contexto de trabajo">
    <div><span className="tf-workflow-step">{group?.label}</span><strong>{MONTHS[month - 1]} {year}</strong>
      {view === "backlog" && <span className="tf-scope-tag">Acumulado · todos los períodos</span>}
      <p>{guide[0]}</p>
    </div>
    <button type="button" onClick={() => onNavigate(guide[1])}>{guide[2]} <span aria-hidden="true">→</span></button>
  </section>;
}
