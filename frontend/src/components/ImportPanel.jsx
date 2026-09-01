import {useEffect,useState} from 'react'
import {getCapacity} from '../api'

const PRESETS=[
 {label:'Semana 1',from:'2026-09-01',to:'2026-09-07'},
 {label:'Semana 2',from:'2026-09-08',to:'2026-09-14'},
 {label:'Semana 3',from:'2026-09-15',to:'2026-09-21'},
 {label:'Semana 4',from:'2026-09-22',to:'2026-09-28'},
 {label:'Cierre mes',from:'2026-09-29',to:'2026-09-30'}
]

export default function ImportPanel({onCapacity,initialWeek}){
 const [from,setFrom]=useState(initialWeek?.from||'2026-09-01')
 const [to,setTo]=useState(initialWeek?.to||'2026-09-07')
 const [status,setStatus]=useState(''),[busy,setBusy]=useState(false)

 async function calculate(nextFrom=from,nextTo=to){
  if(!nextFrom||!nextTo)return setStatus('Selecciona el rango semanal')
  try{
   setBusy(true);setStatus('Calculando capacidad...')
   const r=await getCapacity(nextFrom,nextTo)
   onCapacity(r,{from:nextFrom,to:nextTo})
   setStatus('Capacidad actualizada desde la programación de turnos')
  }catch(e){setStatus(e.message)}finally{setBusy(false)}
 }

 function usePreset(p){
  setFrom(p.from);setTo(p.to);calculate(p.from,p.to)
 }

 useEffect(()=>{calculate(initialWeek?.from||from,initialWeek?.to||to)},[])

 return <section className="panel week-panel">
  <div className="section-head">
   <div><span className="section-kicker">PASO 1</span><h2>Semana a programar</h2><p>El sistema suma las horas reales de los turnos y protege 20% como reserva operativa.</p></div>
   <span className="month-chip">SEPTIEMBRE 2026</span>
  </div>

  <div className="week-presets">
   {PRESETS.map(p=><button key={p.label} className={from===p.from&&to===p.to?'active':''} onClick={()=>usePreset(p)}>{p.label}<small>{p.from.slice(8)}–{p.to.slice(8)} sep</small></button>)}
  </div>

  <div className="week-row">
   <label>Desde<input type="date" value={from} onChange={e=>setFrom(e.target.value)}/></label>
   <label>Hasta<input type="date" value={to} onChange={e=>setTo(e.target.value)}/></label>
   <button className="primary" onClick={()=>calculate()} disabled={busy}>{busy?'Calculando...':'Actualizar H-H'}</button>
   <span className="inline-status">{status}</span>
  </div>
 </section>
}
