import {useEffect,useMemo,useState} from "react";
import {downloadV2ProgressPdf,getV2Progress,getV2ProgressPdfUrl} from "../api";
import "./progressDashboard.css";

const NAMES = {MEC:"Mecánica",ELE:"Eléctrica",MET:"Metrología",SER:"Servicios"};
const number = x => Number(x || 0);
const count = x => number(x).toLocaleString("es-CO",{maximumFractionDigits:0});
const hh = x => number(x).toLocaleString("es-CO",{minimumFractionDigits:1,maximumFractionDigits:2});
const pct = x => x === null || x === undefined ? "Por verificar" : number(x).toLocaleString("es-CO",{maximumFractionDigits:1}) + "%";
const dateLabel = s => s ? s.split("-").reverse().join("/") : "—";

function Card({label,value,extra,tone=""}){
  return <article className={"v2-progress-metric " + tone}>
    <div className="v2-progress-metric-top">
      <span>{label}</span>
      <i aria-hidden="true" />
    </div>
    <strong>{value}</strong>
    <small>{extra}</small>
  </article>;
}

export default function ProgressDashboard({year,month,full=false,onOpenMonthly}){
  const [data,setData]=useState(null);
  const [loading,setLoading]=useState(true);
  const [error,setError]=useState("");
  const [pdfError,setPdfError]=useState("");
  const [downloading,setDownloading]=useState("");
  const [specialty,setSpecialty]=useState("");
  const [revision,setRevision]=useState(0);
  useEffect(()=>{
    let cancelled=false;
    setLoading(true);setError("");
    getV2Progress(year,month).then(result=>{if(!cancelled)setData(result);})
      .catch(err=>{if(!cancelled)setError(err.message);})
      .finally(()=>{if(!cancelled)setLoading(false);});
    return ()=>{cancelled=true;};
  },[year,month,revision]);
  const weeks=useMemo(()=> (data?.weeks||[]).filter(row=>!specialty||row.especialidad===specialty),[data,specialty]);
  const top=data?.monthly||{};
  const totals=data?.weekly_totals||{};
  const overallProgress=Math.max(0,Math.min(100,number(top.progress_ot_pct||0)));
  const showReport=async(programmingId=null)=>{
    const key=programmingId===null?"month":String(programmingId);
    try{setDownloading(key);setPdfError("");await downloadV2ProgressPdf(year,month,programmingId);}
    catch(e){setPdfError(e.message||"No fue posible descargar el reporte");}
    finally{setDownloading("");}
  };
  if(loading&&!data) return <section className="v2-panel">Cargando avance semanal y mensual...</section>;
  if(error&&!data) return <section className="v2-panel v2-error">
    No se pudo cargar el progreso: {error}
    <button type="button" onClick={()=>setRevision(x=>x+1)}>Reintentar</button>
  </section>;
  return <section className="v2-progress-dashboard v2-stack">
    {pdfError&&<div className="v2-error" role="alert" style={{
      position:"sticky",top:8,zIndex:10,padding:16,borderRadius:10
    }}>
      <b>No se pudo descargar el PDF:</b> {pdfError}
      <a href={getV2ProgressPdfUrl(year,month)}
        target="_blank" rel="noopener noreferrer"
        style={{display:"inline-block",marginLeft:12,textDecoration:"underline"}}>
        Abrir PDF mensual directamente
      </a>
    </div>}
    <div className="v2-panel v2-progress-overview-panel">
      <div className="v2-section-head">
        <div>
          <span className="v2-kicker">SEGUIMIENTO DEL PERIODO</span>
          <h3>{full?"Informe general de cierre mensual":"Avance de programación y cierres"}</h3>
          <p>Lectura ejecutiva del avance registrado en programación, cierres y H-H estimadas.</p>
        </div>
        <button type="button" className="v2-progress-refresh" onClick={()=>setRevision(x=>x+1)} disabled={loading}>
          {loading?"Actualizando...":"Actualizar avance"}
        </button>
      </div>

      {top.contains_future_week_closures&&<div className="v2-warning" role="note">
        CIERRE DE PRUEBA / ANTICIPADO: existen semanas cerradas con fecha de fin posterior a hoy.
        No presentar este informe como cierre operativo definitivo del mes.
      </div>}

      <div className="v2-progress-overview">
        <div className="v2-progress-focus">
          <div className="v2-progress-ring" style={{"--progress":overallProgress+"%"}}>
            <div>
              <strong>{pct(top.progress_ot_pct)}</strong>
              <span>OT finalizadas</span>
            </div>
          </div>
          <div className="v2-progress-focus-copy">
            <span className="v2-kicker">ESTADO GENERAL</span>
            <h4>{count(top.weeks_closed)} de {count(top.weeks_total)} programaciones cerradas</h4>
            <p>{top.all_weeks_closed
              ?"Periodo completamente cerrado para las especialidades programadas."
              :"Informe parcial: aún quedan programaciones sin cierre."}</p>
            <div className="v2-progress-focus-tags">
              <span><b>{count(top.programmed)}</b> OT programadas</span>
              <span><b>{count(top.finalized)}</b> finalizadas</span>
              <span><b>{count(top.pending)}</b> pendientes</span>
            </div>
          </div>
        </div>

        <div className="v2-progress-metrics">
          <Card label="OT únicas programadas" value={count(top.programmed)} extra="Sin duplicar OT reprogramadas"/>
          <Card label="OT finalizadas" value={count(top.finalized)} extra={pct(top.progress_ot_pct)+" de OT únicas"} tone="success"/>
          <Card label="OT pendientes" value={count(top.pending)} extra="Según el último cierre del período" tone="warning"/>
          <Card label="No encontradas" value={count(top.not_found)} extra="Requieren conciliación" tone={number(top.not_found)?"danger":""}/>
          <Card label="Registros PMP" value={count(top.pmp_count)} extra="Mantenimiento del mes, sin OPERACIÓN"/>
          <Card label="H-H finalizadas est." value={hh(totals.hh_finalized)} extra={"De "+hh(totals.hh_programmed)+" H-H programadas"} tone="success"/>
        </div>
      </div>

      <div className="v2-progress-note">
        <b>Criterio del tablero:</b> el consolidado superior cuenta cada OT una vez según su último cierre del período.
        El análisis semanal cuenta cada vez que fue programada. Las H-H mostradas son estimadas, no horas reales ejecutadas.
      </div>
    </div>
    <section className="v2-panel v2-progress-trend-panel">
      <div className="v2-section-head">
        <div>
          <span className="v2-kicker">TENDENCIA SEMANAL</span>
          <h3>Avance por especialidad</h3>
          <p>Cortes de jueves a miércoles · OT programadas frente a finalizadas.</p>
        </div>
        <label className="v2-progress-filter">
          <span>Especialidad</span>
          <select value={specialty} onChange={e=>setSpecialty(e.target.value)}>
            <option value="">Todas las especialidades</option>
            {Object.entries(NAMES).map(([code,name])=><option key={code} value={code}>{name}</option>)}
          </select>
        </label>
      </div>

      {weeks.length===0
        ? <div className="v2-progress-empty">
            <b>Aún no hay programación para este filtro.</b>
            <span>La tendencia aparecerá a medida que se guarden y cierren semanas.</span>
          </div>
        : <>
          <div className="v2-progress-chart" aria-label="Avance semanal por OT programadas y finalizadas">
            {weeks.map(week=>{
              const closed=week.estado==="CERRADA";
              const progress=Math.max(0,Math.min(100,number(week.progress_ot_pct||0)));
              return <div className="v2-progress-chart-row" key={week.programming_id}>
                <div className="v2-progress-chart-label">
                  <div>
                    <b>{NAMES[week.especialidad]||week.especialidad}</b>
                    <span className={"v2-progress-status "+(closed?"closed":"open")}>{closed?"Cerrada":"Abierta"}</span>
                  </div>
                  <span>{dateLabel(week.week_from)} – {dateLabel(week.week_to)}</span>
                </div>
                <div className="v2-progress-week-body">
                  <div className="v2-progress-week-copy">
                    <span>{count(week.programmed)} OT programadas</span>
                    <span>{closed?count(week.finalized)+" finalizadas":"Pendiente de cierre"}</span>
                  </div>
                  <div className="v2-progress-chart-track">
                    <div className="v2-progress-chart-done" style={{width:(closed?progress:0)+"%"}}/>
                  </div>
                </div>
                <strong>{closed?pct(week.progress_ot_pct):"—"}</strong>
              </div>;
            })}
          </div>

          <details className="v2-progress-detail">
            <summary>
              <span>
                <b>Ver detalle semanal completo</b>
                <small>OT, backlog, H-H y reportes por corte</small>
              </span>
            </summary>
            <div className="v2-table-wrap">
              <table>
                <thead><tr><th>Corte</th><th>Especialidad</th><th>Estado</th><th>Programadas</th><th>Finalizadas</th>
                  <th>Pendientes</th><th>No encontradas</th><th>Backlog programado</th><th>HH prog.</th><th>HH fin. est.</th><th>OT %</th><th>HH %</th><th>Reporte</th></tr></thead>
                <tbody>{weeks.map(w=><tr key={w.programming_id}>
                  <td>{dateLabel(w.week_from)} – {dateLabel(w.week_to)}</td>
                  <td><b>{NAMES[w.especialidad]||w.especialidad}</b></td>
                  <td><span className={"v2-progress-status "+(w.estado==="CERRADA"?"closed":"open")}>{w.estado}</span></td>
                  <td>{count(w.programmed)}</td><td>{w.estado==="CERRADA"?count(w.finalized):"—"}</td>
                  <td>{w.estado==="CERRADA"?count(w.pending):"—"}</td><td>{w.estado==="CERRADA"?count(w.not_found):"—"}</td>
                  <td>{count(w.origin_backlog)}</td><td>{hh(w.hh_programmed)}</td>
                  <td>{w.estado==="CERRADA"?hh(w.hh_finalized):"—"}</td>
                  <td>{pct(w.progress_ot_pct)}</td><td>{pct(w.progress_hh_pct)}</td>
                  <td><div className="v2-progress-row-actions">
                    <button type="button" disabled={!!downloading} onClick={()=>showReport(w.programming_id)}>
                      {downloading===String(w.programming_id)?"Generando...":"PDF"}
                    </button>
                    <a href={getV2ProgressPdfUrl(year,month,w.programming_id)} target="_blank" rel="noopener noreferrer">Abrir</a>
                  </div></td>
                </tr>)}</tbody>
              </table>
            </div>
          </details>
        </>
      }
    </section>
    {full&&<section className="v2-panel">
      <div className="v2-section-head"><div><span className="v2-kicker">CONSOLIDADO MENSUAL</span>
        <h3>Cómo terminó el mes</h3><p>Resultado de cada orden distinta según su última programación del periodo.</p>
      </div></div>
      <div className="v2-progress-metrics">
        <Card label="Registros PMP mantenimiento" value={count(top.pmp_count)} extra="Incluye órdenes no programadas"/>
        <Card label="OT distintas programadas" value={count(top.programmed)} extra="Incluye reprogramadas solo una vez"/>
        <Card label="Registros PMP sin programación" value={count(top.not_programmed)} extra="No incluye órdenes heredadas de otros meses"/>
        <Card label="OT cerradas" value={count(top.finalized)} extra={pct(top.progress_ot_pct)+" de las programadas"} tone="success"/>
        <Card label="OT abiertas en último cierre" value={count(top.pending)} extra="No equivale a toda la cartera sin ejecutar" tone="warning"/>
        <Card label="OT sin encontrar / verificar" value={count(top.not_found+top.unchecked)} extra="Conciliación y semanas abiertas" tone="warning"/>
      </div>
      <h3>Pendientes y no encontradas del último cierre</h3>
      <div className="v2-table-wrap"><table>
        <thead><tr><th>OT</th><th>Especialidad</th><th>Equipo</th><th>Plan de trabajo</th><th>Estado cierre</th><th>Resultado</th><th>HH estimadas</th></tr></thead>
        <tbody>{(data?.unresolved||[]).slice(0,40).map((o,i)=><tr key={i}>
          <td>{o.numero_ot}</td><td>{o.especialidad}</td><td>{o.activo}</td><td>{o.plan}</td>
          <td>{o.estado_cierre}</td><td>{o.resultado}</td><td>{hh(o.hh_estimada)}</td></tr>)}
          {!data?.unresolved?.length&&<tr><td colSpan="7">No hay OT pendientes en los últimos cierres registrados.</td></tr>}
        </tbody></table></div>
      {(data?.unresolved?.length||0)>40&&<p>Se muestran 40 OT. El reporte PDF incluye hasta 80 y el contador resume todas.</p>}
    </section>}
    <section className="v2-panel v2-progress-report">
      <div><span className="v2-kicker">EXPORTACIÓN</span>
        <h3>Informe {full?"consolidado mensual":"de avance mensual"} · {String(month).padStart(2,"0")}/{year}</h3>
        <p>PDF con indicadores, desglose semanal, avance por OT y HH, y criterios de cálculo.
          {top.all_weeks_closed?" Todas las programaciones registradas están cerradas.":" Se identificará como informe parcial."}</p>
      </div>
      <div className="v2-progress-report-actions">
        <button type="button" className="v2-primary" disabled={!weeks.length||!!downloading}
          onClick={()=>showReport()}>
          {downloading==="month"?"Generando...":"Descargar informe mensual PDF"}
        </button>
        <a href={getV2ProgressPdfUrl(year,month)} target="_blank" rel="noopener noreferrer"
          style={{alignSelf:"center",textDecoration:"underline"}}>Abrir PDF directamente</a>
        {!full&&onOpenMonthly&&<button type="button" onClick={onOpenMonthly}>Ver cierre mensual completo</button>}
      </div>
      {pdfError&&<div className="v2-error" role="alert">{pdfError}</div>}
    </section>
  </section>;
}
