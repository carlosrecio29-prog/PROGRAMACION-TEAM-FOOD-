import {useEffect,useMemo,useState} from 'react'
import {analyzeProgrammingCloseLive,downloadProgrammingExport,getProgrammingHistory,getProgrammingVersion} from '../api'

const SPECS=['MEC','ELE','SER','MET']
const NAMES={MEC:'Mecánica',ELE:'Eléctrica',SER:'Servicios',MET:'Metrología'}

function fmtDate(v){
 if(!v)return '—'
 const [y,m,d]=String(v).slice(0,10).split('-')
 return `${d}/${m}/${y}`
}
function hh(v){return Number(v||0).toFixed(1)}
function fmtDateTime(v){
 if(!v)return '—'
 const d=new Date(v)
 return Number.isNaN(d.getTime())?'—':d.toLocaleString('es-CO',{dateStyle:'short',timeStyle:'short'})
}

export default function SavedProgramming(){
 const [history,setHistory]=useState([])
 const [specialty,setSpecialty]=useState('MEC')
 const [selectedVersion,setSelectedVersion]=useState('')
 const [detail,setDetail]=useState([])
 const [loading,setLoading]=useState(true)
 const [message,setMessage]=useState('')
 const [exporting,setExporting]=useState('')
 const [analyzing,setAnalyzing]=useState(false)
 const [closeAnalysis,setCloseAnalysis]=useState(null)

 async function loadHistory(){
  try{
   setLoading(true)
   const rows=await getProgrammingHistory(200)
   setHistory(rows.filter(x=>x.es_actual))
  }catch(e){setMessage(e.message)}
  finally{setLoading(false)}
 }

 useEffect(()=>{loadHistory()},[])

 const specHistory=useMemo(
  ()=>history.filter(x=>x.especialidad===specialty),
  [history,specialty]
 )

 useEffect(()=>{
  const first=specHistory[0]
  setSelectedVersion(first?String(first.version_id):'')
 },[specialty,history])

 const current=useMemo(
  ()=>history.find(x=>String(x.version_id)===String(selectedVersion)),
  [history,selectedVersion]
 )

 useEffect(()=>{
  setCloseAnalysis(null)
  if(!selectedVersion){setDetail([]);return}
  let active=true
  getProgrammingVersion(selectedVersion)
   .then(r=>{if(active)setDetail(r)})
   .catch(e=>{if(active)setMessage(e.message)})
  return()=>{active=false}
 },[selectedVersion])

 async function exportFile(format){
  if(!selectedVersion)return
  try{
   setExporting(format)
   await downloadProgrammingExport(selectedVersion,format)
  }catch(e){setMessage(e.message)}
  finally{setExporting('')}
 }

 async function analyzeClose(){
  if(!selectedVersion)return
  try{
   setAnalyzing(true)
   setMessage('')
   const result=await analyzeProgrammingCloseLive(selectedVersion)
   setCloseAnalysis(result)
  }catch(e){
   setCloseAnalysis(null)
   setMessage(e.message)
  }finally{
   setAnalyzing(false)
  }
 }

 return <section className="saved-page">
  <div className="page-intro">
   <div>
    <span className="section-kicker">HISTORIAL OPERATIVO</span>
    <h2>Programaciones guardadas</h2>
    <p>Consulta lo que ya asignaste por semana y especialidad. Guardar una semana ya no significa perderla de vista.</p>
   </div>
   <button className="ghost" onClick={loadHistory}>Actualizar</button>
  </div>

  <div className="specialty-tabs saved-specialty-tabs">
   {SPECS.map(s=>{
    const count=history.filter(x=>x.especialidad===s).length
    return <button key={s} className={specialty===s?'active':''} onClick={()=>setSpecialty(s)}>
     <span className="spec-icon">{s.slice(0,2)}</span>
     <span className="spec-copy"><b>{NAMES[s]}</b><small>{count} semana{count===1?'':'s'} guardada{count===1?'':'s'}</small></span>
    </button>
   })}
  </div>

  {!specHistory.length&&!loading&&<div className="panel empty-saved">
   <h3>No hay programaciones guardadas en {NAMES[specialty]}</h3>
   <p>Cuando guardes una semana desde Programación semanal aparecerá aquí automáticamente.</p>
  </div>}

  {!!specHistory.length&&<>
   <section className="panel saved-selector-panel">
    <div className="saved-selector-head">
     <div><span className="section-kicker">SEMANA</span><h3>Selecciona la programación</h3></div>
     <select value={selectedVersion} onChange={e=>setSelectedVersion(e.target.value)}>
      {specHistory.map(x=><option key={x.version_id} value={x.version_id}>
       {fmtDate(x.fecha_desde)} al {fmtDate(x.fecha_hasta)} · v{x.numero_version} · {hh(x.hh_programadas)} H-H
      </option>)}
     </select>
    </div>

    {current&&<div className="saved-metrics">
     <div><span>Estado</span><b>{current.estado}</b><small>Versión {current.numero_version}</small></div>
     <div><span>H-H disponibles</span><b>{hh(current.hh_disponibles)}</b><small>Capacidad real</small></div>
     <div><span>Meta 80%</span><b>{hh(current.hh_objetivo)}</b><small>Objetivo semanal</small></div>
     <div><span>H-H programadas</span><b>{hh(current.hh_programadas)}</b><small>{current.items} actividades</small></div>
     <div><span>Reserva</span><b>{hh(current.hh_standby)}</b><small>20% standby</small></div>
    </div>}

    <div className="saved-actions">
     <button className="analyze-close-btn" disabled={!selectedVersion||analyzing} onClick={analyzeClose}>
      {analyzing?'Analizando TEAM FOOD...':'Analizar cierre'}
     </button>
     <button className="export-excel" disabled={!selectedVersion||!!exporting} onClick={()=>exportFile('xlsx')}>
      {exporting==='xlsx'?'Generando...':'Exportar Excel'}
     </button>
     <button className="export-pdf" disabled={!selectedVersion||!!exporting} onClick={()=>exportFile('pdf')}>
      {exporting==='pdf'?'Generando...':'Exportar PDF'}
     </button>
    </div>
   </section>

   {closeAnalysis&&<section className="panel close-analysis-panel">
    <div className="section-head">
     <div>
      <span className="section-kicker">ANÁLISIS DE CIERRE · SOLO LECTURA</span>
      <h2>Resultado contra TEAM FOOD actualizado</h2>
      <p>Se compararon únicamente las OT de esta programación contra los estados sincronizados desde TEAM FOOD. No necesitas subir ningún archivo.</p>
      <small className="sync-stamp">Última sincronización de estados: <b>{fmtDateTime(closeAnalysis.last_status_sync)}</b></small>
     </div>
     <span className="week-badge">{Number(closeAnalysis.compliance_pct||0).toFixed(1)}% cumplimiento</span>
    </div>

    <div className="close-analysis-metrics">
     <div><span>Programadas</span><b>{closeAnalysis.total_programmed}</b><small>OT de esta semana</small></div>
     <div className="metric-finalized"><span>Finalizadas</span><b>{closeAnalysis.finalized}</b><small>{hh(closeAnalysis.hh_finalized)} H-H</small></div>
     <div className="metric-pending"><span>Pendientes</span><b>{closeAnalysis.pending}</b><small>{hh(closeAnalysis.hh_pending)} H-H pendientes</small></div>
     <div className="metric-review"><span>Por revisar</span><b>{closeAnalysis.review}</b><small>No encontrada/estado distinto</small></div>
    </div>

    <div className="close-analysis-note">
     <b>Resultado preliminar.</b>
     <span>Cuando confirmemos el cierre definitivo, las FINALIZADAS quedarán como ejecutadas y las PENDIENTES requerirán motivo de no ejecución antes de pasar a backlog.</span>
    </div>

    <div className="table-wrap close-analysis-table">
     <table>
      <thead><tr><th>OT</th><th>Área</th><th>Equipo</th><th>Actividad</th><th>Plan</th><th>H-H</th><th>Estado TEAM FOOD</th><th>Resultado</th></tr></thead>
      <tbody>
       {closeAnalysis.items.map(x=><tr key={x.program_item_id}>
        <td><b>{x.numero_orden||'—'}</b></td>
        <td>{x.area_nombre||'—'}</td>
        <td><span className="asset-code">{x.activo_codigo}</span><small className="asset-name">{x.activo_descripcion}</small></td>
        <td>{x.actividad||'—'}</td>
        <td>{x.plan_trabajo||'—'}</td>
        <td><b>{hh(x.hh_programadas)}</b></td>
        <td><span className={'close-state state-'+String(x.estado_maestro||'').toLowerCase().replaceAll(' ','-')}>{x.estado_maestro}</span></td>
        <td><span className={'close-result result-'+String(x.resultado_cierre||'').toLowerCase()}>{x.resultado_cierre}</span></td>
       </tr>)}
      </tbody>
     </table>
    </div>
   </section>}

   <section className="panel saved-detail-panel">
    <div className="section-head">
     <div>
      <span className="section-kicker">DETALLE GUARDADO</span>
      <h2>{NAMES[specialty]} · {current?fmtDate(current.fecha_desde)+' al '+fmtDate(current.fecha_hasta):''}</h2>
      <p>Esta tabla representa la versión oficial que quedó guardada.</p>
     </div>
     <span className="week-badge">{detail.length} actividades</span>
    </div>
    <div className="table-wrap saved-detail-table">
     <table>
      <thead><tr><th>OT</th><th>Área</th><th>Equipo</th><th>Actividad</th><th>Plan</th><th>Crit.</th><th>Condición</th><th>Personas</th><th>Tiempo min</th><th>H-H</th><th>Origen</th><th>Estado OT</th></tr></thead>
      <tbody>
       {!detail.length&&<tr><td colSpan="12" className="empty">No hay actividades en esta versión.</td></tr>}
       {detail.map(x=><tr key={x.program_item_id}>
        <td><b>{x.numero_orden||'—'}</b></td>
        <td>{x.area_nombre||'—'}</td>
        <td><span className="asset-code">{x.activo_codigo}</span><small className="asset-name">{x.activo_descripcion}</small></td>
        <td>{x.actividad||'—'}</td>
        <td>{x.plan_trabajo}</td>
        <td><span className={'criticality crit-'+(x.criticidad||'x')}>{x.criticidad||'—'}</span></td>
        <td>{x.condicion}</td>
        <td>{x.personas_usar??'—'}</td>
        <td>{x.tiempo_planeado_min??'—'}</td>
        <td><b>{hh(x.hh_programadas)}</b></td>
        <td>{x.origen}</td>
        <td>{x.estado}</td>
       </tr>)}
      </tbody>
     </table>
    </div>
   </section>
  </>}

  <div className="message">{message}</div>
 </section>
}
