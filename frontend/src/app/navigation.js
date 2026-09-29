export const MONTHS = [
  "Enero", "Febrero", "Marzo", "Abril", "Mayo", "Junio",
  "Julio", "Agosto", "Septiembre", "Octubre", "Noviembre", "Diciembre",
];

export const VIEW_META = {
  summary: ["Panel de control", "Estado operativo y accesos rápidos del período."],
  indicators: ["Indicadores y seguimiento", "Seguimiento del período, tendencia semanal, especialidades y exportación."],
  programming: ["Programación semanal", "Programa por capacidad, condición y origen de las OT."],
  advanceStops: ["Preparación de paradas", "Revisa el calendario provisional del mes siguiente y exporta las actividades con equipo detenido."],
  pmp: ["PMP del mes", "Cartera preventiva exportada desde el software de mantenimiento."],
  operationExclusions: ["Actividades excluidas", "Consulta los planes y registros retirados del PMP por corresponder a OPERACIÓN."],
  closure: ["Cierre semanal", "Reconcilia la programación contra el estado verificado del software."],
  monthly: ["Cierre mensual", "Valida semanas, consolida resultados, gestiona pendientes y formaliza el cierre del período."],
  backlog: ["Backlog acumulado", "OT pendientes conservadas hasta confirmar su finalización."],
  pending: ["Completar datos", "Completa sólo los datos que faltan en los planes del periodo."],
  technicians: ["Programación de técnicos", "Programa turnos, ausencias y disponibilidad mensual del personal."],
  imports: ["Actualizar base", "Carga los Excel del software de mantenimiento en un único lugar."],
};

export const NAV_GROUPS = [
  { label: "Inicio", items: [{ id: "summary", label: "Panel de control", code: "PC" }] },
  { label: "Planificación", items: [
    { id: "advanceStops", label: "Preparación de paradas", code: "PA" },
    { id: "technicians", label: "Programación de técnicos", code: "TE", indicator: "technicians" },
    { id: "programming", label: "Programación semanal", code: "PS" },
    { id: "pmp", label: "PMP del mes", code: "PM" },
    { id: "operationExclusions", label: "Actividades excluidas", code: "OP" },
  ] },
  { label: "Cierre", items: [
    { id: "closure", label: "Cierre semanal", code: "CI" },
    { id: "monthly", label: "Cierre mensual", code: "CM" },
  ] },
  { label: "Backlog", items: [{ id: "backlog", label: "Seguimiento acumulado", code: "BL" }] },
  { label: "Administración", items: [
    { id: "imports", label: "Cargar Excel", code: "EX" },
    { id: "pending", label: "Completar datos", code: "CD", indicator: "pending" },
  ] },
];

export function navigationIds(groups = NAV_GROUPS) {
  return [...groups.flatMap((group) => group.items.map((item) => item.id)), "indicators"];
}
