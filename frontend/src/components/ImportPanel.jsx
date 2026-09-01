import {useState} from 'react'
import {getCapacity} from '../api'

export default function ImportPanel({onCapacity}){
 const [from,setFrom]=useState(''),[to,setTo]=useState(''),[status,setStatus]=useState('')
 async function calculate(){
  if(!from||!to)return setStatus('Selecciona el rango semanal')
  try{const r=await getCapacity(from,to);onCapacity(r,{from,to});setStatus('Capacidad calculada con la programación de técnicos')}
  catch(e){setStatus(e.message)}
 }
 return <section className="panel">
  <h2>Semana a programar</h2>
  <p className="panel-copy">La meta operativa es el 80% de las H-H disponibles. El 20% restante queda protegido como standby.</p>
  <div className="week-row">
   <label>Desde<input type="date" value={from} onChange={e=>setFrom(e.target.value)}/></label>
   <label>Hasta<input type="date" value={to} onChange={e=>setTo(e.target.value)}/></label>
   <button className="primary" onClick={calculate}>Calcular H-H disponibles</button>
   <span>{status}</span>
  </div>
 </section>
}
