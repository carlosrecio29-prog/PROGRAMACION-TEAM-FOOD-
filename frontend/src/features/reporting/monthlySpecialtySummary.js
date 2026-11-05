/**
 * El cierre mensual debe mostrar el mismo KPI de OT únicas que el tablero
 * de avance, sin mezclarlo con el recuento de asignaciones semanales.
 * Se reutilizan los cálculos del backend sin volver a calcular porcentajes.
 */
export function buildMonthlySpecialtySummary(progress = {}, names = {}) {
  const weekly = progress.specialties || [];
  const monthly = progress.monthly_progress_by_specialty || [];
  const weeklyByCode = new Map(weekly.map((row) => [row.especialidad, row]));
  const monthlyByCode = new Map(monthly.map((row) => [row.especialidad, row]));
  const codes = [
    ...weekly.map((row) => row.especialidad),
    ...monthly.filter((row) => Number(row.total_ot || 0) > 0).map((row) => row.especialidad),
  ];

  return [...new Set(codes)].map((code) => ({
    especialidad: code,
    name: names[code] || monthlyByCode.get(code)?.name || weeklyByCode.get(code)?.name || code,
    monthly: monthlyByCode.get(code) || null,
    weekly: weeklyByCode.get(code) || null,
  }));
}
