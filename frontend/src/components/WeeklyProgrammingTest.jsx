import { useEffect, useMemo, useState } from "react";
import { monthWeeks } from "../features/planning/monthWeeks.js";
import { getV2WeekProgramming } from "../api";
import { emptyFilters, matchesFilters, updateGroupFilters } from "../features/planning/weeklyProgrammingFilters";
import { toggleWeeklySelection } from "../features/planning/weeklyProgrammingSelection";
import Badge from "../shared/Badge";

const SPEC_NAMES = { MEC: "Mecánica", ELE: "Eléctrica", MET: "Metrología", SER: "Servicios" };
const SPECS = ["MEC", "ELE", "MET", "SER"];

function number(value, fallback = 0) {
  const parsed = Number(value);
  return Number.isFinite(parsed) ? parsed : fallback;
}

function fmt(value, decimals = 1) {
  return number(value).toLocaleString("es-CO", {
    minimumFractionDigits: decimals,
    maximumFractionDigits: decimals,
  });
}

function storageKey(year, month, week, specialty) {
  return `team-food-weekly-test:${year}:${month}:${week?.from || ""}:${specialty}`;
}

function ActivityGroup({ kind, rows, dashboard, filters, onFiltersChange, onToggle }) {
  const config = {
    operating: {
      kicker: "EQUIPO OPERANDO",
      title: "Actividades con equipo operando",
      description: "Trabajos que pueden ejecutarse sin detener el equipo.",
      tone: "ok",
    },
    stopped: {
      kicker: "PARADA REQUERIDA",
      title: "Actividades que requieren parada",
      description: "Trabajos que necesitan coordinación de detención.",
      tone: "stop",
    },
    backlog: {
      kicker: "BACKLOG",
      title: "Backlog disponible",
      description: "OT pendientes de programaciones anteriores disponibles para revisar.",
      tone: "backlog",
    },
  }[kind];

  const visible = matchesFilters(rows, filters);

  return (
    <section className={`v2-activity-section ${kind}`} aria-label={config.title}>
      <div className="v2-activity-head">
        <div>
          <span className="v2-kicker">{config.kicker}</span>
          <h3>{config.title}</h3>
          <p>{config.description}</p>
        </div>
        <Badge tone={config.tone}>{visible.length} disponibles</Badge>
      </div>

      <div className="v2-group-filters" aria-label={`Filtros de ${config.title}`}>
        <div className="v2-group-filter-title"><b>{config.kicker}</b></div>
        <label>
          <span>Área</span>
          <select
            value={filters.area}
            onChange={(event) => onFiltersChange({ area: event.target.value })}
          >
            <option value="">Todas las áreas</option>
            {(dashboard?.areas || []).map((area) => (
              <option key={area.codigo} value={area.codigo}>
                {area.codigo} · {area.nombre || area.codigo}
              </option>
            ))}
          </select>
        </label>
        <label>
          <span>Buscar</span>
          <input
            placeholder="OT, equipo o plan..."
            value={filters.search}
            onChange={(event) => onFiltersChange({ search: event.target.value })}
          />
        </label>
      </div>

      <div className="v2-table-wrap v2-program-table">
        <table>
          <thead>
            <tr>
              {kind === "backlog" && <th>Origen</th>}
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
            {visible.map((row) => (
              <tr key={row.orden_mantenimiento_id}>
                {kind === "backlog" && (
                  <td>
                    <div className="v2-backlog-origin">
                      <b>BACKLOG</b>
                      <small>{row.semana_origen_inicio || "Semana anterior"}</small>
                    </div>
                  </td>
                )}
                <td><b>{row.numero_ot || "SIN ASIGNAR"}</b></td>
                <td><Badge>{row.area_codigo || "—"}</Badge><small>{row.area_nombre || ""}</small></td>
                <td><b>{row.activo_codigo}</b><small>{row.activo_descripcion}</small></td>
                <td><span className="v2-plan">{row.plan_trabajo}</span><small>{row.descripcion_grupo || ""}</small></td>
                <td><b>{row.numero_personas_efectivo}</b></td>
                <td>{fmt(row.tiempo_min, 0)} min</td>
                <td><b>{fmt(row.hh, 1)}</b></td>
                <td>
                  <button type="button" className="v2-select" onClick={() => onToggle(row)}>
                    Seleccionar
                  </button>
                </td>
              </tr>
            ))}
            {!visible.length && (
              <tr>
                <td colSpan={kind === "backlog" ? 9 : 8} className="v2-empty">
                  No hay actividades con estos filtros.
                </td>
              </tr>
            )}
          </tbody>
        </table>
      </div>
    </section>
  );
}

export default function WeeklyProgrammingTest({ year, month, dashboard }) {
  const weeks = useMemo(() => monthWeeks(year, month), [year, month]);
  const week = useMemo(
    () => weeks.find((item) => !item.transition) || weeks[0],
    [weeks],
  );
  const [specialty, setSpecialty] = useState("MEC");
  const [data, setData] = useState(null);
  const [selected, setSelected] = useState(new Set());
  const [savedSelection, setSavedSelection] = useState(new Set());
  const [filters, setFilters] = useState(emptyFilters);
  const [loading, setLoading] = useState(false);
  const [message, setMessage] = useState("");
  const [error, setError] = useState("");

  async function load() {
    if (!week) return;
    try {
      setLoading(true);
      setError("");
      const result = await getV2WeekProgramming(week.from, week.to, specialty);
      setData(result);

      const key = storageKey(year, month, week, specialty);
      let stored = [];
      try {
        stored = JSON.parse(window.localStorage.getItem(key) || "[]");
      } catch {
        stored = [];
      }
      const ids = new Set((Array.isArray(stored) ? stored : []).map(Number));
      setSelected(ids);
      setSavedSelection(new Set(ids));
      setFilters(emptyFilters);
    } catch (cause) {
      setError(cause.message || "No se pudo cargar la semana de prueba.");
    } finally {
      setLoading(false);
    }
  }

  useEffect(() => {
    load();
  }, [year, month, week?.from, week?.to, specialty]);

  const allRows = useMemo(
    () => [
      ...(data?.operating || []),
      ...(data?.stopped || []),
      ...(data?.backlog || []),
    ],
    [data],
  );

  const rowMap = useMemo(
    () => new Map(allRows.map((row) => [Number(row.orden_mantenimiento_id), row])),
    [allRows],
  );

  useEffect(() => {
    if (!rowMap.size) return;
    setSelected((current) => new Set([...current].filter((id) => rowMap.has(Number(id)))));
    setSavedSelection((current) => new Set([...current].filter((id) => rowMap.has(Number(id)))));
  }, [rowMap]);

  const selectedRows = useMemo(
    () => [...selected]
      .map((id) => rowMap.get(Number(id)))
      .filter(Boolean)
      .sort((a, b) =>
        Number(b.requiere_parada) - Number(a.requiere_parada)
        || String(a.area_codigo || "").localeCompare(String(b.area_codigo || ""))
        || String(a.numero_ot || "").localeCompare(String(b.numero_ot || ""))
      ),
    [selected, rowMap],
  );

  const selectedHH = useMemo(
    () => selectedRows.reduce((sum, row) => sum + number(row.hh), 0),
    [selectedRows],
  );

  const target = number(data?.capacity?.target);
  const available = number(data?.capacity?.available);
  const effective = number(data?.capacity?.effective);
  const reserve = number(data?.capacity?.reserve);
  const initialMargin = number(data?.capacity?.initial_margin);
  const remaining = Math.max(0, target - selectedHH);
  const progress = target > 0 ? Math.min(100, (selectedHH / target) * 100) : 0;
  const techniciansAvailable = number(
    data?.capacity?.technicians_available,
    data?.capacity?.technicians || 0,
  );

  const dirty = useMemo(() => {
    if (selected.size !== savedSelection.size) return true;
    for (const id of selected) if (!savedSelection.has(id)) return true;
    return false;
  }, [selected, savedSelection]);

  function updateFilters(kind, patch) {
    setFilters((current) => updateGroupFilters(current, kind, patch));
  }

  function toggle(row) {
    const id = Number(row.orden_mantenimiento_id);
    setError("");
    setMessage("");
    setSelected((current) => {
      const result = toggleWeeklySelection({ selected: current, id, row, rowMap, target });
      if (result.error) {
        setError(
          `No se puede seleccionar esta actividad: llegarías a ${fmt(result.nextHH, 1)} H-H y la meta preventiva máxima es ${fmt(target, 1)} H-H.`,
        );
        return current;
      }
      return result.selected;
    });
  }

  function saveTest() {
    if (!selected.size) {
      setError("Selecciona al menos una actividad para guardar la simulación.");
      return;
    }
    const key = storageKey(year, month, week, specialty);
    window.localStorage.setItem(key, JSON.stringify([...selected]));
    setSavedSelection(new Set(selected));
    setMessage(
      `Prueba guardada en este navegador: ${selected.size} actividades · ${fmt(selectedHH, 1)} H-H. No se modificó Supabase.`,
    );
    setError("");
  }

  function restoreSaved() {
    setSelected(new Set(savedSelection));
    setMessage("Cambios de la simulación descartados.");
    setError("");
  }

  function resetTest() {
    const key = storageKey(year, month, week, specialty);
    window.localStorage.removeItem(key);
    setSelected(new Set());
    setSavedSelection(new Set());
    setFilters(emptyFilters);
    setMessage("Prueba reiniciada. No se modificó información productiva.");
    setError("");
  }

  const groups = [
    { kind: "stopped", rows: (data?.stopped || []).filter((row) => !selected.has(Number(row.orden_mantenimiento_id))) },
    { kind: "backlog", rows: (data?.backlog || []).filter((row) => !selected.has(Number(row.orden_mantenimiento_id))) },
    { kind: "operating", rows: (data?.operating || []).filter((row) => !selected.has(Number(row.orden_mantenimiento_id))) },
  ];

  const operatingHH = selectedRows
    .filter((row) => row.requiere_parada === false)
    .reduce((sum, row) => sum + number(row.hh), 0);
  const stoppedHH = selectedRows
    .filter((row) => row.requiere_parada === true)
    .reduce((sum, row) => sum + number(row.hh), 0);

  return (
    <div className="v2-stack v2-weekly-programming weekly-test-mode">
      <section className="v2-panel weekly-test-banner">
        <div>
          <span className="v2-kicker">MODO PRUEBA · AISLADO</span>
          <h3>Primera programación · Semana 1</h3>
          <p>
            Consulta datos reales, pero el guardado de esta pantalla es solo una simulación local.
            No crea programación, no mueve OT a backlog y no afecta cierres.
          </p>
        </div>
        <Badge tone="warn">NO PRODUCTIVO</Badge>
      </section>

      <section className="v2-panel v2-week-context">
        <div className="v2-section-head">
          <div>
            <span className="v2-kicker">SEMANA DE PRUEBA</span>
            <h3>{week ? `Semana 1 · ${week.label}` : "Semana 1"}</h3>
            <p>
              Corte operativo jueves → miércoles. Selecciona una especialidad para simular su primera programación.
            </p>
          </div>
          <Badge>{loading ? "Calculando..." : `${techniciansAvailable} técnicos disponibles`}</Badge>
        </div>

        <div className="v2-specialty-buttons weekly-test-specialties">
          {SPECS.map((item) => (
            <button
              type="button"
              key={item}
              className={specialty === item ? "active" : ""}
              onClick={() => setSpecialty(item)}
            >
              <b>{item}</b>
              <span>{SPEC_NAMES[item]}</span>
            </button>
          ))}
        </div>
      </section>

      <section className="v2-capacity-panel v2-capacity-summary">
        <div className="v2-capacity-cards">
          <div><span>H-H brutas</span><b>{fmt(available)}</b><small>100% turnos programados</small></div>
          <div><span>H-H efectivas</span><b>{fmt(effective)}</b><small>80% de H-H brutas</small></div>
          <div className="target"><span>Meta preventivo</span><b>{fmt(target)}</b><small>80% de H-H efectivas</small></div>
          <div className="selected"><span>H-H seleccionadas</span><b>{fmt(selectedHH)}</b><small>{selected.size} actividades</small></div>
          <div className={remaining <= 0.01 ? "complete" : "remaining"}>
            <span>Disponible para programar</span>
            <b>{fmt(remaining)}</b>
            <small>H-H preventivas</small>
          </div>
        </div>
        <div className="v2-capacity-details">
          <span>Tiempo no programable · 20% bruto <b>{fmt(initialMargin)}</b></span>
          <span>Correctivo / reserva · 20% efectivas <b>{fmt(reserve)}</b></span>
        </div>
        <div className="v2-progress-block">
          <div className="v2-progress-copy">
            <span>Uso de capacidad preventiva</span>
            <b>{fmt(progress, 1)}%</b>
          </div>
          <div className="v2-progress-track"><i style={{ width: `${progress}%` }} /></div>
          <div className="v2-progress-foot">
            <span>{fmt(selectedHH)} H-H seleccionadas</span>
            <span>{fmt(target)} H-H máximo preventivo</span>
          </div>
        </div>
        {available === 0 && (
          <div className="v2-warning">
            Esta especialidad no tiene disponibilidad cargada para la semana de prueba.
          </div>
        )}
      </section>

      <section className="v2-selected-section">
        <div className="v2-selected-head">
          <div>
            <span className="v2-kicker">SELECCIÓN DE PRUEBA</span>
            <h3>Actividades seleccionadas para Semana 1</h3>
            <p>Esta selección todavía no forma parte de la programación real.</p>
          </div>
          <div className="v2-selected-totals">
            <span><b>{selectedRows.length}</b> actividades</span>
            <span><b>{fmt(operatingHH)}</b> H-H operando</span>
            <span><b>{fmt(stoppedHH)}</b> H-H detenido</span>
            <span className="total"><b>{fmt(selectedHH)}</b> H-H total</span>
          </div>
        </div>

        <div className="v2-table-wrap v2-selected-table">
          <table>
            <thead>
              <tr>
                <th>Condición</th><th>Origen</th><th>OT</th><th>Área</th><th>Equipo</th>
                <th>Plan de trabajo</th><th>Personas</th><th>Tiempo</th><th>H-H</th><th>Acción</th>
              </tr>
            </thead>
            <tbody>
              {selectedRows.map((row) => (
                <tr key={row.orden_mantenimiento_id}>
                  <td>{row.requiere_parada ? <Badge tone="stop">Equipo detenido</Badge> : <Badge tone="ok">Equipo funcionando</Badge>}</td>
                  <td>{row.origen === "BACKLOG" || row.origen_backlog ? <Badge tone="backlog">BACKLOG</Badge> : <Badge>PMP DEL MES</Badge>}</td>
                  <td><b>{row.numero_ot || "SIN ASIGNAR"}</b></td>
                  <td><Badge>{row.area_codigo || "—"}</Badge><small>{row.area_nombre || ""}</small></td>
                  <td><b>{row.activo_codigo}</b><small>{row.activo_descripcion}</small></td>
                  <td><span className="v2-plan">{row.plan_trabajo}</span><small>{row.descripcion_grupo || ""}</small></td>
                  <td><b>{row.numero_personas_efectivo}</b></td>
                  <td>{fmt(row.tiempo_min, 0)} min</td>
                  <td><b>{fmt(row.hh)}</b></td>
                  <td><button type="button" className="v2-unselect" onClick={() => toggle(row)}>Quitar</button></td>
                </tr>
              ))}
              {!selectedRows.length && (
                <tr><td colSpan="10" className="v2-empty">Aún no has seleccionado actividades para la prueba.</td></tr>
              )}
            </tbody>
          </table>
        </div>
      </section>

      <section className="v2-save-program v2-program-action-bar weekly-test-actions">
        <div className="v2-save-program-copy">
          <span className="v2-kicker">GUARDADO DE SIMULACIÓN</span>
          <h3>{dirty ? "Hay cambios de prueba sin guardar" : "Prueba guardada / sin cambios"}</h3>
          <div className="v2-save-summary">
            <span><b>{fmt(selectedHH)}</b> H-H seleccionadas</span>
            <span><b>{fmt(target)}</b> H-H capacidad preventiva</span>
            <span><b>{fmt(remaining)}</b> H-H disponibles</span>
          </div>
          {error && <div className="v2-error v2-error-bottom">{error}</div>}
          {message && <div className="v2-success v2-success-bottom">{message}</div>}
        </div>
        <div className="v2-report-actions">
          <button type="button" className="v2-primary" disabled={!dirty || !selected.size} onClick={saveTest}>
            Guardar prueba
          </button>
          <button type="button" disabled={!dirty} onClick={restoreSaved}>Descartar cambios</button>
          <button type="button" onClick={resetTest}>Reiniciar prueba</button>
        </div>
      </section>

      <section className="v2-panel v2-available-work">
        <div className="v2-program-toolbar">
          <div>
            <span className="v2-kicker">ACTIVIDADES DISPONIBLES</span>
            <h3>Cartera real consultada en modo prueba</h3>
          </div>
        </div>
        {groups.map((group) => (
          <ActivityGroup
            key={group.kind}
            {...group}
            dashboard={dashboard}
            filters={filters[group.kind]}
            onFiltersChange={(patch) => updateFilters(group.kind, patch)}
            onToggle={toggle}
          />
        ))}
      </section>
    </div>
  );
}
