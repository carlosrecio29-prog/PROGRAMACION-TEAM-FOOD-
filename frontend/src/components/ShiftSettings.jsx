import { useEffect, useState } from "react";
import Badge from "../shared/Badge";

function fmt(value) {
  const n = Number(value);
  return Number.isFinite(n) ? n.toLocaleString("es-CO", { maximumFractionDigits: 2 }) : "0";
}

export default function ShiftSettings({ year, month }) {
  const [rows, setRows] = useState([]);
  const [draft, setDraft] = useState({});
  const [saving, setSaving] = useState("");
  const [loading, setLoading] = useState(false);
  const [error, setError] = useState("");
  const [message, setMessage] = useState("");

  async function load() {
    try {
      setLoading(true);
      setError("");
      const response = await fetch(`/api/v2/shifts?${new URLSearchParams({ year, month })}`);
      const body = await response.json();
      if (!response.ok) throw new Error(body.detail || `HTTP ${response.status}`);
      setRows(body.shifts || []);
    } catch (cause) {
      setError(cause.message);
    } finally {
      setLoading(false);
    }
  }

  useEffect(() => {
    load();
  }, [year, month]);

  function value(row) {
    return draft[row.codigo] ?? row.horas ?? 0;
  }

  async function save(row) {
    const hours = Number(value(row));
    if (!Number.isFinite(hours) || hours < 0 || hours > 24) {
      setError("Las horas del turno deben estar entre 0 y 24.");
      return;
    }
    try {
      setSaving(row.codigo);
      setError("");
      setMessage("");
      const response = await fetch(`/api/v2/shifts/${encodeURIComponent(row.codigo)}`, {
        method: "PATCH",
        headers: { "Content-Type": "application/json" },
        body: JSON.stringify({ hours }),
      });
      const body = await response.json();
      if (!response.ok) throw new Error(body.detail || `HTTP ${response.status}`);
      setDraft((current) => {
        const next = { ...current };
        delete next[row.codigo];
        return next;
      });
      setMessage(
        `${row.codigo} actualizado a ${fmt(hours)} H. La disponibilidad de los técnicos que usan este turno quedó recalculada en la base de datos.`,
      );
      await load();
    } catch (cause) {
      setError(cause.message);
    } finally {
      setSaving("");
    }
  }

  const workShifts = rows.filter((row) => !row.es_ausencia);
  const absences = rows.filter((row) => row.es_ausencia);

  return (
    <section className="v2-panel v2-shift-settings">
      <div className="v2-section-head">
        <div>
          <span className="v2-kicker">CONFIGURACIÓN DE TURNOS</span>
          <h3>Horas disponibles por turno</h3>
          <p>
            Esta configuración queda guardada en Supabase. Al cambiar un turno,
            se actualizan las H-H disponibles de los técnicos que lo tienen asignado.
          </p>
        </div>
        <Badge>{loading ? "Consultando..." : `${workShifts.length} turnos`}</Badge>
      </div>

      {error && <div className="v2-error">{error}</div>}
      {message && <div className="v2-success">{message}</div>}

      <div className="v2-table-wrap">
        <table>
          <thead>
            <tr>
              <th>Turno</th>
              <th>Horas</th>
              <th>Uso en el mes</th>
              <th>Técnicos</th>
              <th>Acción</th>
            </tr>
          </thead>
          <tbody>
            {workShifts.map((row) => (
              <tr key={row.codigo}>
                <td><b>{row.codigo}</b></td>
                <td>
                  <label className="v2-shift-hour-field">
                    <input
                      type="number"
                      min="0"
                      max="24"
                      step="0.25"
                      value={value(row)}
                      onChange={(event) =>
                        setDraft((current) => ({ ...current, [row.codigo]: event.target.value }))
                      }
                    />
                    <span>H</span>
                  </label>
                </td>
                <td><b>{Number(row.registros_mes || 0)}</b><small>días asignados</small></td>
                <td><b>{Number(row.tecnicos_mes || 0)}</b><small>en el período</small></td>
                <td>
                  <button
                    type="button"
                    className="v2-save"
                    disabled={saving === row.codigo || draft[row.codigo] === undefined}
                    onClick={() => save(row)}
                  >
                    {saving === row.codigo ? "Guardando..." : "Guardar horas"}
                  </button>
                </td>
              </tr>
            ))}
            {!workShifts.length && !loading && (
              <tr><td colSpan="5" className="v2-empty">No hay turnos de trabajo cargados.</td></tr>
            )}
          </tbody>
        </table>
      </div>

      {!!absences.length && (
        <div className="v2-shift-absence-note">
          <b>Códigos sin disponibilidad:</b>{" "}
          {absences.map((row) => row.codigo).join(", ")}. Se mantienen en 0 H porque representan ausencias o días no laborados.
        </div>
      )}
    </section>
  );
}
