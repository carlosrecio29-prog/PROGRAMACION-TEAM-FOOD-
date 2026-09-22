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
    <section className="v2-hero advance-stop-hero">
      <div>
        <span className="v2-kicker">PLANIFICACIÓN ANTICIPADA · MANTENIMIENTO</span>
        <h2>Preparación de paradas del mes siguiente</h2>
        <p>Identifica los planes con equipo detenido antes de generar las OT.
          Entrega el Excel al planeador para coordinar las ventanas de parada.</p>
      </div>
      <div className="advance-stop-hero-chip">ANÁLISIS PROVISIONAL · SOLO LECTURA</div>
    </section>

    <section className="v2-panel">
      <div className="v2-section-head">
        <div><span className="v2-kicker">PASO 1 · PERÍODO Y ARCHIVO</span>
          <h3>Cargar Lista de Calendario provisional</h3>
          <p>Se acepta con número de OT o sin OT. El resultado aparece automáticamente
            al seleccionar el Excel.</p></div>
      </div>
      <div className="advance-stop-form">
        <label>Mes que necesitas preparar
          <select value={periodMonth} onChange={e => setPeriodMonth(Number(e.target.value))}>
            {MONTHS.map((name, i) => <option key={name} value={i + 1}>{name}</option>)}
          </select>
        </label>
        <label>Año
          <input type="number" min="2020" max="2100" value={periodYear}
            onChange={e => setPeriodYear(Number(e.target.value))}/>
        </label>
        <label className="advance-stop-file">Lista de Calendario (.xlsx)
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
      <div className="v2-success advance-stop-safe">
        Esta carga <b>NO reemplaza el PMP operativo</b> y no modifica programaciones,
        cierres, órdenes, backlog ni maestros. El mes seleccionado identifica el informe;
        no se inventan fechas de parada ausentes en el archivo.
      </div>
      {file && <p className="advance-stop-upload-status">
        <b>Archivo:</b> {file.name} · <b>Período:</b> {MONTHS[periodMonth - 1]} {periodYear}
        {loading ? " · Analizando planes y equipos..." : preview ? " · Análisis listo" : ""}
      </p>}
      {error && <div className="v2-error" role="alert">{error}</div>}
    </section>

    {preview && <section className="v2-panel">
      <div className="v2-section-head">
        <div><span className="v2-kicker">PASO 2 · CLASIFICACIÓN DEL MAESTRO</span>
          <h3>Actividades del período {MONTHS[periodMonth - 1]} {periodYear}</h3>
          <p>Criterio: <b>TiempoParada &gt; 0 = EQUIPO DETENIDO</b>;
             <b> TiempoParada = 0 = OPERANDO</b>; sin dato o sin plan maestro = SIN DEFINIR.</p>
        </div>
        <button type="button" className="v2-primary"
          disabled={downloading || loading} onClick={exportFile}>
          {downloading ? "Generando Excel..." : "Descargar Excel para el planeador"}
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
      <div className="advance-stop-note">
        {num(preview.total_archivo)} filas del archivo · {num(preview.sin_ot)} actividades sin número de OT ·
        {num(preview.excluidos_operacion)} registros de OPERACIÓN excluidos.
        <br/>Las actividades <b>SIN DEFINIR</b> no se consideran operando ni detenidas
        hasta que el planeador confirme el maestro. El Excel conserva <b>todas</b>
        las actividades, aunque filtres la pantalla.
      </div>
      {preview.sin_definir > 0 && <div className="advance-stop-note" role="status">
        <b>¿Por qué aparecen SIN DEFINIR?</b> El sistema diferencia
        <b> {num(preview.sin_definir_por_tiempo)} actividades</b> cuyo plan existe,
        pero tiene TiempoParada vacío;
        <b> {num(preview.sin_definir_por_plan)}</b> cuyo plan no coincide con el maestro
        <b> {num(preview.sin_definir_por_ambiguo)}</b> con coincidencia ambigua
        y <b>{num(preview.sin_definir_por_invalido)}</b> con tiempo inválido.
        No se asume parada ni operación hasta revisar el dato correcto.
      </div>}
      <div className="advance-stop-filters">
        {condition === "SIN DEFINIR" && <label>Motivo de revisión
          <select value={reason} onChange={e => setReason(e.target.value)}>
            <option value="">Todos los motivos</option>
            <option value="TIEMPO PARADA VACÍO">TiempoParada vacío en maestro</option>
            <option value="PLAN NO ENCONTRADO">Plan no encontrado</option>
            <option value="PLAN AMBIGUO">Plan ambiguo</option>
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
        <span><b>{num(visible.length)}</b> coincidencias</span>
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
      <h3>¿Qué recibirá el planeador?</h3>
      <p>Un Excel con pestañas <b>RESUMEN</b>, <b>EQUIPO DETENIDO</b>,
        <b>OPERANDO</b> y <b>SIN DEFINIR</b>. Cada fila incluirá OT si existe,
        equipo, área, criticidad, especialidad, plan, tiempos y HH estimadas.</p>
      <p>La clasificación no depende de que el software haya asignado el número de OT.</p>
    </section>}
  </div>;
}
