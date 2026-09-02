import {useEffect,useMemo,useState} from 'react'
import {downloadProgrammingExport,getProgrammingHistory,getProgrammingVersion} from '../api'

const SPECS=['MEC','ELE','SER','MET']
const NAMES={MEC:'Mecánica',ELE:'Eléctrica',SER:'Servicios',MET:'Metrología'}

function fmtDate(v){
 if(!v)return '—'
 const [y,m,d]=String(v).slice(0,10).split('-')
 return `${d}/${m}/${y}`
}
function hh(v){return Number(v||0).toFixed(1)}

export default function SavedProgramming(){
 const [history,setHistory]=useState([])
 const [specialty,setSpecialty]=useState('MEC')
 const [selectedVersion,setSelectedVersion]=useState('')
 const [detail,setDetail]=useState([])
 const [loading,setLoading]=useState(true)
 const [message,setMessage]=useState('')
 const [exporting,setExporting]=useState('')

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
     <button className="export-excel" disabled={!selectedVersion||!!exporting} onClick={()=>exportFile('xlsx')}>
      {exporting==='xlsx'?'Generando...':'Exportar Excel'}
     </button>
     <button className="export-pdf" disabled={!selectedVersion||!!exporting} onClick={()=>exportFile('pdf')}>
      {exporting==='pdf'?'Generando...':'Exportar PDF'}
     </button>
    </div>
   </section>

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
