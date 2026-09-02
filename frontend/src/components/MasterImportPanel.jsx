import {useEffect,useState} from 'react'
import {getMasterStatus,uploadFile} from '../api'

export default function MasterImportPanel(){
 const [file,setFile]=useState(null),[status,setStatus]=useState(null),[busy,setBusy]=useState(false),[message,setMessage]=useState('')
 async function refresh(){try{setStatus(await getMasterStatus())}catch{}}
 useEffect(()=>{refresh()},[])
 async function sync(){
  if(!file)return setMessage('Selecciona la copia .xlsx de TEAM FOOD')
  try{
   setBusy(true);setMessage('Sincronizando fuente maestra...')
   const r=await uploadFile('/api/imports/team-food',file)
   setMessage('Mes cargado: '+r.month+'/'+r.year+' · '+r.pmp+' PMP · '+r.orders+' órdenes · '+r.incomplete_people+' planes sin personas · '+r.incomplete_condition+' sin condición')
   await refresh()
  }catch(e){setMessage('Error: '+e.message)}finally{setBusy(false)}
 }
 const c=status?.counts||{}
 const period=status?.latest_period?(status.latest_period.mes+'/'+status.latest_period.anio):'sin cargar'
 return <section className="panel master-source">
   <div className="source-head"><div><h2>Fuente maestra · TEAM FOOD</h2><p>Activos, planeación, planes de trabajo, órdenes, turnos y programación de técnicos se consolidan desde un solo libro.</p></div><span className="source-badge">MAESTRO ÚNICO</span></div>
   <div className="metrics source-metrics">
    <div><span>Activos</span><b>{c.activos??0}</b></div>
    <div><span>Planes</span><b>{c.planes??0}</b></div>
    <div><span>Sin personas</span><b>{c.planes_sin_personas??0}</b></div>
    <div><span>Sin condición</span><b>{c.planes_sin_condicion??0}</b></div>
   </div>
   <div className="master-upload">
    <input type="file" accept=".xlsx" onChange={e=>setFile(e.target.files?.[0]||null)}/>
    <button className="primary" onClick={sync} disabled={busy}>{busy?'Sincronizando...':'Sincronizar TEAM FOOD'}</button>
    <small>{message||('Último periodo en base: '+period)}</small>
   </div>
 </section>
}
