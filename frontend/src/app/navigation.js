export const MONTHS = [
  "Enero", "Febrero", "Marzo", "Abril", "Mayo", "Junio",
  "Julio", "Agosto", "Septiembre", "Octubre", "Noviembre", "Diciembre",
];

export const VIEW_META = {
  summary: ["Inicio", "Estado operativo y próximos pasos del periodo."],
  programming: ["Programación semanal", "Programa por capacidad, condición y origen de las OT."],
  advanceStops: ["Preparación de paradas", "Revisa el calendario provisional del mes siguiente y exporta las actividades con equipo detenido."],
  pmp: ["PMP del mes", "Cartera preventiva exportada desde el software de mantenimiento."],
  closure: ["Cierre semanal", "Reconcilia la programación contra el estado verificado del software."],
  monthly: ["Cierre mensual", "Avance, cumplimiento, pendientes e informe consolidado del mes."],
  backlog: ["Backlog acumulado", "OT pendientes conservadas hasta confirmar su finalización."],
  pending: ["Completar datos", "Completa sólo los datos que faltan en los planes del periodo."],
  technicians: ["Técnicos", "Personal, turnos, disponibilidad y especialidades."],
  imports: ["Actualizar base", "Carga los Excel del software de mantenimiento en un único lugar."],
};

export const NAV_GROUPS = [
  { label: "Inicio", items: [{ id: "summary", label: "Resumen operativo", code: "IN" }] },
  { label: "Planificación", items: [
    { id: "advanceStops", label: "Preparación de paradas", code: "PA" },
    { id: "programming", label: "Programación semanal", code: "PS" },
    { id: "pmp", label: "PMP del mes", code: "PM" },
  ] },
  { label: "Cierre", items: [
    { id: "closure", label: "Cierre semanal", code: "CI" },
    { id: "monthly", label: "Informe mensual", code: "IM" },
  ] },
  { label: "Backlog", items: [{ id: "backlog", label: "Seguimiento acumulado", code: "BL" }] },
  { label: "Administración", items: [
    { id: "imports", label: "Cargar Excel", code: "EX" },
    { id: "pending", label: "Completar datos", code: "CD", indicator: "pending" },
    { id: "technicians", label: "Técnicos y turnos", code: "TE", indicator: "technicians" },
  ] },
];

export function navigationIds(groups = NAV_GROUPS) {
  return groups.flatMap((group) => group.items.map((item) => item.id));
}
