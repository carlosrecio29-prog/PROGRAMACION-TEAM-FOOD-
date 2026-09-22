async function check(res) {
  if (!res.ok) {
    let detail = `HTTP ${res.status}`;
    try {
      const b = await res.json();
      detail = b.detail || JSON.stringify(b);
    } catch {}
    throw new Error(detail);
  }
  return res.json();
}
export async function uploadFile(path, file, params = {}) {
  const qs = new URLSearchParams();
  Object.entries(params).forEach(([k, v]) => {
    if (v !== undefined && v !== null && v !== "") qs.set(k, v);
  });
  const form = new FormData();
  form.append("file", file);
  return check(
    await fetch(`${path}${qs.size ? `?${qs}` : ""}`, {
      method: "POST",
      body: form,
    }),
  );
}
export async function getCapacity(dateFrom, dateTo) {
  return check(
    await fetch(
      `/api/capacity?${new URLSearchParams({ date_from: dateFrom, date_to: dateTo })}`,
    ),
  );
}
export async function getCandidates(filters) {
  const qs = new URLSearchParams();
  Object.entries(filters).forEach(([k, v]) => {
    if (v !== undefined && v !== null && v !== "") qs.set(k, v);
  });
  return check(await fetch(`/api/candidates?${qs}`));
}
export async function getMasterStatus() {
  return check(await fetch("/api/master-status"));
}
export async function learnPlan(planId, payload) {
  return check(
    await fetch(`/api/plans/${planId}/learn`, {
      method: "POST",
      headers: { "Content-Type": "application/json" },
      body: JSON.stringify(payload),
    }),
  );
}
export async function saveProgramming(payload) {
  return check(
    await fetch("/api/programming", {
      method: "POST",
      headers: { "Content-Type": "application/json" },
      body: JSON.stringify(payload),
    }),
  );
}
export async function getProgrammingHistory(limit = 50) {
  return check(await fetch(`/api/programming/history?limit=${limit}`));
}
export async function getProgrammingVersion(versionId) {
  return check(await fetch(`/api/programming/version/${versionId}`));
}
export async function closeProgramming(payload) {
  return check(
    await fetch("/api/programming/close", {
      method: "POST",
      headers: { "Content-Type": "application/json" },
      body: JSON.stringify(payload),
    }),
  );
}

export async function getHealth() {
  return check(await fetch("/api/health"));
}

export async function getMonthReconciliation(year, month) {
  return check(
    await fetch(
      `/api/month-reconciliation?${new URLSearchParams({ year, month })}`,
    ),
  );
}
export async function getMonthSummary(year, month) {
  return check(
    await fetch(`/api/month-summary?${new URLSearchParams({ year, month })}`),
  );
}

export async function downloadProgrammingExport(versionId, format) {
  const res = await fetch(
    `/api/programming/version/${versionId}/export.${format}`,
  );
  if (!res.ok) {
    let detail = `HTTP ${res.status}`;
    try {
      const b = await res.json();
      detail = b.detail || JSON.stringify(b);
    } catch {}
    throw new Error(detail);
  }
  const blob = await res.blob();
  const disposition = res.headers.get("content-disposition") || "";
  const match = disposition.match(/filename="?([^";]+)"?/i);
  const filename = match?.[1] || `programacion.${format}`;
  const url = URL.createObjectURL(blob);
  const a = document.createElement("a");
  a.href = url;
  a.download = filename;
  document.body.appendChild(a);
  a.click();
  a.remove();
  URL.revokeObjectURL(url);
}

export async function resetTestingData() {
  return check(
    await fetch("/api/testing/reset", {
      method: "POST",
      headers: { "Content-Type": "application/json" },
      body: JSON.stringify({ confirmation: "REINICIAR PRUEBAS" }),
    }),
  );
}

export async function getPendingDefinitions(year, month, specialty = "") {
  const qs = new URLSearchParams({ year, month });
  if (specialty) qs.set("specialty", specialty);
  return check(await fetch(`/api/definitions/pending?${qs}`));
}
export async function savePlanDefinition(planId, payload) {
  return check(
    await fetch(`/api/definitions/plans/${planId}`, {
      method: "POST",
      headers: { "Content-Type": "application/json" },
      body: JSON.stringify(payload),
    }),
  );
}

export async function getV2Dashboard(year = 2026, month = 9) {
  return check(
    await fetch(`/api/v2/dashboard?${new URLSearchParams({ year, month })}`),
  );
}
export async function getV2PendingPlans(
  year = 2026,
  month = 9,
  specialty = "",
) {
  const qs = new URLSearchParams({ year, month });
  if (specialty) qs.set("specialty", specialty);
  return check(await fetch(`/api/v2/pending-plans?${qs}`));
}
export async function saveV2PlanComplement(planId, payload) {
  return check(
    await fetch(`/api/v2/plans/${planId}`, {
      method: "PATCH",
      headers: { "Content-Type": "application/json" },
      body: JSON.stringify(payload),
    }),
  );
}
export async function getV2Technicians(year = 2026, month = 9) {
  return check(
    await fetch(`/api/v2/technicians?${new URLSearchParams({ year, month })}`),
  );
}
export async function saveV2TechnicianComplement(technicianId, specialty) {
  return check(
    await fetch(`/api/v2/technicians/${technicianId}`, {
      method: "PATCH",
      headers: { "Content-Type": "application/json" },
      body: JSON.stringify({ specialty }),
    }),
  );
}
export async function getV2Pmp({
  year = 2026,
  month = 9,
  specialty = "",
  area = "",
  search = "",
  limit = 300,
} = {}) {
  const qs = new URLSearchParams({ year, month, limit });
  if (specialty) qs.set("specialty", specialty);
  if (area) qs.set("area", area);
  if (search) qs.set("search", search);
  return check(await fetch(`/api/v2/pmp?${qs}`));
}

export async function getV2WeekProgramming(dateFrom, dateTo, specialty) {
  const qs = new URLSearchParams({
    date_from: dateFrom,
    date_to: dateTo,
    specialty,
  });
  return check(await fetch(`/api/v2/programming/week?${qs}`));
}
export async function saveV2WeekProgramming(payload) {
  return check(
    await fetch("/api/v2/programming", {
      method: "POST",
      headers: { "Content-Type": "application/json" },
      body: JSON.stringify(payload),
    }),
  );
}
export async function getV2Backlog(filters = {}) {
  const qs = new URLSearchParams();
  Object.entries(filters).forEach(([key, value]) => {
    if (value !== undefined && value !== null && value !== "")
      qs.set(key, value);
  });
  return check(await fetch(`/api/v2/backlog?${qs}`));
}
export async function previewAdvanceStops(file, year, month, signal) {
  const form = new FormData();
  form.append("monthly", file);
  const params = new URLSearchParams({ year, month });
  return check(await fetch(`/api/v2/advance-stops/preview?${params}`, {
    method: "POST",
    body: form,
    signal,
  }));
}

export async function downloadAdvanceStopsExcel(file, year, month) {
  const form = new FormData();
  form.append("monthly", file);
  const params = new URLSearchParams({ year, month });
  const response = await fetch(`/api/v2/advance-stops/export.xlsx?${params}`, {
    method: "POST",
    body: form,
  });
  if (!response.ok) {
    let detail = `HTTP ${response.status}`;
    try {
      const payload = await response.json();
      detail = payload.detail || detail;
    } catch {}
    throw new Error(detail);
  }
  const blob = await response.blob();
  if (!blob.size) throw new Error("El servidor no devolvió el Excel solicitado.");
  const objectUrl = URL.createObjectURL(blob);
  const disposition = response.headers.get("content-disposition") || "";
  const name = disposition.match(/filename="?([^";]+)"?/i)?.[1]
    || `anticipacion_paradas_${year}_${String(month).padStart(2,"0")}.xlsx`;
  const link = document.createElement("a");
  link.href = objectUrl;
  link.download = name;
  document.body.appendChild(link);
  link.click();
  link.remove();
  window.setTimeout(() => URL.revokeObjectURL(objectUrl), 60000);
}

export async function getV2Progress(year = 2026, month = 9) {
  return check(await fetch(`/api/v2/progress?${new URLSearchParams({year,month})}`));
}

export function getV2ProgressPdfUrl(year, month, programmingId = null) {
  const params = new URLSearchParams({ year, month });
  if (programmingId !== null && programmingId !== undefined) {
    params.set("programming_id", programmingId);
  }
  return `/api/v2/progress/report.pdf?${params}`;
}

export async function downloadV2ProgressPdf(year, month, programmingId = null) {
  const url = getV2ProgressPdfUrl(year, month, programmingId);
  // Validar la respuesta antes de activar la descarga; así un 500 no queda
  // oculto ni se entrega como archivo PDF vacío.
  const res = await fetch(url, { cache: "no-store" });
  if (!res.ok) {
    let message = `HTTP ${res.status}`;
    try { const body = await res.json(); message = body.detail || message; } catch {}
    throw new Error(message);
  }
  const blob = await res.blob();
  if (blob.size < 8 || !blob.type.includes("pdf")) {
    throw new Error("El servidor no devolvió un PDF válido. Usa 'Abrir PDF directamente' para diagnosticarlo.");
  }
  const disposition = res.headers.get("content-disposition") || "";
  const match = disposition.match(/filename="?([^";]+)"?/i);
  const filename = match?.[1] || `informe_mtto_${year}_${month}.pdf`;
  const objectUrl = URL.createObjectURL(blob);
  const link = document.createElement("a");
  link.href = objectUrl;
  link.download = filename;
  document.body.appendChild(link);
  link.click();
  link.remove();
  // Revocar de inmediato puede cancelar la descarga en algunos navegadores.
  window.setTimeout(() => URL.revokeObjectURL(objectUrl), 60000);
}

export async function getV2WeekClosure(programmingId) {
  return check(await fetch(`/api/v2/programming/${programmingId}/closure`));
}
export async function previewV2WeekClosure(programmingId, file) {
  const form = new FormData();
  form.append("file", file);
  return check(await fetch(`/api/v2/programming/${programmingId}/preview-close-file`, {
    method: "POST",
    body: form,
  }));
}

export async function uploadV2WeekClosure(
  programmingId,
  file,
  closedBy = "",
) {
  const qs = new URLSearchParams();
  if (closedBy) qs.set("closed_by", closedBy);
  const form = new FormData();
  form.append("file", file);
  return check(
    await fetch(`/api/v2/programming/${programmingId}/close-file${qs.size ? `?${qs}` : ""}`, {
      method: "POST",
      body: form,
    }),
  );
}

export async function downloadV2WeeklyReport(programmingId, format = "pdf") {
  const res = await fetch(
    `/api/v2/programming/${programmingId}/export.${format}`,
  );
  if (!res.ok) {
    let detail = `HTTP ${res.status}`;
    try {
      const b = await res.json();
      detail = b.detail || JSON.stringify(b);
    } catch {}
    throw new Error(detail);
  }
  const blob = await res.blob();
  const disposition = res.headers.get("content-disposition") || "";
  const match = disposition.match(/filename="?([^";]+)"?/i);
  const filename = match?.[1] || `programacion_semanal.${format}`;
  const url = URL.createObjectURL(blob);
  const a = document.createElement("a");
  a.href = url;
  a.download = filename;
  document.body.appendChild(a);
  a.click();
  a.remove();
  URL.revokeObjectURL(url);
}
