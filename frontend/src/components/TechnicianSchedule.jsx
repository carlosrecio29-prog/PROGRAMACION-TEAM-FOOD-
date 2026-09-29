import { useEffect, useMemo, useState } from "react";
import {
  getTechnicianSchedule,
  saveTechnicianSchedule,
  uploadV2TechnicianSchedule,
  saveV2TechnicianComplement,
} from "../api";
import Badge from "../shared/Badge";

const SPEC_NAMES = {
  MEC: "Mecánica",
  ELE: "Eléctrica",
  MET: "Metrología",
  SER: "Servicios",
};
const SPECS = ["MEC", "ELE", "MET", "SER"];
const DAY_NAMES = ["DO", "LU", "MA", "MI", "JU", "VI", "SA"];

function fmt(value, digits = 1) {
  const n = Number(value || 0);
  return Number.isFinite(n)
    ? n.toLocaleString("es-CO", {
        minimumFractionDigits: digits,
        maximumFractionDigits: digits,
      })
    : "0";
}

function isoDate(year, month, day) {
  return `${year}-${String(month).padStart(2, "0")}-${String(day).padStart(2, "0")}`;
}

function shiftTone(code) {
  if (!code) return "";
  if (code === "T1") return "t1";
  if (code === "T2") return "t2";
  if (code === "T3") return "t3";
  if (code === "T-12") return "t12";
  if (code === "T-37") return "t37";
  if (code === "T-56") return "t56";
  return "absence";
}

export default function TechnicianSchedule({ year, month, onChanged }) {
  const [data, setData] = useState(null);
  const [draft, setDraft] = useState({});
  const [loading, setLoading] = useState(true);
  const [saving, setSaving] = useState(false);
  const [message, setMessage] = useState("");
  const [error, setError] = useState("");
  const [file, setFile] = useState(null);
  const [uploading, setUploading] = useState(false);
  const [specialtyDraft, setSpecialtyDraft] = useState({});
  const [savingSpecialty, setSavingSpecialty] = useState(null);

  const days = useMemo(
    () => Array.from({ length: new Date(year, month, 0).getDate() }, (_, index) => index + 1),
    [year, month],
  );

  async function load() {
    try {
      setLoading(true);
      setError("");
      const result = await getTechnicianSchedule(year, month);
      setData(result);
      setDraft({});
    } catch (cause) {
      setError(cause.message || "No se pudo cargar la programación de técnicos.");
    } finally {
      setLoading(false);
    }
  }

  useEffect(() => {
    load();
  }, [year, month]);

  function currentValue(technicianId, day) {
    const date = isoDate(year, month, day);
    const key = `${technicianId}|${date}`;
    if (Object.prototype.hasOwnProperty.call(draft, key)) return draft[key];
    return data?.schedule?.[String(technicianId)]?.[date]?.shift_code || "";
  }

  function setValue(technicianId, day, value) {
    const date = isoDate(year, month, day);
    const key = `${technicianId}|${date}`;
    const original = data?.schedule?.[String(technicianId)]?.[date]?.shift_code || "";
    setDraft((current) => {
      const next = { ...current };
      if (value === original) delete next[key];
      else next[key] = value;
      return next;
    });
    setMessage("");
  }

  async function saveChanges() {
    const changes = Object.entries(draft).map(([key, shiftCode]) => {
      const [technicianId, workDate] = key.split("|");
      return {
        technician_id: Number(technicianId),
        work_date: workDate,
        shift_code: shiftCode || null,
      };
    });
    if (!changes.length) return;

    try {
      setSaving(true);
      setError("");
      const result = await saveTechnicianSchedule(changes);
      setMessage(
        `${result.updated} asignaciones actualizadas${result.cleared ? ` · ${result.cleared} eliminadas` : ""}. La disponibilidad quedó recalculada.`,
      );
      await load();
      onChanged?.();
    } catch (cause) {
      setError(cause.message || "No se pudieron guardar los cambios.");
    } finally {
      setSaving(false);
    }
  }

  async function importExcel() {
    if (!file) return;
    try {
      setUploading(true);
      setError("");
      const result = await uploadV2TechnicianSchedule(file, year, month);
      setMessage(
        `Excel importado: ${result.registros || result.registros_archivo || 0} registros · ${fmt(result.hh_disponibles, 1)} H-H disponibles.`,
      );
      setFile(null);
      await load();
      onChanged?.();
    } catch (cause) {
      setError(cause.message || "No se pudo importar el Excel.");
    } finally {
      setUploading(false);
    }
  }

  async function saveSpecialty(technician) {
    const specialty = specialtyDraft[technician.id];
    if (!specialty) return;
    try {
      setSavingSpecialty(technician.id);
      setError("");
      await saveV2TechnicianComplement(technician.id, specialty);
      setSpecialtyDraft((current) => {
        const next = { ...current };
        delete next[technician.id];
        return next;
      });
      await load();
      onChanged?.();
    } catch (cause) {
      setError(cause.message || "No se pudo guardar la especialidad.");
    } finally {
      setSavingSpecialty(null);
    }
  }

  const changeCount = Object.keys(draft).length;
  const missingSpecialty = (data?.technicians || []).filter((technician) => !technician.especialidad);

  return (
    <div className="v2-stack technician-planning">
      <section className="v2-panel technician-planning-head">
        <div className="v2-section-head">
          <div>
            <span className="v2-kicker">PLANIFICACIÓN DE PERSONAL</span>
            <h3>Programación mensual de técnicos</h3>
            <p>
              Modifica los turnos directamente en la matriz. Los cambios se guardan por técnico y fecha,
              por lo que puedes actualizar el mes tantas veces como sea necesario.
            </p>
          </div>
          <Badge tone={changeCount ? "warn" : "ok"}>
            {changeCount ? `${changeCount} cambio${changeCount === 1 ? "" : "s"} sin guardar` : "Sin cambios pendientes"}
          </Badge>
        </div>

        <div className="technician-planning-actions">
          <button
            type="button"
            className="v2-primary"
            disabled={!changeCount || saving}
            onClick={saveChanges}
          >
            {saving ? "Guardando..." : `Guardar cambios (${changeCount})`}
          </button>
          <button type="button" disabled={!changeCount || saving} onClick={() => setDraft({})}>
            Descartar cambios
          </button>
          <button type="button" disabled={loading || saving} onClick={load}>
            Actualizar
          </button>
        </div>

        {error && <div className="v2-error">{error}</div>}
        {message && <div className="v2-success">{message}</div>}
      </section>

      <section className="v2-panel technician-capacity-summary">
        <div className="v2-section-head">
          <div>
            <span className="v2-kicker">CAPACIDAD DEL MES</span>
            <h3>Regla de disponibilidad por especialidad</h3>
            <p>
              100% H-H → 80% capacidad efectiva → de esa capacidad: 80% preventivo y 20% correctivo.
            </p>
          </div>
        </div>
        <div className="technician-capacity-grid">
          {(data?.specialties || []).map((row) => (
            <article key={row.specialty}>
              <div>
                <Badge>{SPEC_NAMES[row.specialty] || row.specialty}</Badge>
              </div>
              <dl>
                <div><dt>H-H netas</dt><dd>{fmt(row.available)}</dd></div>
                <div><dt>Capacidad efectiva · 80%</dt><dd>{fmt(row.effective)}</dd></div>
                <div className="preventive"><dt>Preventivo · 80%</dt><dd>{fmt(row.preventive)}</dd></div>
                <div className="corrective"><dt>Correctivo · 20%</dt><dd>{fmt(row.corrective)}</dd></div>
                <div><dt>Margen inicial · 20%</dt><dd>{fmt(row.initial_margin)}</dd></div>
              </dl>
            </article>
          ))}
        </div>
      </section>

      <section className="v2-panel">
        <div className="v2-section-head technician-grid-title">
          <div>
            <span className="v2-kicker">MATRIZ MENSUAL</span>
            <h3>{String(month).padStart(2, "0")}/{year}</h3>
            <p>Selecciona un turno o ausencia en cada día. Una celda vacía significa programación no definida.</p>
          </div>
          <span className="technician-grid-help">Desplázate horizontalmente para ver todo el mes →</span>
        </div>

        {loading && !data ? (
          <div className="v2-empty">Cargando técnicos y turnos...</div>
        ) : (
          <div className="technician-grid-wrap">
            <table className="technician-grid">
              <thead>
                <tr>
                  <th className="sticky-col tech-col">Técnico</th>
                  <th className="sticky-col specialty-col">Esp.</th>
                  {days.map((day) => {
                    const weekday = new Date(year, month - 1, day).getDay();
                    return (
                      <th key={day} className={weekday === 0 ? "sunday" : weekday === 6 ? "saturday" : ""}>
                        <span>{DAY_NAMES[weekday]}</span>
                        <b>{String(day).padStart(2, "0")}</b>
                      </th>
                    );
                  })}
                  <th className="month-total">H-H mes</th>
                </tr>
              </thead>
              <tbody>
                {(data?.technicians || []).map((technician) => (
                  <tr key={technician.id}>
                    <td className="sticky-col tech-col">
                      <b>{technician.nombre}</b>
                      <small>{technician.identificacion || ""}</small>
                    </td>
                    <td className="sticky-col specialty-col">
                      {technician.especialidad ? (
                        <span className="tech-specialty">{technician.especialidad}</span>
                      ) : (
                        <span className="tech-specialty missing">—</span>
                      )}
                    </td>
                    {days.map((day) => {
                      const value = currentValue(technician.id, day);
                      const weekday = new Date(year, month - 1, day).getDay();
                      return (
                        <td
                          key={day}
                          className={`shift-cell ${weekday === 0 ? "sunday" : ""} ${shiftTone(value)}`}
                        >
                          <select
                            value={value}
                            onChange={(event) => setValue(technician.id, day, event.target.value)}
                            aria-label={`${technician.nombre}, día ${day}`}
                          >
                            <option value="">—</option>
                            {(data?.shifts || []).map((shift) => (
                              <option key={shift.codigo} value={shift.codigo}>
                                {shift.codigo}
                              </option>
                            ))}
                          </select>
                        </td>
                      );
                    })}
                    <td className="month-total"><b>{fmt(technician.hh_mes)}</b></td>
                  </tr>
                ))}
              </tbody>
            </table>
          </div>
        )}
      </section>

      {!!missingSpecialty.length && (
        <section className="v2-panel">
          <div className="v2-section-head">
            <div>
              <span className="v2-kicker">DATOS PENDIENTES</span>
              <h3>Técnicos sin especialidad</h3>
              <p>Estos técnicos no aportarán capacidad a una especialidad hasta completar este dato.</p>
            </div>
          </div>
          <div className="technician-specialty-list">
            {missingSpecialty.map((technician) => (
              <div key={technician.id}>
                <span><b>{technician.nombre}</b><small>{technician.identificacion || ""}</small></span>
                <select
                  value={specialtyDraft[technician.id] || ""}
                  onChange={(event) =>
                    setSpecialtyDraft((current) => ({ ...current, [technician.id]: event.target.value }))
                  }
                >
                  <option value="">Especialidad...</option>
                  {SPECS.map((spec) => (
                    <option key={spec} value={spec}>{SPEC_NAMES[spec]}</option>
                  ))}
                </select>
                <button
                  type="button"
                  className="v2-save"
                  disabled={!specialtyDraft[technician.id] || savingSpecialty === technician.id}
                  onClick={() => saveSpecialty(technician)}
                >
                  {savingSpecialty === technician.id ? "Guardando..." : "Guardar"}
                </button>
              </div>
            ))}
          </div>
        </section>
      )}

      <section className="v2-panel technician-excel-backup">
        <div>
          <span className="v2-kicker">RESPALDO</span>
          <h3>Importar programación desde Excel</h3>
          <p>
            La programación directa en la aplicación es el método principal. El Excel queda disponible
            para recibir una programación externa o recuperar un mes.
          </p>
        </div>
        <div className="technician-excel-actions">
          <input
            type="file"
            accept=".xlsx"
            onChange={(event) => setFile(event.target.files?.[0] || null)}
          />
          <button type="button" disabled={!file || uploading} onClick={importExcel}>
            {uploading ? "Importando..." : "Importar Excel"}
          </button>
        </div>
      </section>
    </div>
  );
}
