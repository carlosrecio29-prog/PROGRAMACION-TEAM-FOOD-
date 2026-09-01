import {useEffect,useState} from 'react'
import {getImportHistory,getMasterStatus,uploadFile} from '../api'

function fmtDateTime(v){
 if(!v)return '—'
 const d=new Date(v)
 return Number.isNaN(d.getTime())?'—':d.toLocaleString('es-CO',{dateStyle:'short',timeStyle:'short'})
}

export default function MasterImportPanel(){
 const [file,setFile]=useState(null)
 const [status,setStatus]=useState(null)
 const [history,setHistory]=useState([])
 const [busy,setBusy]=useState(false)
 const [message,setMessage]=useState('')

 async function refresh(){
  try{
   const [master,imports]=await Promise.all([getMasterStatus(),getImportHistory(20)])
   setStatus(master)
   setHistory(imports.filter(x=>x.tipo==='MAESTRO_TEAM_FOOD').slice(0,6))
  }catch{}
 }

 useEffect(()=>{refresh()},[])

 async function sync(){
  if(!file)return setMessage('Selecciona el archivo maestro .xlsx de TEAM FOOD')
  try{
   setBusy(true)
   setMessage('Procesando Excel y guardando los datos en Supabase...')
   const r=await uploadFile('/api/imports/team-food',file)
   setMessage(
    'Carga completada: '+r.month+'/'+r.year+
    ' · '+r.pmp+' PMP del periodo · '+r.orders+' órdenes del periodo'+
    ' · '+(r.order_status_updates||0)+' estados históricos actualizados'
   )
   setFile(null)
   const input=document.getElementById('team-food-master-file')
   if(input)input.value=''
   await refresh()
  }catch(e){
   setMessage('Error: '+e.message)
  }finally{
   setBusy(false)
  }
 }

 const c=status?.counts||{}
 const last=status?.last_sync
 const period=status?.latest_period?(String(status.latest_period.mes).padStart(2,'0')+'/'+status.latest_period.anio):'sin cargar'

 return <div className="master-page">
  <section className="panel master-source">
   <div className="source-head">
    <div>
     <span className="section-kicker">FUENTE DE DATOS</span>
     <h2>Excel maestro · TEAM FOOD</h2>
     <p>Sube la versión más reciente del libro maestro. El sistema extrae la información y la almacena de forma relacional en Supabase.</p>
    </div>
    <span className="source-badge">EXCEL → SUPABASE</span>
   </div>

   <div className="master-info-note">
    <b>No almacenamos el archivo completo.</b>
    <span>Se guardan y actualizan activos, planes, actividades, PMP, órdenes, estados de OT, técnicos y turnos. Cada carga queda registrada para auditoría.</span>
   </div>

   <div className="metrics source-metrics">
    <div><span>Activos</span><b>{c.activos??0}</b><small>Catálogo de planta</small></div>
    <div><span>Planes</span><b>{c.planes??0}</b><small>Planes de trabajo</small></div>
    <div><span>Actividades</span><b>{c.actividades??0}</b><small>Relaciones maestro</small></div>
    <div><span>Periodo activo</span><b>{period}</b><small>Último mes cargado</small></div>
   </div>

   <div className="master-upload-card">
    <div className="master-upload-copy">
     <span className="section-kicker">ACTUALIZAR BASE</span>
     <h3>Subir nuevo Excel maestro</h3>
     <p>Puedes subir el mismo maestro todas las veces que sea necesario. Los registros existentes se actualizan y los nuevos se insertan.</p>
     {last&&<small>Última carga completada: <b>{fmtDateTime(last.finalizado_en)}</b> · {last.filas_procesadas||0} registros procesados</small>}
    </div>
    <div className="master-upload">
     <input id="team-food-master-file" type="file" accept=".xlsx" onChange={e=>setFile(e.target.files?.[0]||null)}/>
     {file&&<span className="selected-master-file">{file.name}</span>}
     <button className="primary" onClick={sync} disabled={busy}>{busy?'Guardando en base...':'Procesar y guardar en base'}</button>
    </div>
   </div>

   {message&&<div className={'master-message '+(message.startsWith('Error')?'error':'')}>{message}</div>}
  </section>

  <section className="panel master-history-panel">
   <div className="section-head">
    <div>
     <span className="section-kicker">AUDITORÍA</span>
     <h2>Historial de cargas del maestro</h2>
     <p>Cada importación queda registrada aunque los datos se actualicen sobre las mismas tablas.</p>
    </div>
    <button className="ghost" onClick={refresh}>Actualizar</button>
   </div>
   <div className="table-wrap master-history-table">
    <table>
     <thead><tr><th>Fecha</th><th>Archivo</th><th>Estado</th><th>Leídas</th><th>Procesadas</th><th>Rechazadas</th></tr></thead>
     <tbody>
      {!history.length&&<tr><td colSpan="6" className="empty">Todavía no hay cargas registradas.</td></tr>}
      {history.map(x=><tr key={x.id}>
       <td>{fmtDateTime(x.fecha_importacion)}</td>
       <td><b>{x.nombre_archivo}</b></td>
       <td><span className={'import-state '+String(x.estado||'').toLowerCase()}>{x.estado}</span></td>
       <td>{x.filas_leidas??0}</td>
       <td>{x.filas_insertadas??0}</td>
       <td>{x.filas_rechazadas??0}</td>
      </tr>)}
     </tbody>
    </table>
   </div>
  </section>
 </div>
}