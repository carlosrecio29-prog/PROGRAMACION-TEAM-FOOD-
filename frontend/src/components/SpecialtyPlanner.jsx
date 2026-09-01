import {useEffect,useMemo,useState} from 'react'
import {getCandidates,getMonthReconciliation,learnPlan,saveProgramming} from '../api'

const CONDITIONS=['OPERANDO','EQUIPO DETENIDO','LINEA DETENIDA','AREA/PLANTA DETENIDA']

function hh(v){
 return v===null||v===undefined?'—':Number(v).toFixed(1)+' H-H'
}
function pct(v,max){
 if(!max)return 0
 return Math.min(100,Math.max(0,(v/max)*100))
}
function uniqueOptions(rows,key){
 const values=[...new Set(rows.map(x=>x[key]).filter(Boolean))]
 return values.sort((a,b)=>String(a).localeCompare(String(b),'es')).map(v=>({value:v,label:v}))
}
function exportCsv(rows,specialty){
 if(!rows.length)return
 const headers=['Orden','Área','Activo','Descripción','Plan','Actividad','Criticidad','Condición','Personas','Tiempo min','H-H','Origen']
 const data=rows.map(x=>[x.numero_orden||'',x.area_nombre||'',x.activo_codigo,x.activo_descripcion,x.plan_trabajo,x.actividad||'',x.criticidad||'',x.condicion,x.personas_usar,x.tiempo_planeado_min,x.hh_pmp,x.origen])
 const csv=[headers,...data].map(r=>r.map(v=>`"${String(v??'').replaceAll('"','""')}"`).join(',')).join('\n')
 const blob=new Blob(['\ufeff'+csv],{type:'text/csv;charset=utf-8'})
 const url=URL.createObjectURL(blob),a=document.createElement('a')
 a.href=url;a.download=`programacion_${specialty}.csv`;a.click();URL.revokeObjectURL(url)
}

function SearchableSelect({label,value,options,onChange,placeholder,disabled=false,emptyText='Sin resultados'}){
 const [open,setOpen]=useState(false)
 const [query,setQuery]=useState('')
 const [typed,setTyped]=useState(false)

 const selectedLabel=useMemo(
  ()=>options.find(o=>String(o.value)===String(value))?.label||'',
  [options,value]
 )

 useEffect(()=>{
  if(value&&selectedLabel){setQuery(selectedLabel);setTyped(false)}
  else if(!typed){setQuery('')}
 },[value,selectedLabel])

 const visible=useMemo(()=>{
  if(!typed)return options.slice(0,120)
  const q=query.trim().toLowerCase()
  if(!q)return options.slice(0,120)
  return options.filter(o=>(o.search||o.label).toLowerCase().includes(q)).slice(0,120)
 },[options,query,typed])

 function handleFocus(){
  if(disabled)return
  setOpen(true)
  setTyped(false)
 }
 function handleChange(e){
  const next=e.target.value
  setQuery(next)
  setTyped(true)
  setOpen(true)
  if(value)onChange('')
 }
 function choose(option){
  onChange(option.value)
  setQuery(option.label)
  setTyped(false)
  setOpen(false)
 }
 function blur(){
  window.setTimeout(()=>setOpen(false),120)
 }

 return <div className={'search-select '+(disabled?'disabled':'')}>
  <label><span>{label}</span>
   <div className="search-select-box">
    <input
     value={query}
     disabled={disabled}
     placeholder={placeholder}
     onFocus={handleFocus}
     onChange={handleChange}
     onBlur={blur}
     autoComplete="off"
    />
    <button type="button" tabIndex="-1" disabled={disabled} onMouseDown={e=>e.preventDefault()} onClick={()=>{setOpen(v=>!v);setTyped(false)}}>⌄</button>
   </div>
  </label>
  {open&&!disabled&&<div className="search-options">
   {visible.map(o=><button type="button" key={String(o.value)} onMouseDown={e=>e.preventDefault()} onClick={()=>choose(o)}>{o.label}</button>)}
   {!visible.length&&<div className="no-result">{emptyText}</div>}
   {options.length>120&&!typed&&<div className="more-results">Escribe para filtrar entre {options.length} opciones.</div>}
  </div>}
 </div>
}

export default function SpecialtyPlanner({specialty,specialtyName,capacity,week,year,month}){
 const [candidates,setCandidates]=useState([])
 const [selected,setSelected]=useState([])
 const [area,setArea]=useState(''),[criticality,setCriticality]=useState(''),[condition,setCondition]=useState('')
 const [origin,setOrigin]=useState('MES')
 const [chosenPlan,setChosenPlan]=useState(''),[chosenActivity,setChosenActivity]=useState(''),[currentId,setCurrentId]=useState('')
 const [message,setMessage]=useState(''),[refresh,setRefresh]=useState(0),[loading,setLoading]=useState(false)
 const [reconciliation,setReconciliation]=useState({})
 const [learnCondition,setLearnCondition]=useState(''),[learnPeople,setLearnPeople]=useState(''),[learning,setLearning]=useState(false)

 useEffect(()=>{
  setSelected([]);resetFlow();setMessage('')
 },[specialty])

 useEffect(()=>{
  let active=true
  const timer=setTimeout(async()=>{
   try{
    setLoading(true)
    const rows=await getCandidates({
      specialty,year,month,area:area||undefined,criticality:criticality||undefined,
      condition:condition||undefined,origin,limit:2000
    })
    if(active)setCandidates(rows)
   }catch(e){if(active)setMessage(e.message)}
   finally{if(active)setLoading(false)}
  },120)
  return()=>{active=false;clearTimeout(timer)}
 },[specialty,year,month,area,criticality,condition,origin,refresh])

 useEffect(()=>{
  let active=true
  getMonthReconciliation(year,month)
   .then(r=>{if(active)setReconciliation(r||{})})
   .catch(()=>{if(active)setReconciliation({})})
  return()=>{active=false}
 },[year,month,refresh,selected.length])

 const available=useMemo(()=>candidates.filter(x=>!selected.some(s=>s.pmp_id===x.pmp_id)),[candidates,selected])
 const areaOptions=useMemo(()=>[...new Set(candidates.map(x=>x.area_nombre).filter(Boolean))].sort(),[candidates])

 const planOptions=useMemo(()=>uniqueOptions(available,'plan_trabajo'),[available])
 const planRows=useMemo(()=>chosenPlan?available.filter(x=>x.plan_trabajo===chosenPlan):[],[available,chosenPlan])
 const activityOptions=useMemo(()=>uniqueOptions(planRows,'actividad'),[planRows])
 const activityRows=useMemo(()=>chosenActivity?planRows.filter(x=>x.actividad===chosenActivity):[],[planRows,chosenActivity])
 const equipmentOptions=useMemo(()=>activityRows.map(x=>({
   value:String(x.pmp_id),
   label:`${x.activo_codigo} — ${x.activo_descripcion} — ${x.numero_orden||'SIN OT'}`,
   search:`${x.activo_codigo} ${x.activo_descripcion} ${x.numero_orden||''} ${x.area_nombre||''}`
 })),[activityRows])
 const current=useMemo(()=>candidates.find(x=>String(x.pmp_id)===String(currentId)),[candidates,currentId])

 const stats=reconciliation[specialty]||{}
 const target=Number(capacity?.target||0)
 const total=Number(capacity?.available||0)
 const standby=Number(capacity?.standby||0)
 const used=selected.reduce((sum,x)=>sum+Number(x.hh_pmp||0),0)
 const remaining=Math.max(0,target-used)
 const ready=available.filter(x=>x.datos_completos).length
 const incomplete=available.length-ready

 function resetFlow(){
  setChosenPlan('');setChosenActivity('');setCurrentId('')
 }
 function selectPlan(value){
  setChosenPlan(value);setChosenActivity('');setCurrentId('');setMessage('')
 }
 function selectActivity(value){
  setChosenActivity(value);setCurrentId('');setMessage('')
 }
 function chooseCurrent(value){
  setCurrentId(value)
  const item=candidates.find(x=>String(x.pmp_id)===String(value))
  if(item){
   setLearnCondition(item.condicion==='SIN CLASIFICAR'?'':item.condicion)
   setLearnPeople(item.personas_usar??'')
  }
  setMessage('')
 }
 async function completePlan(){
  if(!current)return
  if((current.datos_faltantes||[]).includes('CONDICION')&&!learnCondition)return setMessage('Define la condición del equipo antes de continuar.')
  if((current.datos_faltantes||[]).includes('PERSONAS')&&!learnPeople)return setMessage('Indica cuántas personas requiere este plan.')
  try{
   setLearning(true)
   await learnPlan(current.plan_trabajo_id,{
    condition:learnCondition||current.condicion,
    people:learnPeople?Number(learnPeople):null
   })
   setMessage('Dato aprendido. Se reutilizará cuando este plan vuelva a aparecer.')
   setRefresh(x=>x+1)
  }catch(e){setMessage(e.message)}finally{setLearning(false)}
 }
 function addItem(item=current){
  if(!item)return setMessage('Selecciona un equipo.')
  if(!item.datos_completos)return setMessage('Completa los datos faltantes antes de agregar la actividad.')
  const next=used+Number(item.hh_pmp||0)
  if(target<=0)return setMessage('Primero selecciona una semana con capacidad disponible.')
  if(next>target+.0001)return setMessage(`No se puede agregar: quedarías en ${next.toFixed(1)} H-H y la meta es ${target.toFixed(1)} H-H.`)
  setSelected(prev=>[...prev,item])
  setCurrentId('')
  setMessage(`${item.numero_orden||'Actividad'} agregada a la programación.`)
 }
 async function save(){
  if(!week?.from||!week?.to)return setMessage('Selecciona la semana.')
  if(!selected.length)return setMessage('Agrega al menos una actividad.')
  try{
   const r=await saveProgramming({
    date_from:week.from,date_to:week.to,specialty,pmp_ids:selected.map(x=>x.pmp_id)
   })
   setMessage(`Programación guardada · ${Number(r.hh_programmed).toFixed(1)} H-H · versión ${r.version}`)
   setSelected([]);resetFlow();setRefresh(x=>x+1)
  }catch(e){setMessage(e.message)}
 }

 return <div className="planner">
  <div className="capacity-strip">
   <div><span>Técnicos</span><b>{Number(capacity?.technicians||0)}</b><small>en {specialtyName}</small></div>
   <div><span>Capacidad real</span><b>{total.toFixed(1)}</b><small>H-H disponibles</small></div>
   <div className="target-card"><span>Meta programable</span><b>{target.toFixed(1)}</b><small>80% de capacidad</small></div>
   <div><span>Programadas</span><b>{used.toFixed(1)}</b><small>{remaining.toFixed(1)} H-H por usar</small></div>
   <div><span>Reserva</span><b>{standby.toFixed(1)}</b><small>20% standby</small></div>
  </div>

  <div className="capacity-progress">
   <div className="progress-copy"><span>Uso de la meta semanal</span><b>{pct(used,target).toFixed(0)}%</b></div>
   <div className="progress-track"><i style={{width:pct(used,target)+'%'}}/></div>
  </div>

  <div className="reconciliation-card">
   <div className="reconciliation-head">
    <div><span className="section-kicker">CONCILIACIÓN CON MAESTRO</span><h3>De Excel a programación</h3><p>Las OT repetidas se consolidan; las OT distintas se conservan como PMP independientes.</p></div>
    <span className="reconciliation-period">09 / 2026</span>
   </div>
   <div className="reconciliation-grid">
    <div><span>PMP en maestro</span><b>{Number(stats.master_rows||0)}</b><small>Filas de {specialtyName}</small></div>
    <div><span>OT únicas</span><b>{Number(stats.unique_ot||0)}</b><small>{Number(stats.repeated_extra_rows||0)} repetidas consolidadas</small></div>
    <div><span>Pendientes</span><b>{Number(stats.pending_unique_ot||0)}</b><small>OT pendientes únicas</small></div>
    <div><span>Finalizadas</span><b>{Number(stats.finalized_unique_ot||0)}</b><small>No entran a programación</small></div>
    <div className="reconciliation-warn"><span>Inconsistencias</span><b>{Number(stats.pending_exceptions||0)}</b><small>Requieren corregir relación</small></div>
    <div className="reconciliation-ok"><span>Disponibles ahora</span><b>{Number(stats.available_now??available.length)}</b><small>Para seguir programando</small></div>
   </div>
   <div className="reconciliation-equation">
    <span>{Number(stats.master_rows||0)} maestro</span><i>→</i>
    <span>{Number(stats.unique_ot||0)} OT únicas</span><i>→</i>
    <span>{Number(stats.pending_unique_ot||0)} pendientes</span><i>→</i>
    <span>{Number(stats.pending_exceptions||0)} inconsistencias</span><i>→</i>
    <strong>{Number(stats.available_now??available.length)} disponibles</strong>
   </div>
  </div>

  <div className="candidate-summary">
   <div><b>{available.length}</b><span>PMP pendientes disponibles</span></div>
   <div className="ok"><b>{ready}</b><span>Listos para programar</span></div>
   <div className="warn"><b>{incomplete}</b><span>Necesitan completar datos</span></div>
  </div>

  <div className="subsection-title">
   <div><span className="step-number">3</span><div><h3>Filtra los PMP del mes</h3><p>Los filtros definen qué planes, actividades y equipos estarán disponibles abajo.</p></div></div>
   <button className="ghost" onClick={()=>{setArea('');setCriticality('');setCondition('');setOrigin('MES');resetFlow()}}>Limpiar filtros</button>
  </div>

  <div className="filters">
   <label>Área<select value={area} onChange={e=>{setArea(e.target.value);resetFlow()}}><option value="">Todas las áreas</option>{areaOptions.map(x=><option key={x}>{x}</option>)}</select></label>
   <label>Criticidad<select value={criticality} onChange={e=>{setCriticality(e.target.value);resetFlow()}}><option value="">A, B y C</option><option>A</option><option>B</option><option>C</option></select></label>
   <label>Condición<select value={condition} onChange={e=>{setCondition(e.target.value);resetFlow()}}><option value="">Todas</option><option>OPERANDO</option><option>EQUIPO DETENIDO</option><option>LINEA DETENIDA</option><option>AREA/PLANTA DETENIDA</option><option>SIN CLASIFICAR</option></select></label>
   <label>Origen<select value={origin} onChange={e=>{setOrigin(e.target.value);resetFlow()}}><option value="MES">PMP del mes</option><option value="BACKLOG">Backlog</option><option value="ALL">Mes + backlog</option></select></label>
  </div>

  <div className="subsection-title selection-title">
   <div><span className="step-number">4</span><div><h3>Selecciona Plan → Actividad → Equipo</h3><p>Haz clic para ver toda la lista o escribe para encontrar más rápido.</p></div></div>
   {loading&&<span className="loading-chip">Actualizando PMP...</span>}
  </div>

  <div className="cascade-selectors">
   <SearchableSelect
    label="1. Plan del PMP"
    value={chosenPlan}
    options={planOptions}
    onChange={selectPlan}
    placeholder="Haz clic o escribe un plan..."
    emptyText="No hay planes con los filtros seleccionados."
   />
   <SearchableSelect
    label="2. Actividad del plan"
    value={chosenActivity}
    options={activityOptions}
    onChange={selectActivity}
    disabled={!chosenPlan}
    placeholder={chosenPlan?'Haz clic o escribe una actividad...':'Primero selecciona un plan'}
    emptyText="Este plan no tiene actividades disponibles."
   />
   <SearchableSelect
    label="3. Equipo con esa actividad"
    value={currentId}
    options={equipmentOptions}
    onChange={chooseCurrent}
    disabled={!chosenActivity}
    placeholder={chosenActivity?'Haz clic o escribe equipo, código u OT...':'Primero selecciona una actividad'}
    emptyText="No hay equipos para esa actividad."
   />
  </div>

  <div className="cascade-counts">
   <span><b>{planOptions.length}</b> planes</span>
   <span><b>{activityOptions.length}</b> actividades del plan</span>
   <span><b>{equipmentOptions.length}</b> equipos / OT</span>
  </div>

  {current&&<div className="selected-equipment-card">
   <div className="selected-equipment-main">
    <span className="selection-label">SELECCIÓN ACTUAL</span>
    <h3>{current.activo_codigo} — {current.activo_descripcion}</h3>
    <p><b>{current.actividad}</b></p>
    <div className="selection-meta">
     <span>OT <b>{current.numero_orden||'—'}</b></span>
     <span>Área <b>{current.area_nombre||'—'}</b></span>
     <span>Criticidad <b>{current.criticidad||'—'}</b></span>
     <span>Condición <b>{current.condicion==='SIN CLASIFICAR'?'Sin definir':current.condicion}</b></span>
     <span>Personas <b>{current.personas_usar??'—'}</b></span>
     <span>H-H <b>{hh(current.hh_pmp)}</b></span>
    </div>
   </div>
   <div className="selection-action">
    {current.datos_completos
      ?<><span className="data-ready">Datos completos</span><button className="primary" onClick={()=>addItem(current)}>Agregar a semana</button></>
      :<><span className="data-missing">Falta {(current.datos_faltantes||[]).join(' + ')}</span><small>Completa la información debajo.</small></>}
   </div>
  </div>}

  {current&&!current.datos_completos&&<div className="learning-box">
   <div className="learning-copy"><span className="learning-tag">APRENDIZAJE</span><strong>{current.plan_trabajo}</strong><p>Falta: {(current.datos_faltantes||[]).join(', ')}. Se guardará como dato del plan para próximas programaciones.</p></div>
   <label>Condición<select value={learnCondition} onChange={e=>setLearnCondition(e.target.value)}><option value="">Definir</option>{CONDITIONS.map(x=><option key={x}>{x}</option>)}</select></label>
   <label>Número de personas<input type="number" min="1" step="1" value={learnPeople} onChange={e=>setLearnPeople(e.target.value)} placeholder="Ej. 2"/></label>
   <button onClick={completePlan} disabled={learning}>{learning?'Guardando...':'Guardar dato'}</button>
  </div>}

  <div className={'message '+(message.includes('agregada')||message.includes('guardada')||message.includes('aprendido')?'success':'')}>{message}</div>

  <div className="programmed-head">
   <div><span className="step-number">5</span><div><h3>Programación de {specialtyName}</h3><p>{selected.length} actividades seleccionadas · {used.toFixed(1)} de {target.toFixed(1)} H-H.</p></div></div>
   <div className="table-actions"><button onClick={()=>exportCsv(selected,specialty)}>Exportar CSV</button><button className="primary" onClick={save}>Guardar semana</button></div>
  </div>

  <div className="table-wrap selected-table">
   <table>
    <thead><tr><th></th><th>OT</th><th>Área</th><th>Activo</th><th>Plan</th><th>Actividad</th><th>Crit.</th><th>Personas</th><th>H-H</th><th>Origen</th></tr></thead>
    <tbody>
     {!selected.length&&<tr><td colSpan="10" className="empty">La programación está vacía. Selecciona Plan → Actividad → Equipo y agrega actividades.</td></tr>}
     {selected.map(x=><tr key={x.pmp_id}>
      <td><button className="remove-btn" onClick={()=>setSelected(p=>p.filter(i=>i.pmp_id!==x.pmp_id))}>×</button></td>
      <td><b>{x.numero_orden||'—'}</b></td><td>{x.area_nombre}</td>
      <td><span className="asset-code">{x.activo_codigo}</span><small className="asset-name">{x.activo_descripcion}</small></td>
      <td>{x.plan_trabajo}</td><td>{x.actividad}</td><td>{x.criticidad}</td><td>{x.personas_usar}</td><td><b>{hh(x.hh_pmp)}</b></td><td>{x.origen}</td>
     </tr>)}
    </tbody>
   </table>
  </div>
 </div>
}
