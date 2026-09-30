import { useEffect, useMemo, useState } from "react";
import {
  getHealth,
  getV2Dashboard,
  getV2PendingPlans,
  saveV2PlanComplement,
  getV2Technicians,
  uploadV2TechnicianSchedule,
  saveV2TechnicianComplement,
  getV2Pmp,
  getV2WeekProgramming,
  saveV2WeekProgramming,
  downloadV2WeeklyReport,
} from "./api";
import WeeklyClosure from "./components/WeeklyClosure";
import ProgressDashboard from "./components/ProgressDashboard";
import AdvanceStops from "./components/AdvanceStops";
import WeeklyProgramming from "./components/WeeklyProgramming";
import WeeklyProgrammingTest from "./components/WeeklyProgrammingTest";
import MaintenanceBaseUpload from "./components/MaintenanceBaseUpload";
import TechnicianSchedule from "./components/TechnicianSchedule";
import AccumulatedBacklog from "./components/AccumulatedBacklog";
import OperationExclusions from "./components/OperationExclusions";
import MonthlyClose from "./components/MonthlyClose";
import AppShell from "./app/AppShell";
import { navigationIds } from "./app/navigation";
import Badge from "./shared/Badge";
import "./styles.css";
import "./backlog.css";

const MONTHS = [
  "Enero",
  "Febrero",
  "Marzo",
  "Abril",
  "Mayo",
  "Junio",
  "Julio",
  "Agosto",
  "Septiembre",
  "Octubre",
  "Noviembre",
  "Diciembre",
];
const SPEC_NAMES = {
  MEC: "Mecánica",
  ELE: "Eléctrica",
  MET: "Metrología",
  SER: "Servicios",
};
const SPECS = ["MEC", "ELE", "MET", "SER"];

function number(v, d = 0) {
  const n = Number(v);
  return Number.isFinite(n) ? n : d;
}
function fmt(v, d = 1) {
  return number(v).toLocaleString("es-CO", {
    minimumFractionDigits: d,
    maximumFractionDigits: d,
  });
}
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

function Summary({ data, onNavigate, year, month }) {
  const s = data?.summary || {};
  const p = data?.pending || {};
  const ready = number(s.registros_listos);
  const total = number(s.registros_pmp);
  const readyPct = total > 0 ? Math.round((ready / total) * 100) : 0;
  const quickActions = [
    { id: "advanceStops", title: "Preparar paradas", text: "Revisar actividades con equipo detenido", icon: "calendar" },
    { id: "programming", title: "Programación semanal", text: "Seleccionar y guardar actividades", icon: "tools" },
    { id: "closure", title: "Cierre semanal", text: "Conciliar OT contra el calendario", icon: "check" },
    { id: "monthly", title: "Cierre mensual", text: "Validar, consolidar y formalizar el cierre del mes", icon: "report" },
    { id: "imports", title: "Cargar Excel", text: "Actualizar archivos del período", icon: "calendar" },
  ];
  return (
    <div className="v2-stack v2-control-dashboard">

      <section className="v2-control-primary">
        <article>
          <div className="v2-control-icon"><ControlIcon type="calendar" /></div>
          <div>
            <span>PMP DEL MES</span>
            <strong>{number(s.registros_pmp)}</strong>
            <small>{number(s.ot_distintas)} OT distintas</small>
          </div>
        </article>
        <article>
          <div className="v2-control-icon"><ControlIcon type="clock" /></div>
          <div>
            <span>H-H CALCULABLES</span>
            <strong>{fmt(s.hh_calculables, 1)}</strong>
            <small>carga preventiva calculable</small>
          </div>
        </article>
        <article>
          <div className="v2-control-icon"><ControlIcon type="team" /></div>
          <div>
            <span>H-H TÉCNICOS DEL MES</span>
            <strong>{fmt(s.hh_tecnicos_mes, 1)}</strong>
            <small>disponibilidad antes del 80 / 20</small>
          </div>
        </article>
      </section>

      <button
        type="button"
        className="v2-analysis-entry v2-analysis-entry-top"
        onClick={() => onNavigate("indicators")}
      >
        <span className="v2-analysis-entry-icon"><ControlIcon type="bars" /></span>
        <span className="v2-analysis-entry-copy">
          <b>Indicadores y seguimiento</b>
          <small>Seguimiento del período · Tendencia semanal · Exportación · Por especialidad · Calidad de datos</small>
        </span>
        <span className="v2-analysis-entry-arrow">→</span>
      </button>

      <section className="v2-control-body">
        <div className="v2-control-shortcuts">
          <div className="v2-control-panel-head">
            <div>
              <span className="v2-kicker">ACCESOS RÁPIDOS</span>
              <h3>Procesos principales</h3>
            </div>
          </div>
          <div className="v2-control-action-list">
            {quickActions.map((action) => (
              <button type="button" key={action.id} onClick={() => onNavigate(action.id)}>
                <span className="v2-control-action-icon"><ControlIcon type={action.icon} /></span>
                <span className="v2-control-action-copy">
                  <b>{action.title}</b>
                  <small>{action.text}</small>
                </span>
                <span className="v2-control-arrow">→</span>
              </button>
            ))}
          </div>
        </div>
        <div className="v2-control-overview">
          <div className="v2-control-panel-head">
            <div>
              <span className="v2-kicker">ESTADO OPERATIVO</span>
              <h3>Preparación del período</h3>
            </div>
            <b>{readyPct}% listo</b>
          </div>
          <div className="v2-control-progress">
            <i style={{ width: `${Math.min(100, readyPct)}%` }} />
          </div>
          <div className="v2-control-mini-grid">
            <button type="button" onClick={() => onNavigate("pmp")}>
              <ControlIcon type="check" />
              <span>Registros PMP listos</span>
              <strong>{number(s.registros_listos)}</strong>
            </button>
            <button type="button" onClick={() => onNavigate("pending")}>
              <ControlIcon type="alert" />
              <span>Planes pendientes</span>
              <strong>{number(p.planes_pendientes)}</strong>
            </button>
            <button type="button" onClick={() => onNavigate("pending")}>
              <ControlIcon type="team" />
              <span>Sin Nº personas</span>
              <strong>{number(p.planes_sin_personas)}</strong>
            </button>
            <button type="button" onClick={() => onNavigate("technicians")}>
              <ControlIcon type="team" />
              <span>Técnicos sin especialidad</span>
              <strong>{number(s.tecnicos_sin_especialidad)}</strong>
            </button>
          </div>
          <div className="v2-control-operation-note">
            <b>{number(s.planes_operacion)}</b> planes OPERACIÓN excluidos ·
            <b> {number(s.registros_operacion_excluidos)}</b> registros fuera del PMP de mantenimiento.
          </div>
        </div>

      </section>

    </div>
  );
}


function IndicatorsTracking({ data, year, month, onGoMonthly }) {
  const s = data?.summary || {};
  const specialties = data?.specialties || [];
  const totalHh = specialties.reduce((sum, row) => sum + Number(row.hh_calculables || 0), 0);
  const totalRecords = Number(s.registros_listos || 0)
    + Number(s.registros_sin_personas || 0)
    + Number(s.registros_sin_tiempo_parada || 0)
    + Number(s.registros_sin_plan_maestro || 0);
  const readyPct = totalRecords
    ? Math.round((Number(s.registros_listos || 0) / totalRecords) * 100)
    : 100;

  return (
    <div className="v2-stack v2-indicators-view">
      <ProgressDashboard year={year} month={month} onOpenMonthly={onGoMonthly} />

      <section className="v2-panel v2-indicator-specialties">
        <div className="v2-section-head">
          <div>
            <span className="v2-kicker">POR ESPECIALIDAD</span>
            <h3>Carga preventiva del mes</h3>
            <p>Participación de cada especialidad dentro de las H-H calculables del PMP.</p>
          </div>
          <div className="v2-indicator-total-hh">
            <span>Total calculable</span>
            <b>{fmt(totalHh, 1)} H-H</b>
          </div>
        </div>
        <div className="v2-spec-grid v2-spec-grid-analytics">
          {specialties.map((x) => {
            const hhValue = Number(x.hh_calculables || 0);
            const share = totalHh ? Math.min(100, (hhValue / totalHh) * 100) : 0;
            return (
              <article key={x.especialidad} className="v2-spec-card v2-spec-card-analytics">
                <div className="v2-spec-card-head">
                  <span className="v2-spec-code">{x.especialidad}</span>
                  <div>
                    <b>{SPEC_NAMES[x.especialidad] || x.especialidad}</b>
                    <small>{share.toLocaleString("es-CO", { maximumFractionDigits: 1 })}% de las H-H</small>
                  </div>
                </div>
                <div className="v2-spec-card-main">
                  <strong>{fmt(hhValue, 1)}</strong>
                  <span>H-H calculables</span>
                </div>
                <div className="v2-spec-share-track">
                  <i style={{ width: `${share}%` }} />
                </div>
                <div className="v2-spec-card-foot">
                  <span><b>{number(x.ot_distintas)}</b> OT distintas</span>
                  <span><b>{number(x.registros || x.pmp_count || 0)}</b> registros</span>
                </div>
              </article>
            );
          })}
        </div>
      </section>

      <section className="v2-panel v2-indicator-quality">
        <div className="v2-section-head">
          <div>
            <span className="v2-kicker">CALIDAD DE DATOS</span>
            <h3>Estado de preparación de la información</h3>
            <p>Validación de los datos mínimos requeridos antes de programar.</p>
          </div>
          <div className="v2-quality-score">
            <strong>{readyPct}%</strong>
            <span>preparación</span>
          </div>
        </div>

        <div className="v2-quality-progress">
          <i style={{ width: `${Math.max(0, Math.min(100, readyPct))}%` }} />
        </div>

        <div className="v2-quality-grid v2-quality-grid-analytics">
          <article className="good">
            <span>Listos para programar</span>
            <b>{number(s.registros_listos)}</b>
            <small>registros del PMP completos</small>
          </article>
          <article className={Number(s.registros_sin_personas || 0) ? "warn" : "good"}>
            <span>Sin Nº personas</span>
            <b>{number(s.registros_sin_personas)}</b>
            <small>requieren completar recurso</small>
          </article>
          <article className={Number(s.registros_sin_tiempo_parada || 0) ? "warn" : "good"}>
            <span>Sin tiempo de parada</span>
            <b>{number(s.registros_sin_tiempo_parada)}</b>
            <small>requieren definir condición</small>
          </article>
          <article className={Number(s.registros_sin_plan_maestro || 0) ? "danger" : "good"}>
            <span>Sin plan maestro</span>
            <b>{number(s.registros_sin_plan_maestro)}</b>
            <small>requieren conciliación</small>
          </article>
        </div>
      </section>
    </div>
  );
}

function PendingPlans({ year, month, onChanged }) {
  const [data, setData] = useState(null);
  const [spec, setSpec] = useState("");
  const [search, setSearch] = useState("");
  const [draft, setDraft] = useState({});
  const [saving, setSaving] = useState(null);
  const [error, setError] = useState("");
  const load = () =>
    getV2PendingPlans(year, month, spec)
      .then(setData)
      .catch((e) => setError(e.message));
  useEffect(() => {
    load();
  }, [year, month, spec]);
  const rows = useMemo(() => {
    const q = search.trim().toLowerCase();
    if (!q) return data?.plans || [];
    return (data?.plans || []).filter(
      (x) =>
        String(x.descripcion_grupo || "")
          .toLowerCase()
          .includes(q) ||
        String(x.plan_trabajo || "")
          .toLowerCase()
          .includes(q),
    );
  }, [data, search]);
  function value(id, field, current) {
    return draft[id]?.[field] ?? current ?? "";
  }
  function setValue(id, field, v) {
    setDraft((d) => ({ ...d, [id]: { ...(d[id] || {}), [field]: v } }));
  }
  async function save(row) {
    const peopleRaw = value(row.id, "people", row.numero_personas_app);
    const stopRaw = value(row.id, "stop", row.tiempo_parada_app_min);
    const people = peopleRaw === "" ? null : Number(peopleRaw);
    const stop = stopRaw === "" ? null : Number(stopRaw);
    try {
      setSaving(row.id);
      setError("");
      await saveV2PlanComplement(row.id, {
        people: Number.isFinite(people) ? people : null,
        stop_minutes: Number.isFinite(stop) ? stop : null,
      });
      setDraft((d) => {
        const n = { ...d };
        delete n[row.id];
        return n;
      });
      await load();
      onChanged?.();
    } catch (e) {
      setError(e.message);
    } finally {
      setSaving(null);
    }
  }
  return (
    <div className="v2-stack">
      <section className="v2-panel">
        <div className="v2-section-head">
          <div>
            <span className="v2-kicker">APRENDIZAJE DE LA APP</span>
            <h3>Datos que faltan en los planes usados este mes</h3>
            <p>
              Si el software ya trae el dato, se usa automáticamente. Si viene
              vacío, puedes completarlo aquí.
            </p>
          </div>
          <Badge tone="warn">
            {data?.plans?.length || 0} planes pendientes
          </Badge>
        </div>
        <div className="v2-toolbar">
          <input
            placeholder="Buscar grupo o plan de trabajo..."
            value={search}
            onChange={(e) => setSearch(e.target.value)}
          />
          <select value={spec} onChange={(e) => setSpec(e.target.value)}>
            <option value="">Todas las especialidades</option>
            {SPECS.map((s) => (
              <option key={s} value={s}>
                {SPEC_NAMES[s]}
              </option>
            ))}
          </select>
        </div>
        {error && <div className="v2-error">{error}</div>}
        <div className="v2-table-wrap">
          <table>
            <thead>
              <tr>
                <th>Grupo</th>
                <th>Plan de trabajo</th>
                <th>Esp.</th>
                <th>PMP mes</th>
                <th>Nº personas</th>
                <th>Tiempo parada</th>
                <th>Acción</th>
              </tr>
            </thead>
            <tbody>
              {rows.map((row) => {
                const peopleSoftware = row.numero_personas_software;
                const stopSoftware = row.tiempo_parada_software;
                return (
                  <tr key={row.id}>
                    <td>
                      <b>{row.descripcion_grupo || row.grupo}</b>
                    </td>
                    <td>
                      <span className="v2-plan">{row.plan_trabajo}</span>
                      <small>{row.descripcion_plan_trabajo}</small>
                    </td>
                    <td>
                      <Badge>{row.especialidad || "—"}</Badge>
                    </td>
                    <td>
                      <b>{number(row.registros_pmp)}</b>
                      <small>{number(row.ot_distintas)} OT</small>
                    </td>
                    <td>
                      {peopleSoftware != null ? (
                        <div>
                          <b>{peopleSoftware}</b>
                          <small>Software</small>
                        </div>
                      ) : (
                        <label className="v2-inline-field">
                          <input
                            type="number"
                            min="1"
                            step="1"
                            placeholder="Ej. 2"
                            value={value(
                              row.id,
                              "people",
                              row.numero_personas_app,
                            )}
                            onChange={(e) =>
                              setValue(row.id, "people", e.target.value)
                            }
                          />
                          <small>Completar en app</small>
                        </label>
                      )}
                    </td>
                    <td>
                      {stopSoftware != null ? (
                        <div>
                          <b>{stopSoftware} min</b>
                          <small>
                            {number(stopSoftware) > 0
                              ? "Equipo detenido"
                              : "Equipo operando"}{" "}
                            · Software
                          </small>
                        </div>
                      ) : (
                        <label className="v2-inline-field">
                          <input
                            type="number"
                            min="0"
                            step="1"
                            placeholder="0 = operando"
                            value={value(
                              row.id,
                              "stop",
                              row.tiempo_parada_app_min,
                            )}
                            onChange={(e) =>
                              setValue(row.id, "stop", e.target.value)
                            }
                          />
                          <small>0 = no requiere parada</small>
                        </label>
                      )}
                    </td>
                    <td>
                      <button
                        className="v2-save"
                        disabled={saving === row.id}
                        onClick={() => save(row)}
                      >
                        {saving === row.id ? "Guardando..." : "Guardar"}
                      </button>
                    </td>
                  </tr>
                );
              })}
              {!rows.length && (
                <tr>
                  <td colSpan="7" className="v2-empty">
                    No hay planes pendientes con este filtro.
                  </td>
                </tr>
              )}
            </tbody>
          </table>
        </div>
      </section>
      {!!data?.missing_master?.length && (
        <section className="v2-panel v2-alert-panel">
          <div className="v2-section-head">
            <div>
              <span className="v2-kicker">REVISAR EN SOFTWARE</span>
              <h3>Planes usados por el PMP que no están en Plan de Trabajo</h3>
            </div>
          </div>
          <div className="v2-missing-list">
            {data.missing_master.map((x) => (
              <div key={x.plan_clave_software}>
                <b>{x.plan_clave_software}</b>
                <span>
                  {number(x.registros_pmp)} registros · {number(x.ot_distintas)}{" "}
                  OT
                </span>
              </div>
            ))}
          </div>
        </section>
      )}
    </div>
  );
}

function Technicians({ year, month, onChanged }) {
  const [data, setData] = useState(null);
  const [draft, setDraft] = useState({});
  const [saving, setSaving] = useState(null);
  const [scheduleFile, setScheduleFile] = useState(null);
  const [uploadingSchedule, setUploadingSchedule] = useState(false);
  const [scheduleResult, setScheduleResult] = useState(null);
  const [error, setError] = useState("");
  const load = () =>
    getV2Technicians(year, month)
      .then(setData)
      .catch((e) => setError(e.message));
  useEffect(() => {
    load();
  }, [year, month]);
  async function save(t) {
    const specialty = draft[t.id];
    if (!specialty) return;
    try {
      setSaving(t.id);
      setError("");
      await saveV2TechnicianComplement(t.id, specialty);
      setDraft((d) => ({ ...d, [t.id]: "" }));
      await load();
      onChanged?.();
    } catch (e) {
      setError(e.message);
    } finally {
      setSaving(null);
    }
  }
  async function uploadSchedule() {
    if (!scheduleFile) return setError("Selecciona la programación mensual de técnicos.");
    setUploadingSchedule(true);
    setScheduleResult(null);
    setError("");
    try {
      const result = await uploadV2TechnicianSchedule(scheduleFile, year, month);
      setScheduleResult(result);
      await load();
      onChanged?.();
    } catch (e) {
      setError(e.message || "No se pudo cargar la programación de técnicos.");
    } finally {
      setUploadingSchedule(false);
    }
  }
  return (
    <section className="v2-panel">
      <div className="v2-section-head">
        <div>
          <span className="v2-kicker">PERSONAL</span>
          <h3>Programación mensual de técnicos</h3>
          <p>
            La especialidad del software tiene prioridad. Solo completamos los
            técnicos que vienen sin ella.
          </p>
        </div>
        <Badge
          tone={
            data?.technicians?.some((t) => !t.especialidad_efectiva)
              ? "warn"
              : "ok"
          }
        >
          {data?.technicians?.filter((t) => !t.especialidad_efectiva).length ||
            0}{" "}
          pendientes
        </Badge>
      </div>
      <div className="v2-panel" style={{ marginBottom: 16 }}>
        <span className="v2-kicker">CARGA DEL MES</span>
        <h3>Programación de técnicos · {String(month).padStart(2, "0")}/{year}</h3>
        <p>Sube el Excel que contiene la hoja <b>PROGRAMACION DE TECNICOS</b>. Para el piloto de octubre se insertan o actualizan los turnos por técnico y fecha sin modificar otros meses.</p>
        <div className="v2-program-review-actions">
          <input type="file" accept=".xlsx" onChange={(e) => {
            setScheduleFile(e.target.files?.[0] || null);
            setScheduleResult(null);
          }} />
          <button type="button" className="v2-primary" onClick={uploadSchedule}
            disabled={!scheduleFile || uploadingSchedule}>
            {uploadingSchedule ? "Cargando programación..." : "Cargar programación de técnicos"}
          </button>
        </div>
        {scheduleResult && <div className="v2-success" style={{ marginTop: 12 }}>
          <b>{scheduleResult.tecnicos} técnicos · {scheduleResult.registros} registros de calendario · {fmt(scheduleResult.hh_disponibles, 1)} H-H disponibles.</b>
          <p>{scheduleResult.ausencias} registros de ausencia · {scheduleResult.tecnicos_sin_enlace} técnicos sin enlace.</p>
          {scheduleResult.warnings?.length > 0 && <details>
            <summary>Advertencias ({scheduleResult.warnings.length})</summary>
            <ul>{scheduleResult.warnings.map((w, i) => <li key={i}>{w}</li>)}</ul>
          </details>}
        </div>}
      </div>
      {error && <div className="v2-error">{error}</div>}
      <div className="v2-table-wrap">
        <table>
          <thead>
            <tr>
              <th>Técnico</th>
              <th>Especialidad</th>
              <th>Fuente</th>
              <th>H-H mes</th>
              <th>Acción</th>
            </tr>
          </thead>
          <tbody>
            {(data?.technicians || []).map((t) => (
              <tr key={t.id}>
                <td>
                  <b>{t.nombre}</b>
                  <small>{t.identificacion || ""}</small>
                </td>
                <td>
                  {t.especialidad_efectiva ? (
                    <Badge>
                      {SPEC_NAMES[t.especialidad_efectiva] ||
                        t.especialidad_efectiva}
                    </Badge>
                  ) : (
                    <select
                      value={draft[t.id] || ""}
                      onChange={(e) =>
                        setDraft((d) => ({ ...d, [t.id]: e.target.value }))
                      }
                    >
                      <option value="">Seleccionar...</option>
                      {SPECS.map((s) => (
                        <option key={s} value={s}>
                          {SPEC_NAMES[s]}
                        </option>
                      ))}
                    </select>
                  )}
                </td>
                <td>
                  <small>
                    {t.especialidad_software
                      ? "SOFTWARE"
                      : t.especialidad_app
                        ? "APP"
                        : "PENDIENTE"}
                  </small>
                </td>
                <td>
                  <b>{fmt(t.hh_mes, 1)}</b>
                </td>
                <td>
                  {!t.especialidad_efectiva ? (
                    <button
                      className="v2-save"
                      disabled={!draft[t.id] || saving === t.id}
                      onClick={() => save(t)}
                    >
                      {saving === t.id ? "Guardando..." : "Guardar"}
                    </button>
                  ) : (
                    <Badge tone="ok">Completo</Badge>
                  )}
                </td>
              </tr>
            ))}
          </tbody>
        </table>
      </div>
    </section>
  );
}

function monthWeeks(year, month) {
  const days = new Date(year, month, 0).getDate();
  const weeks = [];
  for (let start = 1; start <= days; start += 7) {
    const end = Math.min(start + 6, days);
    const from = `${year}-${String(month).padStart(2, "0")}-${String(start).padStart(2, "0")}`;
    const to = `${year}-${String(month).padStart(2, "0")}-${String(end).padStart(2, "0")}`;
    weeks.push({ from, to, label: `${start}–${end} ${MONTHS[month - 1]}` });
  }
  return weeks;
}

function LegacyWeeklyProgramming({ year, month, dashboard }) {
  const weeks = useMemo(() => monthWeeks(year, month), [year, month]);
  const [weekIndex, setWeekIndex] = useState(0);
  const [specialty, setSpecialty] = useState("MEC");
  const [data, setData] = useState(null);
  const [selected, setSelected] = useState(new Set());
  const [search, setSearch] = useState("");
  const [area, setArea] = useState("");
  const [loading, setLoading] = useState(false);
  const [saving, setSaving] = useState(false);
  const [error, setError] = useState("");
  const [message, setMessage] = useState("");
  const [dirty, setDirty] = useState(false);
  const [programmingId, setProgrammingId] = useState(null);
  const [editing, setEditing] = useState(true);
  const week = weeks[Math.min(weekIndex, weeks.length - 1)] || weeks[0];
  async function load() {
    if (!week) return;
    try {
      setLoading(true);
      setError("");
      const r = await getV2WeekProgramming(week.from, week.to, specialty);
      setData(r);
      setSelected(new Set((r.selected_ids || []).map(Number)));
      setProgrammingId(r.programming?.id || null);
      setEditing(!r.programming);
      setDirty(false);
    } catch (e) {
      setError(e.message);
    } finally {
      setLoading(false);
    }
  }
  useEffect(() => {
    setWeekIndex(0);
  }, [month]);
  useEffect(() => {
    load();
  }, [week?.from, week?.to, specialty]);
  const allRows = useMemo(
    () => [
      ...(data?.operating || []),
      ...(data?.stopped || []),
      ...(data?.backlog || []),
    ],
    [data],
  );
  const rowMap = useMemo(
    () => new Map(allRows.map((r) => [Number(r.orden_mantenimiento_id), r])),
    [allRows],
  );
  const selectedHH = useMemo(
    () =>
      [...selected].reduce((sum, id) => sum + number(rowMap.get(id)?.hh), 0),
    [selected, rowMap],
  );
  const target = number(data?.capacity?.target);
  const available = number(data?.capacity?.available);
  const effective = number(data?.capacity?.effective);
  const reserve = number(data?.capacity?.reserve);
  const initialMargin = number(data?.capacity?.initial_margin);
  const techniciansAvailable = number(
    data?.capacity?.technicians_available,
    data?.capacity?.technicians || 0,
  );
  const techniciansAssigned = number(
    data?.capacity?.technicians_assigned,
    data?.capacity?.technicians || 0,
  );
  const remaining = Math.max(0, target - selectedHH);
  const progress = target > 0 ? Math.min(100, (selectedHH / target) * 100) : 0;
  function toggle(row, event) {
    event?.preventDefault();
    if (!editing) return;
    const pageY = window.scrollY;
    const scroller = event?.currentTarget?.closest(".v2-program-table");
    const tableY = scroller?.scrollTop ?? 0;
    const id = Number(row.orden_mantenimiento_id);
    setError("");
    setMessage("");
    setSelected((prev) => {
      const next = new Set(prev);
      if (next.has(id)) {
        next.delete(id);
        setDirty(true);
        return next;
      }
      const currentHH = [...prev].reduce(
        (sum, selectedId) => sum + number(rowMap.get(selectedId)?.hh),
        0,
      );
      const nextHH = currentHH + number(row.hh);
      if (nextHH > target + 0.001) {
        setError(
          `No se puede seleccionar esta actividad: llegarías a ${fmt(nextHH, 1)} H-H y la meta máxima es ${fmt(target, 1)} H-H.`,
        );
        return prev;
      }
      next.add(id);
      setDirty(true);
      return next;
    });
    requestAnimationFrame(() => {
      window.scrollTo({ top: pageY, left: 0, behavior: "auto" });
      if (scroller) scroller.scrollTop = tableY;
      requestAnimationFrame(() => {
        window.scrollTo({ top: pageY, left: 0, behavior: "auto" });
        if (scroller) scroller.scrollTop = tableY;
      });
    });
  }
  function filtered(rows) {
    const q = search.trim().toLowerCase();
    return rows.filter((r) => {
      if (area && r.area_codigo !== area) return false;
      if (!q) return true;
      return (
        String(r.numero_ot || "")
          .toLowerCase()
          .includes(q) ||
        String(r.activo_codigo || "")
          .toLowerCase()
          .includes(q) ||
        String(r.activo_descripcion || "")
          .toLowerCase()
          .includes(q) ||
        String(r.plan_trabajo || "")
          .toLowerCase()
          .includes(q)
      );
    });
  }
  async function save() {
    if (!selected.size) {
      setError("Selecciona al menos una orden para guardar la semana.");
      return;
    }
    try {
      setSaving(true);
      setError("");
      setMessage("");
      const r = await saveV2WeekProgramming({
        date_from: week.from,
        date_to: week.to,
        specialty,
        order_ids: [...selected],
        created_by: "CARLOS ANDRÉS RECIO MUÑOZ",
      });
      setProgrammingId(r.programming_id);
      setDirty(false);
      await load();
      setMessage(
        `Programación guardada: ${fmt(r.hh_programmed, 1)} H-H de ${fmt(r.hh_target, 1)} H-H objetivo.${r.moved_to_backlog ? ` ${r.moved_to_backlog} OT movida(s) a BACKLOG.` : ""}`,
      );
    } catch (e) {
      setError(e.message);
    } finally {
      setSaving(false);
    }
  }
  async function report(format) {
    if (!programmingId || dirty) {
      setError("Guarda la programación antes de generar el reporte.");
      return;
    }
    try {
      setError("");
      await downloadV2WeeklyReport(programmingId, format);
    } catch (e) {
      setError(e.message);
    }
  }
  function cancelEdit() {
    load();
    setMessage(
      "Cambios descartados. La programación vuelve a la última versión guardada.",
    );
  }
  function ActivityTable({ rows, title, kind }) {
    const visible = filtered(rows).filter(
      (r) => !selected.has(Number(r.orden_mantenimiento_id)),
    );
    const stopped = kind === "stopped";
    const backlog = kind === "backlog";
    return (
      <section
        className={
          "v2-activity-section " +
          (backlog ? "backlog" : stopped ? "stopped" : "operating")
        }
      >
        <div className="v2-activity-head">
          <div>
            <span className="v2-kicker">
              {backlog
                ? "BACKLOG"
                : stopped
                  ? "PARADA REQUERIDA"
                  : "EQUIPO OPERANDO"}
            </span>
            <h3>{title}</h3>
            <p>
              {backlog
                ? "OT retiradas de programaciones anteriores. Revísalas primero para no perderlas de vista."
                : stopped
                  ? "Actividades que necesitan el equipo detenido."
                  : "Actividades que pueden ejecutarse con el equipo funcionando."}
            </p>
          </div>
          <Badge tone={backlog ? "backlog" : stopped ? "stop" : "ok"}>
            {visible.length} disponibles
          </Badge>
        </div>
        <div className="v2-table-wrap v2-program-table">
          <table>
            <thead>
              <tr>
                {backlog && <th>Origen</th>}
                <th>OT</th>
                <th>Área</th>
                <th>Equipo</th>
                <th>Plan de trabajo</th>
                <th>Personas</th>
                <th>Tiempo</th>
                <th>H-H</th>
                <th>Seleccionar</th>
              </tr>
            </thead>
            <tbody>
              {visible.map((r) => {
                const id = Number(r.orden_mantenimiento_id);
                return (
                  <tr key={id}>
                    {backlog && (
                      <td>
                        <div className="v2-backlog-origin">
                          <b>Movida</b>
                          <small>
                            {r.semana_origen_inicio || "Semana anterior"} →{" "}
                            {r.semana_origen_fin || ""}
                          </small>
                        </div>
                      </td>
                    )}
                    <td>
                      <b>{r.numero_ot || "SIN ASIGNAR"}</b>
                    </td>
                    <td>
                      <Badge>{r.area_codigo || "—"}</Badge>
                      <small>{r.area_nombre || ""}</small>
                    </td>
                    <td>
                      <b>{r.activo_codigo}</b>
                      <small>{r.activo_descripcion}</small>
                    </td>
                    <td>
                      <span className="v2-plan">{r.plan_trabajo}</span>
                      <small>{r.descripcion_grupo || ""}</small>
                    </td>
                    <td>
                      <b>{r.numero_personas_efectivo}</b>
                    </td>
                    <td>{fmt(r.tiempo_min, 0)} min</td>
                    <td>
                      <b>{fmt(r.hh, 1)}</b>
                    </td>
                    <td>
                      <button
                        type="button"
                        className="v2-select"
                        disabled={!editing}
                        onClick={(e) => toggle(r, e)}
                      >
                        {editing ? "Seleccionar" : "Solo lectura"}
                      </button>
                    </td>
                  </tr>
                );
              })}
              {!visible.length && (
                <tr>
                  <td colSpan={backlog ? 9 : 8} className="v2-empty">
                    {backlog
                      ? "No hay OT pendientes en backlog para esta especialidad."
                      : "No hay actividades listas con estos filtros."}
                  </td>
                </tr>
              )}
            </tbody>
          </table>
        </div>
      </section>
    );
  }
  const selectedRows = useMemo(
    () =>
      [...selected]
        .map((id) => rowMap.get(Number(id)))
        .filter(Boolean)
        .sort(
          (a, b) =>
            Number(a.requiere_parada) - Number(b.requiere_parada) ||
            String(a.area_codigo || "").localeCompare(
              String(b.area_codigo || ""),
            ) ||
            String(a.numero_ot || "").localeCompare(String(b.numero_ot || "")),
        ),
    [selected, rowMap],
  );
  const selectedOperatingHH = selectedRows
    .filter((r) => r.requiere_parada === false)
    .reduce((sum, r) => sum + number(r.hh), 0);
  const selectedStoppedHH = selectedRows
    .filter((r) => r.requiere_parada === true)
    .reduce((sum, r) => sum + number(r.hh), 0);
  function SelectedTable() {
    return (
      <section
        className={"v2-selected-section " + (!editing ? "readonly" : "")}
      >
        <div className="v2-selected-head">
          <div>
            <span className="v2-kicker">
              {editing ? "PROGRAMACIÓN EN EDICIÓN" : "PROGRAMACIÓN GUARDADA"}
            </span>
            <h3>
              {editing
                ? "Actividades seleccionadas para esta semana"
                : "Programación actual de la semana"}
            </h3>
            <p>
              {editing
                ? "Puedes agregar nuevas OT o quitar actividades. Al guardar, las que quites pasarán automáticamente a BACKLOG."
                : "Esta es la última versión guardada. Usa “Modificar programación” si el planeador solicita cambios."}
            </p>
          </div>
          <div className="v2-selected-totals">
            <span>
              <b>{selectedRows.length}</b> actividades
            </span>
            <span>
              <b>{fmt(selectedOperatingHH, 1)}</b> H-H operando
            </span>
            <span>
              <b>{fmt(selectedStoppedHH, 1)}</b> H-H detenido
            </span>
            <span className="total">
              <b>{fmt(selectedHH, 1)}</b> H-H total
            </span>
          </div>
        </div>
        <div className="v2-table-wrap v2-selected-table">
          <table>
            <thead>
              <tr>
                <th>Condición</th>
                <th>Origen</th>
                <th>OT</th>
                <th>Área</th>
                <th>Equipo</th>
                <th>Plan de trabajo</th>
                <th>Personas</th>
                <th>Tiempo</th>
                <th>H-H</th>
                {editing && <th>Acción</th>}
              </tr>
            </thead>
            <tbody>
              {selectedRows.map((r) => (
                <tr key={r.orden_mantenimiento_id}>
                  <td>
                    {r.requiere_parada ? (
                      <Badge tone="stop">Equipo detenido</Badge>
                    ) : (
                      <Badge tone="ok">Equipo funcionando</Badge>
                    )}
                  </td>
                  <td>
                    {r.origen === "BACKLOG" || r.origen_backlog ? (
                      <Badge tone="backlog">BACKLOG</Badge>
                    ) : (
                      <Badge>PMP DEL MES</Badge>
                    )}
                  </td>
                  <td>
                    <b>{r.numero_ot || "SIN ASIGNAR"}</b>
                  </td>
                  <td>
                    <Badge>{r.area_codigo || "—"}</Badge>
                    <small>{r.area_nombre || ""}</small>
                  </td>
                  <td>
                    <b>{r.activo_codigo}</b>
                    <small>{r.activo_descripcion}</small>
                  </td>
                  <td>
                    <span className="v2-plan">{r.plan_trabajo}</span>
                    <small>{r.descripcion_grupo || ""}</small>
                  </td>
                  <td>
                    <b>{r.numero_personas_efectivo}</b>
                  </td>
                  <td>{fmt(r.tiempo_min, 0)} min</td>
                  <td>
                    <b>{fmt(r.hh, 1)}</b>
                  </td>
                  {editing && (
                    <td>
                      <button
                        type="button"
                        className="v2-unselect"
                        onClick={(e) => toggle(r, e)}
                      >
                        Quitar → Backlog
                      </button>
                    </td>
                  )}
                </tr>
              ))}
              {!selectedRows.length && (
                <tr>
                  <td colSpan={editing ? 10 : 9} className="v2-empty">
                    Todavía no has seleccionado actividades para esta semana.
                  </td>
                </tr>
              )}
            </tbody>
          </table>
        </div>
      </section>
    );
  }
  return (
    <div className="v2-stack">
      <section className="v2-panel">
        <div className="v2-section-head">
          <div>
            <span className="v2-kicker">PROGRAMACIÓN SEMANAL</span>
            <h3>Selecciona semana y especialidad</h3>
            <p>
              La semana guardada se puede consultar y, si el planeador solicita
              cambios, abrir nuevamente en modo edición.
            </p>
          </div>
          <Badge>
            {loading
              ? "Calculando..."
              : `${techniciansAvailable} disponibles / ${techniciansAssigned} asignados`}
          </Badge>
        </div>
        <div className="v2-week-selector">
          <div className="v2-week-buttons">
            {weeks.map((w, i) => (
              <button
                type="button"
                key={w.from}
                className={weekIndex === i ? "active" : ""}
                onClick={() => setWeekIndex(i)}
              >
                <b>Semana {i + 1}</b>
                <span>{w.label}</span>
              </button>
            ))}
          </div>
          <div className="v2-specialty-buttons">
            {SPECS.map((s) => (
              <button
                type="button"
                key={s}
                className={specialty === s ? "active" : ""}
                onClick={() => setSpecialty(s)}
              >
                <b>{s}</b>
                <span>{SPEC_NAMES[s]}</span>
              </button>
            ))}
          </div>
        </div>
      </section>
      {programmingId && (
        <section className="v2-program-review">
          <div>
            <span className="v2-kicker">PROGRAMACIÓN EXISTENTE</span>
            <h3>
              {editing
                ? "Modificando programación guardada"
                : "Programación disponible para consulta"}
            </h3>
            <p>
              {editing
                ? "Puedes quitar OT, agregar nuevas y aprovechar una parada de planta. Las OT retiradas pasarán a BACKLOG al guardar."
                : "Puedes verla o exportarla sin modificarla. Si necesitas cambios, activa el modo edición."}
            </p>
          </div>
          <div className="v2-program-review-actions">
            {!editing ? (
              <button
                type="button"
                className="v2-primary"
                onClick={() => {
                  setEditing(true);
                  setMessage(
                    "Modo edición activado. Los cambios no afectan la programación hasta que presiones Guardar cambios.",
                  );
                }}
              >
                Modificar programación
              </button>
            ) : (
              <button type="button" onClick={cancelEdit}>
                Cancelar cambios
              </button>
            )}
            <button
              type="button"
              disabled={dirty}
              onClick={() => report("xlsx")}
            >
              Exportar Excel
            </button>
            <button
              type="button"
              disabled={dirty}
              onClick={() => report("pdf")}
            >
              Exportar PDF
            </button>
          </div>
        </section>
      )}
      <section className="v2-capacity-panel">
        <div className="v2-capacity-cards">
          <div>
            <span>H-H netas técnicos</span>
            <b>{fmt(available, 1)}</b>
            <small>100% según turnos y ausencias</small>
          </div>
          <div>
            <span>Capacidad efectiva</span>
            <b>{fmt(effective, 1)}</b>
            <small>80% de las H-H netas</small>
          </div>
          <div>
            <span>Margen inicial</span>
            <b>{fmt(initialMargin, 1)}</b>
            <small>20% fuera de la capacidad efectiva</small>
          </div>
          <div className="target">
            <span>Preventivo programable</span>
            <b>{fmt(target, 1)}</b>
            <small>80% de la capacidad efectiva para preventivo</small>
          </div>
          <div>
            <span>Correctivo</span>
            <b>{fmt(reserve, 1)}</b>
            <small>
              20% de la capacidad efectiva para correctivo
            </small>
          </div>
          <div className="selected">
            <span>H-H seleccionadas</span>
            <b>{fmt(selectedHH, 1)}</b>
            <small>{selected.size} órdenes / actividades</small>
          </div>
          <div className={remaining <= 0.01 ? "complete" : "remaining"}>
            <span>
              {remaining <= 0.01 ? "Meta alcanzada" : "Faltan para meta"}
            </span>
            <b>{fmt(remaining, 1)}</b>
            <small>H-H</small>
          </div>
        </div>
        <div className="v2-progress-block">
          <div className="v2-progress-copy">
            <span>Avance hacia preventivo</span>
            <b>{fmt(progress, 1)}%</b>
          </div>
          <div className="v2-progress-track">
            <i style={{ width: `${progress}%` }} />
          </div>
          <div className="v2-progress-foot">
            <span>{fmt(selectedHH, 1)} H-H programadas</span>
            <span>Preventivo {fmt(target, 1)} H-H</span>
          </div>
        </div>
        {available === 0 && (
          <div className="v2-warning">
            Esta especialidad no tiene disponibilidad cargada para esta semana.
            Revisa la programación de técnicos.
          </div>
        )}
        {error && <div className="v2-error">{error}</div>}
        {message && <div className="v2-success">{message}</div>}
      </section>
      <section className="v2-panel">
        <div className="v2-program-toolbar">
          <div>
            <span className="v2-kicker">FILTROS</span>
            <h3>
              {editing
                ? "Actividades listas para seleccionar"
                : "Cartera de actividades · solo lectura"}
            </h3>
          </div>
          <div>
            <select value={area} onChange={(e) => setArea(e.target.value)}>
              <option value="">Todas las áreas</option>
              {(dashboard?.areas || []).map((a) => (
                <option key={a.codigo} value={a.codigo}>
                  {a.codigo} · {a.nombre || a.codigo}
                </option>
              ))}
            </select>
            <input
              placeholder="Buscar OT, equipo o plan..."
              value={search}
              onChange={(e) => setSearch(e.target.value)}
            />
          </div>
        </div>
        <ActivityTable
          rows={data?.operating || []}
          title="Equipo operando"
          kind="operating"
        />
        <ActivityTable
          rows={data?.stopped || []}
          title="Equipo detenido"
          kind="stopped"
        />
        <ActivityTable
          rows={data?.backlog || []}
          title="Backlog de programaciones anteriores"
          kind="backlog"
        />
      </section>
      <SelectedTable />
      {(editing || !programmingId) && (
        <section className="v2-save-program">
          <div className="v2-save-program-copy">
            <span className="v2-kicker">
              {programmingId
                ? "GUARDAR MODIFICACIÓN"
                : "CIERRE DE PROGRAMACIÓN"}
            </span>
            <h3>
              {dirty
                ? "Hay cambios sin guardar"
                : programmingId
                  ? "Programación abierta para edición"
                  : "Guarda la selección de esta semana"}
            </h3>
            <p>
              {programmingId
                ? "Al guardar se actualizará la programación. Las OT que estaban en la versión anterior y ahora quitaste pasarán a BACKLOG."
                : "El reporte mostrará las H-H netas, la capacidad efectiva (80%), el preventivo programable (80% de la efectiva), el correctivo (20% de la efectiva) y las órdenes que el ingeniero debe responder."}
            </p>
            <div className="v2-save-summary">
              <span>
                <b>{fmt(selectedHH, 1)}</b> H-H seleccionadas
              </span>
              <span>
                <b>{fmt(target, 1)}</b> H-H meta
              </span>
              <span>
                <b>{fmt(remaining, 1)}</b> H-H faltantes
              </span>
            </div>
            {error && <div className="v2-error v2-error-bottom">{error}</div>}
            {message && (
              <div className="v2-success v2-success-bottom">{message}</div>
            )}
          </div>
          <div className="v2-report-actions">
            <button
              type="button"
              className="v2-primary"
              disabled={
                saving ||
                !selected.size ||
                selectedHH > target + 0.001 ||
                (!dirty && !!programmingId)
              }
              onClick={save}
            >
              {saving
                ? "Guardando..."
                : programmingId
                  ? "Guardar cambios"
                  : "Guardar programación"}
            </button>
            {programmingId && (
              <button type="button" onClick={cancelEdit}>
                Cancelar
              </button>
            )}
          </div>
        </section>
      )}
    </div>
  );
}

function Pmp({ year, month, dashboard }) {
  const [filters, setFilters] = useState({
    specialty: "",
    area: "",
    search: "",
  });
  const [data, setData] = useState(null);
  const [loading, setLoading] = useState(false);
  const [error, setError] = useState("");
  const load = async () => {
    try {
      setLoading(true);
      setError("");
      setData(await getV2Pmp({ year, month, ...filters, limit: 400 }));
    } catch (e) {
      setError(e.message);
    } finally {
      setLoading(false);
    }
  };
  useEffect(() => {
    load();
  }, [year, month]);
  return (
    <section className="v2-panel">
      <div className="v2-section-head">
        <div>
          <span className="v2-kicker">PMP DEL MES</span>
          <h3>Órdenes y planes exportados por el software</h3>
          <p>
            El día de ejecución del software no gobierna nuestra programación
            interna; aquí usamos el mes como cartera de trabajo.
          </p>
        </div>
        <Badge>
          {loading
            ? "Consultando..."
            : (data?.rows?.length || 0) + " registros visibles"}
        </Badge>
      </div>
      <div className="v2-toolbar v2-toolbar-4">
        <select
          value={filters.specialty}
          onChange={(e) =>
            setFilters((f) => ({ ...f, specialty: e.target.value }))
          }
        >
          <option value="">Todas las especialidades</option>
          {SPECS.map((s) => (
            <option key={s} value={s}>
              {SPEC_NAMES[s]}
            </option>
          ))}
        </select>
        <select
          value={filters.area}
          onChange={(e) => setFilters((f) => ({ ...f, area: e.target.value }))}
        >
          <option value="">Todas las áreas</option>
          {(dashboard?.areas || []).map((a) => (
            <option key={a.codigo} value={a.codigo}>
              {a.codigo} · {a.nombre || "Sin nombre raíz"}
            </option>
          ))}
        </select>
        <input
          placeholder="OT, equipo o plan..."
          value={filters.search}
          onChange={(e) =>
            setFilters((f) => ({ ...f, search: e.target.value }))
          }
        />
        <button className="v2-primary" onClick={load}>
          Aplicar filtros
        </button>
      </div>
      {error && <div className="v2-error">{error}</div>}
      <div className="v2-table-wrap v2-pmp-table">
        <table>
          <thead>
            <tr>
              <th>OT</th>
              <th>Área</th>
              <th>Equipo</th>
              <th>Plan</th>
              <th>Esp.</th>
              <th>Personas</th>
              <th>Parada</th>
              <th>Tiempo</th>
              <th>H-H</th>
              <th>Dato</th>
            </tr>
          </thead>
          <tbody>
            {(data?.rows || []).map((r) => (
              <tr key={r.id}>
                <td>
                  <b>{r.numero_ot || "SIN ASIGNAR"}</b>
                </td>
                <td>
                  <Badge>{r.area_codigo || "—"}</Badge>
                  <small>{r.area_nombre || ""}</small>
                </td>
                <td>
                  <b>{r.activo_codigo}</b>
                  <small>{r.activo_descripcion}</small>
                </td>
                <td>
                  <span className="v2-plan">
                    {r.plan_trabajo || r.plan_clave_software}
                  </span>
                  <small>{r.descripcion_grupo || ""}</small>
                </td>
                <td>
                  <Badge>{r.especialidad || "—"}</Badge>
                </td>
                <td>{r.numero_personas_efectivo ?? "—"}</td>
                <td>
                  {r.requiere_parada == null ? (
                    <Badge tone="warn">Falta</Badge>
                  ) : r.requiere_parada ? (
                    <Badge tone="stop">Sí</Badge>
                  ) : (
                    <Badge tone="ok">No</Badge>
                  )}
                </td>
                <td>
                  {r.tiempo_min != null ? fmt(r.tiempo_min, 0) + " min" : "—"}
                </td>
                <td>
                  <b>{r.hh != null ? fmt(r.hh, 1) : "—"}</b>
                </td>
                <td>
                  <Badge tone={r.calidad_dato === "LISTO" ? "ok" : "warn"}>
                    {r.calidad_dato}
                  </Badge>
                </td>
              </tr>
            ))}
            {!data?.rows?.length && !loading && (
              <tr>
                <td colSpan="10" className="v2-empty">
                  No hay registros para estos filtros.
                </td>
              </tr>
            )}
          </tbody>
        </table>
      </div>
    </section>
  );
}

export default function App() {
  const [view, setView] = useState(() => {
    const requested = window.location.hash.replace(/^#\/?/, "");
    return navigationIds().includes(requested) ? requested : "summary";
  });
  const [year] = useState(2026);
  const [month, setMonth] = useState(10);
  const [dashboard, setDashboard] = useState(null);
  const [technicianRevision, setTechnicianRevision] = useState(0);
  const [health, setHealth] = useState("checking");
  const [accessRole, setAccessRole] = useState("loading");
  const [error, setError] = useState("");
  const [backlogOrderId, setBacklogOrderId] = useState("");
  const refresh = () =>
    getV2Dashboard(year, month)
      .then((result) => {
        setDashboard(result);
        return result;
      })
      .catch((e) => {
        setError(e.message);
        throw e;
      });

  const refreshTechnicianData = () => {
    setTechnicianRevision((current) => current + 1);
    return refresh().catch(() => null);
  };
  useEffect(() => {
    getHealth()
      .then(() => setHealth("ok"))
      .catch(() => setHealth("error"));
  }, []);

  useEffect(() => {
    fetch("/api/auth/session", { cache: "no-store" })
      .then(async (response) => {
        if (!response.ok) throw new Error(`HTTP ${response.status}`);
        return response.json();
      })
      .then((body) => setAccessRole(body.role === "admin" ? "admin" : "viewer"))
      .catch(() => setAccessRole("viewer"));
  }, []);

  useEffect(() => {
    const originalFetch = window.fetch.bind(window);
    const canWrite = accessRole === "admin";

    window.fetch = async (input, init = {}) => {
      const method = String(init?.method || "GET").toUpperCase();
      const url = typeof input === "string" ? input : input?.url || "";
      const authRequest = url.includes("/api/auth/");

      if (
        !canWrite &&
        !["GET", "HEAD", "OPTIONS"].includes(method) &&
        !authRequest
      ) {
        return new Response(
          JSON.stringify({
            detail: "Modo solo lectura. Solo el administrador puede modificar información.",
            role: "viewer",
          }),
          {
            status: 403,
            headers: { "Content-Type": "application/json" },
          },
        );
      }

      return originalFetch(input, init);
    };

    return () => {
      window.fetch = originalFetch;
    };
  }, [accessRole]);

  async function adminLogin(password) {
    const response = await fetch("/api/auth/login", {
      method: "POST",
      headers: { "Content-Type": "application/json" },
      body: JSON.stringify({ password }),
    });
    const body = await response.json().catch(() => ({}));
    if (!response.ok) throw new Error(body.detail || "No se pudo iniciar sesión.");
    setAccessRole("admin");
    return body;
  }

  async function adminLogout() {
    await fetch("/api/auth/logout", { method: "POST" }).catch(() => null);
    setAccessRole("viewer");
  }
  useEffect(() => {
    refresh();
  }, [year, month]);
  function navigate(nextView) {
    setView(nextView);
    window.history.replaceState(null, "", `#/${nextView}`);
  }
  return (
    <AppShell
      view={view}
      onNavigate={navigate}
      year={year}
      month={month}
      onMonthChange={setMonth}
      health={health}
      accessRole={accessRole}
      onAdminLogin={adminLogin}
      onAdminLogout={adminLogout}
      onTechnicianDataChanged={refreshTechnicianData}
      indicators={{
        pending: number(dashboard?.pending?.planes_pendientes),
        technicians: number(dashboard?.summary?.tecnicos_sin_especialidad),
      }}
    >
        {error && <div className="v2-error">{error}</div>}
        {view === "summary" && (
          <Summary data={dashboard} year={year} month={month} onNavigate={navigate} />
        )}{" "}
        {view === "indicators" && (
          <IndicatorsTracking data={dashboard} year={year} month={month} onGoMonthly={() => navigate("monthly")} />
        )}{" "}
        {view === "pending" && (
          <PendingPlans year={year} month={month} onChanged={refresh} />
        )}{" "}
        {view === "advanceStops" && <AdvanceStops year={year} month={month} />}
        {view === "programming" && (
          <WeeklyProgramming year={year} month={month} dashboard={dashboard} />
        )}{" "}
        {view === "programmingTest" && (
          <WeeklyProgrammingTest year={year} month={month} dashboard={dashboard} />
        )}{" "}
        {view === "monthly" && <MonthlyClose year={year} month={month} />}
        {view === "closure" && <WeeklyClosure year={year} month={month} onOpenBacklog={(orderId) => { setBacklogOrderId(orderId); navigate("backlog"); }} />}{" "}
        {view === "backlog" && <AccumulatedBacklog areas={dashboard?.areas || []} initialOrderId={backlogOrderId} onClearOrder={() => setBacklogOrderId("")} />}{" "}
        {view === "operationExclusions" && (
          <OperationExclusions year={year} month={month} />
        )}{" "}
        {view === "pmp" && (
          <Pmp year={year} month={month} dashboard={dashboard} />
        )}{" "}
        {view === "technicians" && (
          <TechnicianSchedule
            year={year}
            month={month}
            revision={technicianRevision}
            onChanged={refreshTechnicianData}
          />
        )}
        {view === "imports" && (
          <MaintenanceBaseUpload year={year} month={month} />
        )}
    </AppShell>
  );
}
