import {useEffect,useState} from 'react'
import {getCapacity,getMonthSummary} from '../api'

const PRESETS=[
 {label:'Semana 1',from:'2026-09-01',to:'2026-09-07'},
 {label:'Semana 2',from:'2026-09-08',to:'2026-09-14'},
 {label:'Semana 3',from:'2026-09-15',to:'2026-09-21'},
 {label:'Semana 4',from:'2026-09-22',to:'2026-09-28'},
 {label:'Cierre mes',from:'2026-09-29',to:'2026-09-30'}
]

const SPECS=[
 {code:'MEC',name:'Mecánica'},
 {code:'ELE',name:'Eléctrica'},
 {code:'SER',name:'Servicios'},
 {code:'MET',name:'Metrología'}
]

export default function ImportPanel({onCapacity,initialWeek}){
 const [from,setFrom]=useState(initialWeek?.from||'2026-09-01')
 const [to,setTo]=useState(initialWeek?.to||'2026-09-07')
 const [summary,setSummary]=useState(null)
 const [busy,setBusy]=useState(false)
 const [error,setError]=useState('')

 async function selectWeek(p){
  try{
   setBusy(true);setError('')
   setFrom(p.from);setTo(p.to)
   const r=await getCapacity(p.from,p.to)
   onCapacity(r,{from:p.from,to:p.to})
  }catch(e){setError(e.message)}finally{setBusy(false)}
 }

 useEffect(()=>{
  const initial=PRESETS.find(p=>p.from===(initialWeek?.from||from)&&p.to===(initialWeek?.to||to))||PRESETS[0]
  selectWeek(initial)
  getMonthSummary(2026,9).then(setSummary).catch(e=>setError(e.message))
 },[])

 return <section className="panel week-panel compact-start">
  <div className="section-head">
   <div>
    <span className="section-kicker">PASO 1</span>
    <h2>Selecciona la semana</h2>
    <p>Elige la semana y revisa rápidamente la carga mensual antes de programar.</p>
   </div>
   <span className="month-chip">SEPTIEMBRE 2026</span>
  </div>

  <div className="week-presets clean-weeks">
   {PRESETS.map(p=><button
    key={p.label}
    className={from===p.from&&to===p.to?'active':''}
    onClick={()=>selectWeek(p)}
    disabled={busy}
   >
    <b>{p.label}</b>
    <small>{p.from.slice(8)}–{p.to.slice(8)} sep</small>
   </button>)}
  </div>

  <div className="month-overview">
   {SPECS.map(s=>{
    const x=summary?.specialties?.[s.code]||{}
    return <article key={s.code} className="overview-card">
     <div className="overview-title"><span>{s.code}</span><b>{s.name}</b></div>
     <div className="overview-main">{Number(x.total_orders||0)}<small>OT totales</small></div>
     <div className="overview-stats">
      <div><span>H-H</span><b>{Number(x.hh_total||0).toFixed(1)}</b></div>
      <div><span>Pend.</span><b>{Number(x.pending||0)}</b></div>
      <div><span>Final.</span><b>{Number(x.finalized||0)}</b></div>
     </div>
    </article>
   })}
  </div>

  {summary?.totals&&<div className="overview-foot">
   <b>{Number(summary.totals.total_orders||0)} OT cargadas</b>
   <span>{Number(summary.totals.hh_total||0).toFixed(1)} H-H calculadas con personal ya definido</span>
  </div>}
  {error&&<div className="inline-error">{error}</div>}
 </section>
}
