import {useEffect,useMemo,useState} from "react";
import {downloadV2ProgressPdf,getV2Progress} from "../api";
import "./progressDashboard.css";

const NAMES = {MEC:"Mecánica",ELE:"Eléctrica",MET:"Metrología",SER:"Servicios"};
const number = x => Number(x || 0);
const count = x => number(x).toLocaleString("es-CO",{maximumFractionDigits:0});
const hh = x => number(x).toLocaleString("es-CO",{minimumFractionDigits:1,maximumFractionDigits:2});
const pct = x => x === null || x === undefined ? "Por verificar" : number(x).toLocaleString("es-CO",{maximumFractionDigits:1}) + "%";
const dateLabel = s => s ? s.split("-").reverse().join("/") : "—";

function Card({label,value,extra,tone=""}){
  return <div className={"v2-progress-metric " + tone}>
    <span>{label}</span><strong>{value}</strong><small>{extra}</small>
  </div>;
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
    <div className="v2-panel">
      <div className="v2-section-head">
        <div><span className="v2-kicker">SEGUIMIENTO DEL PERIODO</span>
          <h3>{full?"Informe general de cierre mensual":"Avance de programación y cierres"}</h3>
          <p>Basado en las programaciones y cierres guardados, no en los Excel cargados por separado.</p>
        </div>
        <button type="button" onClick={()=>setRevision(x=>x+1)} disabled={loading}>
          {loading?"Actualizando...":"Actualizar avance"}
        </button>
      </div>
      {top.contains_future_week_closures&&<div className="v2-warning" role="note">
        CIERRE DE PRUEBA / ANTICIPADO: existen semanas cerradas con fecha de fin posterior a hoy.
        No presentar este informe como cierre operativo definitivo del mes.
      </div>}
      <div className="v2-progress-month-state">
        <strong>{count(top.weeks_closed)} de {count(top.weeks_total)} programaciones cerradas</strong>
        <span>{top.all_weeks_closed?"Periodo completamente cerrado para las especialidades programadas":"Informe parcial: quedan programaciones sin cierre"}</span>
      </div>
      <div className="v2-progress-metrics">
        <Card label="OT únicas programadas" value={count(top.programmed)} extra="Sin duplicar OT reprogramadas"/>
        <Card label="OT finalizadas al último cierre" value={count(top.finalized)} extra={pct(top.progress_ot_pct)+" de OT únicas"} tone="success"/>
        <Card label="OT pendientes" value={count(top.pending)} extra="Último cierre del periodo" tone="warning"/>
        <Card label="No encontradas" value={count(top.not_found)} extra="Requieren conciliación" tone="warning"/>
        <Card label="Registros PMP" value={count(top.pmp_count)} extra="Mantenimiento del mes, sin OPERACIÓN"/>
        <Card label="HH estimadas finalizadas" value={hh(totals.hh_finalized)} extra={"De "+hh(totals.hh_programmed)+" HH programadas en semanas"} tone="success"/>
      </div>
      <div className="v2-progress-note">
        <b>Dos formas de medir:</b> el consolidado superior cuenta cada OT una vez según su último
        cierre del periodo; el análisis semanal de abajo cuenta cada vez que fue programada.
        Las HH son estimadas, no horas reales ejecutadas.
      </div>
    </div>
    <section className="v2-panel">
      <div className="v2-section-head">
        <div><span className="v2-kicker">TENDENCIA SEMANAL</span><h3>Avance por especialidad</h3>
          <p>Cierres de jueves a miércoles · OT programadas frente a finalizadas y H-H estimadas.</p></div>
        <label className="v2-progress-filter">Especialidad
          <select value={specialty} onChange={e=>setSpecialty(e.target.value)}>
            <option value="">Todas</option>
            {Object.entries(NAMES).map(([code,name])=><option key={code} value={code}>{name}</option>)}
          </select>
        </label>
      </div>
      {weeks.length===0?<p>Aún no hay programaciones de este periodo para el filtro elegido.</p>:<>
        <div className="v2-progress-chart" aria-label="Avance semanal por OT programadas y finalizadas">
          {weeks.map(week=><div className="v2-progress-chart-row" key={week.programming_id}>
            <div className="v2-progress-chart-label">
              <b>{NAMES[week.especialidad]||week.especialidad}</b>
              <span>{dateLabel(week.week_from)} – {dateLabel(week.week_to)}</span>
            </div>
            <div className="v2-progress-chart-bars">
              <div className="v2-progress-chart-track"><div className="v2-progress-chart-total" style={{width:"100%"}}/></div>
              <div className="v2-progress-chart-track"><div className="v2-progress-chart-done"
                style={{width:Math.min(100,number(week.progress_ot_pct||0))+"%"}}/></div>
            </div>
            <strong>{week.estado==="CERRADA"?pct(week.progress_ot_pct):"Sin cierre"}</strong>
          </div>)}
        </div>
        <div className="v2-progress-chart-legend">Barra clara: OT programadas (100% de la semana). Barra azul: OT finalizadas de esa semana.</div>
        <div className="v2-table-wrap"><table>
          <thead><tr><th>Corte</th><th>Especialidad</th><th>Estado</th><th>Programadas</th><th>Finalizadas</th>
            <th>Pendientes</th><th>No encontradas</th><th>Backlog programado</th><th>HH prog.</th><th>HH fin. est.</th><th>OT %</th><th>HH %</th><th>Reporte</th></tr></thead>
          <tbody>{weeks.map(w=><tr key={w.programming_id}>
            <td>{dateLabel(w.week_from)} – {dateLabel(w.week_to)}</td><td>{NAMES[w.especialidad]||w.especialidad}</td>
            <td>{w.estado}</td><td>{count(w.programmed)}</td><td>{w.estado==="CERRADA"?count(w.finalized):"—"}</td>
            <td>{w.estado==="CERRADA"?count(w.pending):"—"}</td><td>{w.estado==="CERRADA"?count(w.not_found):"—"}</td>
            <td>{count(w.origin_backlog)}</td><td>{hh(w.hh_programmed)}</td>
            <td>{w.estado==="CERRADA"?hh(w.hh_finalized):"—"}</td>
            <td>{pct(w.progress_ot_pct)}</td><td>{pct(w.progress_hh_pct)}</td>
            <td><button type="button" disabled={!!downloading}
              onClick={()=>showReport(w.programming_id)}>
              {downloading===String(w.programming_id)?"Generando...":"PDF semanal"}
            </button></td>
          </tr>)}</tbody>
        </table></div>
      </>}
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
        <Card label="OT abiertas en último cierre" value={count(top.pending)} extra="No equivale a toda la cartera sin ejecutar"} tone="warning"/>
        <Card label="OT sin encontrar / verificar" value={count(top.not_found+top.unchecked)} extra="Conciliación y semanas abiertas"} tone="warning"/>
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
        {!full&&onOpenMonthly&&<button type="button" onClick={onOpenMonthly}>Ver cierre mensual completo</button>}
      </div>
      {pdfError&&<div className="v2-error" role="alert">{pdfError}</div>}
    </section>
  </section>;
}
