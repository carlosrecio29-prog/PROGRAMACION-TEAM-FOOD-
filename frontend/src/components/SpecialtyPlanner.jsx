import {useEffect,useMemo,useState} from 'react'
import {downloadProgrammingExport,getCandidates,getMonthReconciliation,saveProgramming} from '../api'

const STOPPED_CONDITIONS=['EQUIPO DETENIDO','LINEA DETENIDA','AREA/PLANTA DETENIDA']

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
 },[value,selectedLabel,typed])

 const visible=useMemo(()=>{
  if(!typed)return options.slice(0,120)
  const q=query.trim().toLowerCase()
  if(!q)return options.slice(0,120)
  return options.filter(o=>(o.search||o.label).toLowerCase().includes(q)).slice(0,120)
 },[options,query,typed])

 function handleChange(e){
  setQuery(e.target.value)
  setTyped(true)
  setOpen(true)
  if(value)onChange('')
 }

 return <div className={'search-select '+(disabled?'disabled':'')}>
  <label><span>{label}</span>
   <div className="search-select-box">
    <input
     value={query}
     disabled={disabled}
     placeholder={placeholder}
     onFocus={()=>{if(!disabled){setOpen(true);setTyped(false)}}}
     onChange={handleChange}
     onBlur={()=>window.setTimeout(()=>setOpen(false),120)}
     autoComplete="off"
    />
    <button type="button" tabIndex="-1" disabled={disabled}
     onMouseDown={e=>e.preventDefault()}
     onClick={()=>{setOpen(v=>!v);setTyped(false)}}>⌄</button>
   </div>
  </label>
  {open&&!disabled&&<div className="search-options">
   {visible.map(o=><button type="button" key={String(o.value)}
    onMouseDown={e=>e.preventDefault()}
    onClick={()=>{onChange(o.value);setQuery(o.label);setTyped(false);setOpen(false)}}>{o.label}</button>)}
   {!visible.length&&<div className="no-result">{emptyText}</div>}
   {options.length>120&&!typed&&<div className="more-results">Escribe para filtrar entre {options.length} opciones.</div>}
  </div>}
 </div>
}

export default function SpecialtyPlanner({specialty,specialtyName,capacity,week,year,month}){
 const [operatingRows,setOperatingRows]=useState([])
 const [stoppedRows,setStoppedRows]=useState([])
 const [selected,setSelected]=useState([])
 const [area,setArea]=useState('')
 const [criticality,setCriticality]=useState('')
 const [origin,setOrigin]=useState('MES')
 const [chosenPlan,setChosenPlan]=useState('')
 const [chosenActivity,setChosenActivity]=useState('')
 const [currentId,setCurrentId]=useState('')
 const [stoppedSearch,setStoppedSearch]=useState('')
 const [message,setMessage]=useState('')
 const [refresh,setRefresh]=useState(0)
 const [loading,setLoading]=useState(false)
 const [reconciliation,setReconciliation]=useState({})
 const [lastSaved,setLastSaved]=useState(null)
 const [exporting,setExporting]=useState('')

 useEffect(()=>{
  setSelected([])
  setChosenPlan('')
  setChosenActivity('')
  setCurrentId('')
  setStoppedSearch('')
  setMessage('')
  setLastSaved(null)
 },[specialty,week?.from,week?.to])

 useEffect(()=>{
  let active=true
  const timer=setTimeout(async()=>{
   try{
    setLoading(true)
    const common={
     specialty,year,month,
     area:area||undefined,
     criticality:criticality||undefined,
     origin,
     limit:2000
    }
    const [operating,...stoppedSets]=await Promise.all([
     getCandidates({...common,condition:'OPERANDO'}),
     ...STOPPED_CONDITIONS.map(condition=>getCandidates({...common,condition}))
    ])
    if(!active)return
    setOperatingRows(operating)
    const map=new Map()
    stoppedSets.flat().forEach(x=>map.set(x.pmp_id,x))
    setStoppedRows([...map.values()])
   }catch(e){
    if(active)setMessage(e.message)
   }finally{
    if(active)setLoading(false)
   }
  },120)
  return()=>{active=false;clearTimeout(timer)}
 },[specialty,year,month,area,criticality,origin,refresh])

 useEffect(()=>{
  let active=true
  getMonthReconciliation(year,month)
   .then(r=>{if(active)setReconciliation(r||{})})
   .catch(()=>{if(active)setReconciliation({})})
  return()=>{active=false}
 },[year,month,refresh])

 const operatingReady=useMemo(
  ()=>operatingRows.filter(x=>x.datos_completos&&!selected.some(s=>s.pmp_id===x.pmp_id)),
  [operatingRows,selected]
 )
 const stoppedReady=useMemo(
  ()=>stoppedRows.filter(x=>x.datos_completos&&!selected.some(s=>s.pmp_id===x.pmp_id)),
  [stoppedRows,selected]
 )

 const allVisible=useMemo(()=>[...operatingRows,...stoppedRows],[operatingRows,stoppedRows])
 const areaOptions=useMemo(
  ()=>[...new Set(allVisible.map(x=>x.area_nombre).filter(Boolean))].sort(),
  [allVisible]
 )

 const planOptions=useMemo(()=>uniqueOptions(operatingReady,'plan_trabajo'),[operatingReady])
 const planRows=useMemo(
  ()=>chosenPlan?operatingReady.filter(x=>x.plan_trabajo===chosenPlan):[],
  [operatingReady,chosenPlan]
 )
 const activityOptions=useMemo(()=>uniqueOptions(planRows,'actividad'),[planRows])
 const activityRows=useMemo(
  ()=>chosenActivity?planRows.filter(x=>x.actividad===chosenActivity):[],
  [planRows,chosenActivity]
 )
 const equipmentOptions=useMemo(()=>activityRows.map(x=>({
   value:String(x.pmp_id),
   label:`${x.activo_codigo} — ${x.activo_descripcion} — ${x.numero_orden||'SIN OT'}`,
   search:`${x.activo_codigo} ${x.activo_descripcion} ${x.numero_orden||''} ${x.area_nombre||''}`
 })),[activityRows])

 const current=useMemo(
  ()=>operatingReady.find(x=>String(x.pmp_id)===String(currentId)),
  [operatingReady,currentId]
 )

 const stoppedFiltered=useMemo(()=>{
  const q=stoppedSearch.trim().toLowerCase()
  if(!q)return stoppedReady
  return stoppedReady.filter(x=>[
   x.numero_orden,x.area_nombre,x.activo_codigo,x.activo_descripcion,
   x.actividad,x.plan_trabajo,x.criticidad,x.condicion
  ].some(v=>String(v||'').toLowerCase().includes(q)))
 },[stoppedReady,stoppedSearch])

 const stats=reconciliation[specialty]||{}
 const target=Number(capacity?.target||0)
 const total=Number(capacity?.available||0)
 const standby=Number(capacity?.standby||0)
 const used=selected.reduce((sum,x)=>sum+Number(x.hh_pmp||0),0)
 const remaining=Math.max(0,target-used)

 function resetSelectors(){
  setChosenPlan('')
  setChosenActivity('')
  setCurrentId('')
 }

 function addItem(item){
  if(!item)return setMessage('Selecciona un PMP.')
  if(!item.datos_completos)return setMessage('Este PMP todavía está en Pendientes por definir.')
  if(selected.some(x=>x.pmp_id===item.pmp_id))return
  const next=used+Number(item.hh_pmp||0)
  if(target<=0)return setMessage('Primero selecciona una semana con capacidad disponible.')
  if(next>target+.0001)return setMessage(
   `No se puede agregar: quedarías en ${next.toFixed(1)} H-H y la meta es ${target.toFixed(1)} H-H.`
  )
  setSelected(prev=>[...prev,item])
  setCurrentId('')
  setMessage(`${item.numero_orden||'PMP'} agregado a la programación.`)
 }

 async function save(){
  if(!week?.from||!week?.to)return setMessage('Selecciona la semana.')
  if(!selected.length)return setMessage('Agrega al menos una actividad.')
  try{
   const r=await saveProgramming({
    date_from:week.from,
    date_to:week.to,
    specialty,
    pmp_ids:selected.map(x=>x.pmp_id),
    created_by:'PRUEBA_WEB'
   })
   setLastSaved(r)
   setMessage(
    `Programación guardada · ${Number(r.hh_programmed).toFixed(1)} H-H · versión ${r.version}. Puedes verla en Programaciones guardadas.`
   )
   setSelected([])
   resetSelectors()
   setRefresh(x=>x+1)
  }catch(e){setMessage(e.message)}
 }

 async function exportSaved(format){
  if(!lastSaved?.version_id)return setMessage('Primero guarda la programación semanal.')
  try{
   setExporting(format)
   await downloadProgrammingExport(lastSaved.version_id,format)
  }catch(e){setMessage(e.message)}
  finally{setExporting('')}
 }

 return <div className="planner">
  <div className="capacity-strip">
   <div><span>Técnicos</span><b>{Number(capacity?.technicians||0)}</b><small>en {specialtyName}</small></div>
   <div><span>Capacidad real</span><b>{total.toFixed(1)}</b><small>H-H disponibles</small></div>
   <div className="target-card"><span>Meta programable</span><b>{target.toFixed(1)}</b><small>80% de capacidad</small></div>
   <div><span>Seleccionadas</span><b>{used.toFixed(1)}</b><small>{remaining.toFixed(1)} H-H por usar</small></div>
   <div><span>Reserva</span><b>{standby.toFixed(1)}</b><small>20% standby</small></div>
  </div>

  <div className="capacity-progress">
   <div className="progress-copy"><span>Uso de la meta semanal</span><b>{pct(used,target).toFixed(0)}%</b></div>
   <div className="progress-track"><i style={{width:pct(used,target)+'%'}}/></div>
  </div>

  <div className="reconciliation-card">
   <div className="reconciliation-head">
    <div>
     <span className="section-kicker">CONCILIACIÓN CON MAESTRO</span>
     <h3>De Excel a programación</h3>
     <p>Las OT repetidas se consolidan; las OT distintas se conservan como PMP independientes.</p>
    </div>
    <span className="reconciliation-period">{String(month).padStart(2,'0')} / {year}</span>
   </div>
   <div className="reconciliation-grid">
    <div><span>PMP en maestro</span><b>{Number(stats.master_rows||0)}</b><small>Filas de {specialtyName}</small></div>
    <div><span>OT únicas</span><b>{Number(stats.unique_ot||0)}</b><small>{Number(stats.repeated_extra_rows||0)} repetidas consolidadas</small></div>
    <div><span>Pendientes</span><b>{Number(stats.pending_unique_ot||0)}</b><small>OT pendientes únicas</small></div>
    <div><span>Finalizadas</span><b>{Number(stats.finalized_unique_ot||0)}</b><small>No entran a programación</small></div>
    <div className="reconciliation-warn"><span>Inconsistencias</span><b>{Number(stats.pending_exceptions||0)}</b><small>Relación con maestro</small></div>
    <div className="reconciliation-ok"><span>Disponibles ahora</span><b>{Number(stats.available_now||0)}</b><small>Antes de definir/filtrar</small></div>
   </div>
  </div>

  <div className="programming-groups">
   <div className="programming-group-card operating">
    <span>ATENDIBLES OPERANDO</span>
    <b>{operatingReady.length}</b>
    <small>PMP completos que no requieren detener el equipo</small>
   </div>
   <div className="programming-group-card stopped">
    <span>REQUIEREN DETENCIÓN</span>
    <b>{stoppedReady.length}</b>
    <small>Equipo, línea o planta detenida</small>
   </div>
   <div className="programming-group-card selected">
    <span>EN ESTA PROGRAMACIÓN</span>
    <b>{selected.length}</b>
    <small>{used.toFixed(1)} H-H seleccionadas</small>
   </div>
  </div>

  <div className="subsection-title">
   <div><span className="step-number">3</span><div>
    <h3>Filtros de programación</h3>
    <p>Los datos incompletos ya no aparecen aquí: se gestionan en “Pendientes por definir”.</p>
   </div></div>
   <button className="ghost" onClick={()=>{setArea('');setCriticality('');setOrigin('MES');resetSelectors()}}>Limpiar filtros</button>
  </div>

  <div className="filters programming-filters">
   <label>Área<select value={area} onChange={e=>{setArea(e.target.value);resetSelectors()}}>
    <option value="">Todas las áreas</option>{areaOptions.map(x=><option key={x}>{x}</option>)}
   </select></label>
   <label>Criticidad<select value={criticality} onChange={e=>{setCriticality(e.target.value);resetSelectors()}}>
    <option value="">A, B y C</option><option>A</option><option>B</option><option>C</option>
   </select></label>
   <label>Origen<select value={origin} onChange={e=>{setOrigin(e.target.value);resetSelectors()}}>
    <option value="MES">PMP del mes</option><option value="BACKLOG">Backlog</option><option value="ALL">Mes + backlog</option>
   </select></label>
   <div className="definitions-hint">
    <span>¿Falta tiempo, personas o condición?</span>
    <b>Usa “Pendientes por definir” en el menú izquierdo.</b>
   </div>
  </div>

  <section className="operating-section">
   <div className="subsection-title selection-title">
    <div><span className="step-number">4A</span><div>
     <h3>PMP que se pueden atender OPERANDO</h3>
     <p>Selecciona Plan → Actividad → Equipo. Solo aparecen PMP con todos sus datos completos.</p>
    </div></div>
    {loading&&<span className="loading-chip">Actualizando...</span>}
   </div>

   <div className="cascade-selectors">
    <SearchableSelect
     label="1. Plan del PMP"
     value={chosenPlan}
     options={planOptions}
     onChange={v=>{setChosenPlan(v);setChosenActivity('');setCurrentId('')}}
     placeholder="Haz clic o escribe un plan..."
     emptyText="No hay planes operando con estos filtros."
    />
    <SearchableSelect
     label="2. Actividad del plan"
     value={chosenActivity}
     options={activityOptions}
     onChange={v=>{setChosenActivity(v);setCurrentId('')}}
     disabled={!chosenPlan}
     placeholder={chosenPlan?'Haz clic o escribe una actividad...':'Primero selecciona un plan'}
    />
    <SearchableSelect
     label="3. Equipo con esa actividad"
     value={currentId}
     options={equipmentOptions}
     onChange={setCurrentId}
     disabled={!chosenActivity}
     placeholder={chosenActivity?'Haz clic o escribe equipo, código u OT...':'Primero selecciona una actividad'}
    />
   </div>

   <div className="cascade-counts">
    <span><b>{planOptions.length}</b> planes</span>
    <span><b>{activityOptions.length}</b> actividades</span>
    <span><b>{equipmentOptions.length}</b> equipos / OT</span>
   </div>

   {current&&<div className="selected-equipment-card">
    <div className="selected-equipment-main">
     <span className="selection-label">PMP OPERANDO</span>
     <h3>{current.activo_codigo} — {current.activo_descripcion}</h3>
     <p><b>{current.actividad}</b></p>
     <div className="selection-meta">
      <span>OT <b>{current.numero_orden||'—'}</b></span>
      <span>Área <b>{current.area_nombre||'—'}</b></span>
      <span>Criticidad <b>{current.criticidad||'—'}</b></span>
      <span>Personas <b>{current.personas_usar}</b></span>
      <span>H-H <b>{hh(current.hh_pmp)}</b></span>
     </div>
    </div>
    <div className="selection-action">
     <span className="data-ready">OPERANDO</span>
     <button className="primary" onClick={()=>addItem(current)}>Agregar a semana</button>
    </div>
   </div>}
  </section>

  <section className="stopped-section">
   <div className="stopped-head">
    <div>
     <span className="stopped-kicker">4B · DETENCIÓN REQUERIDA</span>
     <h3>PMP que necesitan equipo, línea o planta detenida</h3>
     <p>Selecciona directamente desde la tabla los trabajos que aprovecharás en la ventana de detención.</p>
    </div>
    <div className="stopped-tools">
     <input value={stoppedSearch} onChange={e=>setStoppedSearch(e.target.value)}
      placeholder="Buscar OT, equipo, actividad o plan..."/>
     <span>{stoppedFiltered.length} PMP</span>
    </div>
   </div>

   <div className="table-wrap stopped-table">
    <table>
     <thead><tr><th>OT</th><th>Área</th><th>Equipo</th><th>Actividad</th><th>Plan</th><th>Condición</th><th>Crit.</th><th>Personas</th><th>H-H</th><th></th></tr></thead>
     <tbody>
      {loading&&<tr><td colSpan="10" className="empty">Cargando PMP...</td></tr>}
      {!loading&&!stoppedFiltered.length&&<tr><td colSpan="10" className="empty">No hay PMP completos que requieran detención con estos filtros.</td></tr>}
      {!loading&&stoppedFiltered.slice(0,300).map(x=><tr key={x.pmp_id}>
       <td><b>{x.numero_orden||'—'}</b></td>
       <td>{x.area_nombre||'—'}</td>
       <td><span className="asset-code">{x.activo_codigo}</span><small className="asset-name">{x.activo_descripcion}</small></td>
       <td>{x.actividad||'—'}</td>
       <td>{x.plan_trabajo}</td>
       <td><span className="shutdown-type">{x.condicion}</span></td>
       <td><span className={'criticality crit-'+(x.criticidad||'x')}>{x.criticidad||'—'}</span></td>
       <td>{x.personas_usar}</td>
       <td><b>{hh(x.hh_pmp)}</b></td>
       <td><button className="add-btn" onClick={()=>addItem(x)}>Agregar</button></td>
      </tr>)}
     </tbody>
    </table>
   </div>
   {stoppedFiltered.length>300&&<small className="stopped-limit">Mostrando 300 de {stoppedFiltered.length}. Usa el buscador para reducir la lista.</small>}
  </section>

  <div className={'message '+(message.includes('agregado')||message.includes('guardada')?'success':'')}>{message}</div>

  <div className="programmed-head">
   <div><span className="step-number">5</span><div>
    <h3>Programación de {specialtyName}</h3>
    <p>{selected.length} actividades seleccionadas · {used.toFixed(1)} de {target.toFixed(1)} H-H.</p>
   </div></div>
   <div className="table-actions">
    {lastSaved&&<>
     <button className="export-excel" onClick={()=>exportSaved('xlsx')} disabled={!!exporting}>{exporting==='xlsx'?'Generando...':'Exportar Excel'}</button>
     <button className="export-pdf" onClick={()=>exportSaved('pdf')} disabled={!!exporting}>{exporting==='pdf'?'Generando...':'Exportar PDF'}</button>
    </>}
    <button className="primary" onClick={save}>Guardar semana</button>
   </div>
  </div>

  <div className="table-wrap selected-table">
   <table>
    <thead><tr><th></th><th>OT</th><th>Área</th><th>Activo</th><th>Actividad</th><th>Plan</th><th>Condición</th><th>Crit.</th><th>Personas</th><th>H-H</th><th>Origen</th></tr></thead>
    <tbody>
     {!selected.length&&<tr><td colSpan="11" className="empty">La programación está vacía. Agrega PMP desde OPERANDO o desde DETENCIÓN.</td></tr>}
     {selected.map(x=><tr key={x.pmp_id}>
      <td><button className="remove-btn" onClick={()=>setSelected(p=>p.filter(i=>i.pmp_id!==x.pmp_id))}>×</button></td>
      <td><b>{x.numero_orden||'—'}</b></td>
      <td>{x.area_nombre}</td>
      <td><span className="asset-code">{x.activo_codigo}</span><small className="asset-name">{x.activo_descripcion}</small></td>
      <td>{x.actividad}</td>
      <td>{x.plan_trabajo}</td>
      <td>{x.condicion}</td>
      <td>{x.criticidad}</td>
      <td>{x.personas_usar}</td>
      <td><b>{hh(x.hh_pmp)}</b></td>
      <td>{x.origen}</td>
     </tr>)}
    </tbody>
   </table>
  </div>
 </div>
}
