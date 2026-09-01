import {useState} from 'react'
import {uploadFile,getCapacity} from '../api'

function ImportBox({title,endpoint,onDone,params}){
 const [file,setFile]=useState(null),[status,setStatus]=useState('Sin cargar'),[busy,setBusy]=useState(false)
 async function run(){if(!file)return setStatus('Selecciona un archivo');try{setBusy(true);setStatus('Procesando...');const r=await uploadFile(endpoint,file,params);setStatus(`OK · ${r.rows_read??0} leídas · ${r.inserted??0} nuevas · ${r.updated??0} actualizadas · ${r.rejected??0} rechazadas`);onDone?.(r)}catch(e){setStatus(`Error: ${e.message}`)}finally{setBusy(false)}}
 return <div className="upload-card"><strong>{title}</strong><input type="file" accept=".xlsx" onChange={e=>setFile(e.target.files?.[0]||null)}/><button onClick={run} disabled={busy}>{busy?'Actualizando...':'Actualizar'}</button><small>{status}</small></div>
}
export default function ImportPanel({onCapacity}){
 const [from,setFrom]=useState(''),[to,setTo]=useState(''),[status,setStatus]=useState('')
 async function calculate(){if(!from||!to)return setStatus('Selecciona el rango');try{const r=await getCapacity(from,to);onCapacity(r,{from,to});setStatus('Disponibilidad actualizada')}catch(e){setStatus(e.message)}}
 return <section className="panel"><h2>Archivos y semana</h2><div className="uploads">
  <ImportBox title="Planeación mensual PMP" endpoint="/api/imports/planning"/>
  <ImportBox title="Programación de técnicos" endpoint="/api/imports/technician-roster"/>
  <ImportBox title="Estado actualizado de órdenes" endpoint="/api/imports/order-status"/>
 </div><div className="week-row"><label>Desde<input type="date" value={from} onChange={e=>setFrom(e.target.value)}/></label><label>Hasta<input type="date" value={to} onChange={e=>setTo(e.target.value)}/></label><button className="primary" onClick={calculate}>Calcular disponibilidad</button><span>{status}</span></div></section>
}
