import { useEffect, useMemo, useState } from "react";
import { downloadAdvanceStopsExcel, previewAdvanceStops } from "../api";
import "./advanceStops.css";

const MONTHS = ["Enero","Febrero","Marzo","Abril","Mayo","Junio","Julio",
  "Agosto","Septiembre","Octubre","Noviembre","Diciembre"];
const LABELS = {
  "EQUIPO DETENIDO": "Equipo detenido",
  OPERANDO: "Operando",
  "SIN DEFINIR": "Sin definir",
};
const num = value => Number(value || 0).toLocaleString("es-CO");
const decimal = value => value === null || value === undefined
  ? "—" : Number(value).toLocaleString("es-CO", { maximumFractionDigits: 2 });

export default function AdvanceStops({ year, month }) {
  // Select the month AFTER the current planning period; year turnover supported.
  const [periodYear, setPeriodYear] = useState(
    () => new Date(year, month, 1).getFullYear()
  );
  const [periodMonth, setPeriodMonth] = useState(
    () => new Date(year, month, 1).getMonth() + 1
  );
  const [file, setFile] = useState(null);
  const [preview, setPreview] = useState(null);
  const [error, setError] = useState("");
  const [loading, setLoading] = useState(false);
  const [downloading, setDownloading] = useState(false);
  const [condition, setCondition] = useState("EQUIPO DETENIDO");
  const [reason, setReason] = useState("");
  const [specialty, setSpecialty] = useState("");
  const [search, setSearch] = useState("");

  // Uploading a file immediately previews it. No button to "import" a live PMP.
  useEffect(() => {
    if (!file) {
      setPreview(null);
      return;
    }
    const controller = new AbortController();
    setPreview(null);
    setError("");
    setLoading(true);
    previewAdvanceStops(file, periodYear, periodMonth, controller.signal)
      .then(result => {
        if (!controller.signal.aborted) setPreview(result);
      })
      .catch(e => {
        if (!controller.signal.aborted)
          setError(e.message || "No se pudo analizar la Lista de Calendario.");
      })
      .finally(() => {
        if (!controller.signal.aborted) setLoading(false);
      });
    return () => controller.abort();
  }, [file, periodYear, periodMonth]);

  const specs = useMemo(() => Array.from(new Set(
    (preview?.filas || []).map(r => r.especialidad).filter(Boolean)
  )).sort(), [preview]);
  const visible = useMemo(() => (preview?.filas || []).filter(row => {
    if (condition && row.condicion !== condition) return false;
    if (reason && row.motivo_sin_definir !== reason) return false;
    if (specialty && row.especialidad !== specialty) return false;
    if (search) {
      const text = [row.numero_ot, row.activo_codigo, row.activo_descripcion,
        row.plan_clave_software, row.descripcion_plan, row.area_codigo,
        row.cronograma_planeacion].join(" ").toLowerCase();
      if (!text.includes(search.trim().toLowerCase())) return false;
    }
    return true;
  }), [preview, condition, reason, specialty, search]);

  async function exportFile() {
    if (!file || !preview || loading || downloading) return;
    setDownloading(true);
    setError("");
    try {
      await downloadAdvanceStopsExcel(file, periodYear, periodMonth);
    } catch (e) {
      setError(e.message || "No se pudo descargar el Excel.");
    } finally {
      setDownloading(false);
    }
  }

  return <div className="v2-stack advance-stop-page">
    <section className="v2-panel advance-stop-upload-panel">
      <div className="v2-section-head">
        <div>
          <span className="v2-kicker">PASO 1 · PREPARAR ANÁLISIS</span>
          <h3>Selecciona el período y carga la Lista de Calendario</h3>
          <p>Este análisis es provisional y de solo lectura. Puedes usar un archivo con OT o sin OT.</p>
        </div>
        <span className="advance-stop-readonly">SOLO LECTURA</span>
      </div>

      <div className="advance-stop-input-layout">
        <div className="advance-stop-period-card">
          <span className="advance-stop-card-label">PERÍODO A PREPARAR</span>
          <div className="advance-stop-period-fields">
            <label>Mes
              <select value={periodMonth} onChange={e => setPeriodMonth(Number(e.target.value))}>
                {MONTHS.map((name, i) => <option key={name} value={i + 1}>{name}</option>)}
              </select>
            </label>
            <label>Año
              <input type="number" min="2020" max="2100" value={periodYear}
                onChange={e => setPeriodYear(Number(e.target.value))}/>
            </label>
          </div>
          <strong>{MONTHS[periodMonth - 1]} {periodYear}</strong>
          <small>Mes que se enviará al planeador para preparar las ventanas de parada.</small>
        </div>

        <label className={"advance-stop-dropzone " + (file ? "loaded" : "")}>
          <span className="advance-stop-dropzone-icon" aria-hidden="true">↑</span>
          <span className="advance-stop-dropzone-copy">
            <b>{file ? file.name : "Seleccionar Lista de Calendario"}</b>
            <small>{file ? "Archivo cargado · puedes reemplazarlo seleccionando otro" : "Archivo Excel .xlsx · el análisis inicia automáticamente"}</small>
          </span>
          <span className="advance-stop-dropzone-action">{file ? "Cambiar archivo" : "Buscar archivo"}</span>
          <input type="file" accept=".xlsx"
            onChange={e => {
              setFile(e.target.files?.[0] || null);
              setCondition("EQUIPO DETENIDO");
              setReason("");
              setSpecialty("");
              setSearch("");
            }}/>
        </label>
      </div>

      <div className="advance-stop-safety-strip">
        <span aria-hidden="true">✓</span>
        <p>
          <b>No modifica la operación:</b> esta carga no reemplaza PMP, programaciones,
          cierres, órdenes, backlog ni maestros.
        </p>
      </div>

      {file && <div className={"advance-stop-file-status " + (loading ? "loading" : preview ? "ready" : "")}>
        <span className="advance-stop-file-status-dot" />
        <div>
          <b>{loading ? "Analizando planes y equipos..." : preview ? "Análisis listo" : "Archivo seleccionado"}</b>
          <small>{file.name} · {MONTHS[periodMonth - 1]} {periodYear}</small>
        </div>
      </div>}
      {error && <div className="v2-error" role="alert">{error}</div>}
    </section>

    {preview && <section className="v2-panel advance-stop-results-panel">
      <div className="v2-section-head advance-stop-results-head">
        <div>
          <span className="v2-kicker">PASO 2 · RESULTADO DEL ANÁLISIS</span>
          <h3>Clasificación de actividades · {MONTHS[periodMonth - 1]} {periodYear}</h3>
          <p>Selecciona una condición para filtrar el listado y revisar los equipos que requieren coordinación.</p>
        </div>
        <button type="button" className="v2-primary advance-stop-export"
          disabled={downloading || loading} onClick={exportFile}>
          <span aria-hidden="true">↓</span>
          {downloading ? "Generando Excel..." : "Exportar para planeador"}
        </button>
      </div>
      <div className="advance-stop-cards">
        <button type="button" className={condition === "EQUIPO DETENIDO" ? "active stopped" : "stopped"}
          onClick={() => { setCondition("EQUIPO DETENIDO"); setReason(""); }}>
          <small>REQUIEREN PARADA</small><strong>{num(preview.equipo_detenido)}</strong><span>Equipo detenido</span>
        </button>
        <button type="button" className={condition === "OPERANDO" ? "active running" : "running"}
          onClick={() => { setCondition("OPERANDO"); setReason(""); }}>
          <small>NO REQUIEREN PARADA</small><strong>{num(preview.operando)}</strong><span>Operando</span>
        </button>
        <button type="button" className={condition === "SIN DEFINIR" ? "active unknown" : "unknown"}
          onClick={() => { setCondition("SIN DEFINIR"); setReason(""); }}>
          <small>REVISAR CON PLANEADOR</small><strong>{num(preview.sin_definir)}</strong><span>Sin definir</span>
        </button>
        <button type="button" className={!condition ? "active" : ""}
          onClick={() => { setCondition(""); setReason(""); }}>
          <small>REGISTROS DE MANTENIMIENTO</small><strong>{num(preview.total_mantenimiento)}</strong><span>Ver todos</span>
        </button>
      </div>
      {preview.maestro_planes_operando === 0 && <div className="v2-warning" role="alert">
        <b>ATENCIÓN: el maestro no registra ningún TiempoParada = 0.</b>{" "}
        {num(preview.maestro_planes_sin_tiempo_parada)} planes de mantenimiento
        tienen el tiempo de parada vacío en la base actual. Por eso este análisis
        no puede identificar actividades OPERANDO aunque el Excel las contenga.
        <b> Vacío no significa 0.</b> Debes restaurar los ceros desde un Plan de
        Trabajo que los incluya o confirmar la condición con el planeador.
        No se han supuesto tiempos para completar el listado.
      </div>}
      <div className="advance-stop-summary-strip">
        <span><b>{num(preview.total_archivo)}</b><small>Filas del archivo</small></span>
        <span><b>{num(preview.sin_ot)}</b><small>Sin número de OT</small></span>
        <span><b>{num(preview.excluidos_operacion)}</b><small>OPERACIÓN excluidas</small></span>
        <span><b>{num(preview.total_mantenimiento)}</b><small>Mantenimiento analizado</small></span>
      </div>

      <details className="advance-stop-method">
        <summary>
          <span>
            <b>Criterio de clasificación</b>
            <small>Ver cómo se determina Operando, Equipo detenido y Sin definir</small>
          </span>
        </summary>
        <p>
          <b>TiempoParada &gt; 0</b> = EQUIPO DETENIDO ·
          <b> TiempoParada = 0</b> = OPERANDO ·
          sin dato, valor inválido o plan sin coincidencia = SIN DEFINIR.
          Las actividades SIN DEFINIR no se asumen como operando ni detenidas.
          El Excel exportado conserva el listado completo aunque filtres la pantalla.
        </p>
      </details>
      {preview.sin_definir > 0 && <div className="advance-stop-note" role="status">
        <b>¿Por qué aparecen SIN DEFINIR?</b> El sistema diferencia
        <b> {num(preview.sin_definir_por_tiempo)} actividades</b> cuyo plan existe,
        pero tiene TiempoParada vacío;
        <b> {num(preview.sin_definir_por_plan)}</b> cuyo plan no coincide con el maestro
        y <b>{num(preview.sin_definir_por_invalido)}</b> con tiempo inválido.
        No se asume parada ni operación hasta revisar el dato correcto.
      </div>}
      <div className="advance-stop-list-head">
        <div>
          <span className="v2-kicker">PASO 3 · REVISIÓN DE EQUIPOS</span>
          <h3>${LABELS[condition] || "Todas las actividades"}</h3>
        </div>
        <span><b>{num(visible.length)}</b> resultados visibles</span>
      </div>
      <div className="advance-stop-filters">
        {condition === "SIN DEFINIR" && <label>Motivo de revisión
          <select value={reason} onChange={e => setReason(e.target.value)}>
            <option value="">Todos los motivos</option>
            <option value="TIEMPO PARADA VACÍO">TiempoParada vacío en maestro</option>
            <option value="PLAN NO ENCONTRADO">Plan no encontrado</option>
            <option value="TIEMPO PARADA INVÁLIDO">TiempoParada inválido</option>
          </select>
        </label>}
        <label>Especialidad
          <select value={specialty} onChange={e => setSpecialty(e.target.value)}>
            <option value="">Todas</option>
            {specs.map(spec => <option key={spec} value={spec}>{spec}</option>)}
          </select>
        </label>
        <label>Buscar actividad, equipo u OT
          <input type="search" value={search}
            onChange={e => setSearch(e.target.value)}
            placeholder="Ej.: motor, chiller, BA-…, OT-…"/>
        </label>
      </div>
      <div className="v2-table-wrap advance-stop-table">
        <table>
          <thead><tr>
            <th>Condición</th><th>OT</th><th>Especialidad</th><th>Área</th>
            <th>Equipo</th><th>Criticidad</th><th>Plan de trabajo</th>
            <th>Tiempo parada</th><th>HH est.</th><th>Motivo</th><th>Observación</th>
          </tr></thead>
          <tbody>
            {visible.slice(0, 300).map((row, i) => <tr key={row.fila_origen + "-" + i}>
              <td><span className={"advance-stop-condition " +
                (row.condicion === "EQUIPO DETENIDO" ? "stopped" :
                  row.condicion === "OPERANDO" ? "running" : "unknown")}>
                {LABELS[row.condicion]}
              </span></td>
              <td>{row.numero_ot || <em>Sin OT</em>}</td>
              <td>{row.especialidad}</td><td>{row.area_codigo || "—"}</td>
              <td title={row.activo_descripcion}>{row.activo_codigo}</td>
              <td>{row.criticidad || "—"}</td>
              <td title={row.descripcion_plan}>{row.plan_clave_software}</td>
              <td>{row.tiempo_parada_min === null ? "Sin definir" :
                decimal(row.tiempo_parada_min) + " min"}</td>
              <td>{decimal(row.hh_estimadas)}</td>
              <td>{row.motivo_sin_definir || "—"}</td>
              <td>{row.observacion || "—"}</td>
            </tr>)}
            {!visible.length && <tr><td colSpan="11">No hay actividades para estos filtros.</td></tr>}
          </tbody>
        </table>
      </div>
      {visible.length > 300 && <p>
        Se muestran 300 de {num(visible.length)} coincidencias para mantener ágil la página.
        El Excel descargado incluye el listado completo.
      </p>}
    </section>}
    {!file && <section className="v2-panel advance-stop-empty">
      <div className="advance-stop-empty-icon" aria-hidden="true">▦</div>
      <div>
        <span className="v2-kicker">RESULTADO ESPERADO</span>
        <h3>¿Qué recibirá el planeador?</h3>
        <p>Un Excel organizado con <b>RESUMEN</b>, <b>EQUIPO DETENIDO</b>,
          <b>OPERANDO</b> y <b>SIN DEFINIR</b>, incluyendo equipo, área, criticidad,
          especialidad, plan, tiempos y H-H estimadas.</p>
        <small>La clasificación funciona aunque la actividad todavía no tenga número de OT.</small>
      </div>
    </section>}
  </div>;
}
