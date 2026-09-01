import {useEffect,useMemo,useState} from 'react'
import {getCandidates,learnPlan,saveProgramming} from '../api'

const CONDITIONS=['OPERANDO','EQUIPO DETENIDO','LINEA DETENIDA','AREA/PLANTA DETENIDA']

function hh(v){
 return v===null||v===undefined?'—':Number(v).toFixed(1)+' H-H'
}
function pct(v,max){
 if(!max)return 0
 return Math.min(100,Math.max(0,(v/max)*100))
}
function exportCsv(rows,specialty){
 if(!rows.length)return
 const headers=['Orden','Área','Activo','Descripción','Plan','Criticidad','Condición','Personas','Tiempo min','H-H','Origen']
 const data=rows.map(x=>[x.numero_orden||'',x.area_nombre||'',x.activo_codigo,x.activo_descripcion,x.plan_trabajo,x.criticidad||'',x.condicion,x.personas_usar,x.tiempo_planeado_min,x.hh_pmp,x.origen])
 const csv=[headers,...data].map(r=>r.map(v=>`"${String(v??'').replaceAll('"','""')}"`).join(',')).join('\n')
 const blob=new Blob(['\ufeff'+csv],{type:'text/csv;charset=utf-8'})
 const url=URL.createObjectURL(blob),a=document.createElement('a')
 a.href=url;a.download=`programacion_${specialty}.csv`;a.click();URL.revokeObjectURL(url)
}

export default function SpecialtyPlanner({specialty,specialtyName,capacity,week,year,month}){
 const [candidates,setCandidates]=useState([])
 const [selected,setSelected]=useState([])
 const [area,setArea]=useState(''),[criticality,setCriticality]=useState(''),[condition,setCondition]=useState('')
 const [origin,setOrigin]=useState('MES'),[group,setGroup]=useState(''),[chosenPlan,setChosenPlan]=useState('')
 const [planText,setPlanText]=useState(''),[currentId,setCurrentId]=useState('')
 const [message,setMessage]=useState(''),[refresh,setRefresh]=useState(0),[loading,setLoading]=useState(false)
 const [learnCondition,setLearnCondition]=useState(''),[learnPeople,setLearnPeople]=useState(''),[learning,setLearning]=useState(false)

 useEffect(()=>{
  setSelected([]);setGroup('');setChosenPlan('');setPlanText('');setCurrentId('');setMessage('')
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

 const available=useMemo(()=>candidates.filter(x=>!selected.some(s=>s.pmp_id===x.pmp_id)),[candidates,selected])
 const areaOptions=useMemo(()=>[...new Set(candidates.map(x=>x.area_nombre).filter(Boolean))].sort(),[candidates])
 const groupOptions=useMemo(()=>[...new Set(available.map(x=>x.grupo_plan).filter(Boolean))].sort(),[available])
 const groupRows=useMemo(()=>group?available.filter(x=>x.grupo_plan===group):[],[available,group])
 const planOptions=useMemo(()=>[...new Set(groupRows.map(x=>x.plan_trabajo).filter(Boolean))].sort(),[groupRows])
 const visiblePlans=useMemo(()=>planOptions.filter(p=>!planText||p.toLowerCase().includes(planText.toLowerCase())).slice(0,60),[planOptions,planText])
 const equipment=useMemo(()=>chosenPlan?groupRows.filter(x=>x.plan_trabajo===chosenPlan):[],[groupRows,chosenPlan])
 const current=useMemo(()=>candidates.find(x=>String(x.pmp_id)===String(currentId)),[candidates,currentId])

 const target=Number(capacity?.target||0)
 const total=Number(capacity?.available||0)
 const standby=Number(capacity?.standby||0)
 const used=selected.reduce((sum,x)=>sum+Number(x.hh_pmp||0),0)
 const remaining=Math.max(0,target-used)
 const ready=available.filter(x=>x.datos_completos).length
 const incomplete=available.length-ready

 function resetFlow(){
  setGroup('');setChosenPlan('');setPlanText('');setCurrentId('')
 }
 function chooseGroup(value){
  setGroup(value);setChosenPlan('');setPlanText('');setCurrentId('')
 }
 function choosePlan(plan){
  setChosenPlan(plan);setPlanText(plan);setCurrentId('')
 }
 function chooseCurrent(item){
  setCurrentId(String(item.pmp_id))
  setLearnCondition(item.condicion==='SIN CLASIFICAR'?'':item.condicion)
  setLearnPeople(item.personas_usar??'')
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
  if(!item)return setMessage('Selecciona una orden o equipo.')
  if(!item.datos_completos){chooseCurrent(item);return setMessage('Esta actividad necesita completar datos antes de programarla.')}
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

  <div className="candidate-summary">
   <div><b>{available.length}</b><span>PMP pendientes disponibles</span></div>
   <div className="ok"><b>{ready}</b><span>Listos para programar</span></div>
   <div className="warn"><b>{incomplete}</b><span>Necesitan completar datos</span></div>
  </div>

  <div className="subsection-title">
   <div><span className="step-number">3</span><div><h3>Filtra y encuentra el plan</h3><p>Reduce la lista antes de entrar a Planeación → Plan de trabajo → Equipo.</p></div></div>
   <button className="ghost" onClick={()=>{setArea('');setCriticality('');setCondition('');setOrigin('MES');resetFlow()}}>Limpiar filtros</button>
  </div>

  <div className="filters">
   <label>Área<select value={area} onChange={e=>{setArea(e.target.value);resetFlow()}}><option value="">Todas las áreas</option>{areaOptions.map(x=><option key={x}>{x}</option>)}</select></label>
   <label>Criticidad<select value={criticality} onChange={e=>{setCriticality(e.target.value);resetFlow()}}><option value="">A, B y C</option><option>A</option><option>B</option><option>C</option></select></label>
   <label>Condición<select value={condition} onChange={e=>{setCondition(e.target.value);resetFlow()}}><option value="">Todas</option><option>OPERANDO</option><option>EQUIPO DETENIDO</option><option>LINEA DETENIDA</option><option>AREA/PLANTA DETENIDA</option><option>SIN CLASIFICAR</option></select></label>
   <label>Origen<select value={origin} onChange={e=>{setOrigin(e.target.value);resetFlow()}}><option value="MES">PMP del mes</option><option value="BACKLOG">Backlog</option><option value="ALL">Mes + backlog</option></select></label>
  </div>

  <div className="planning-flow">
   <label><span>1. Planeación / grupo</span><select value={group} onChange={e=>chooseGroup(e.target.value)}><option value="">Selecciona un grupo</option>{groupOptions.map(x=><option key={x}>{x}</option>)}</select></label>

   <div className="plan-combo">
    <label><span>2. Plan de trabajo</span><input value={planText} disabled={!group} onChange={e=>{setPlanText(e.target.value);setChosenPlan('');setCurrentId('')}} placeholder={group?'Buscar plan...':'Primero selecciona un grupo'}/></label>
    {group&&planText&&!chosenPlan&&<div className="suggestions">{visiblePlans.map(p=><button key={p} onClick={()=>choosePlan(p)}>{p}</button>)}{!visiblePlans.length&&<div className="no-result">No hay planes con ese texto.</div>}</div>}
   </div>

   <div className="flow-status">
    <span>Resultado</span>
    <b>{chosenPlan?equipment.length:0} equipos / OT</b>
   </div>
  </div>

  <div className="equipment-panel">
   <div className="equipment-head">
    <div><h3>{chosenPlan||'Equipos del plan seleccionado'}</h3><p>{chosenPlan?'Selecciona las actividades que quieres llevar a la semana.':'Escoge un grupo y un plan de trabajo para ver sus equipos.'}</p></div>
    {loading&&<span className="loading-chip">Actualizando...</span>}
   </div>
   <div className="table-wrap compact-table">
    <table>
     <thead><tr><th>OT</th><th>Área</th><th>Equipo</th><th>Crit.</th><th>Condición</th><th>Personas</th><th>H-H</th><th>Datos</th><th></th></tr></thead>
     <tbody>
      {!equipment.length&&<tr><td colSpan="9" className="empty">No hay equipos para mostrar todavía.</td></tr>}
      {equipment.map(item=><tr key={item.pmp_id} className={String(currentId)===String(item.pmp_id)?'row-active':''}>
       <td><b>{item.numero_orden||'—'}</b></td>
       <td>{item.area_nombre||'—'}</td>
       <td><span className="asset-code">{item.activo_codigo}</span><small className="asset-name">{item.activo_descripcion}</small></td>
       <td><span className={'criticality crit-'+(item.criticidad||'x')}>{item.criticidad||'—'}</span></td>
       <td>{item.condicion==='SIN CLASIFICAR'?'Sin definir':item.condicion}</td>
       <td>{item.personas_usar??'—'}</td>
       <td><b>{hh(item.hh_pmp)}</b></td>
       <td>{item.datos_completos?<span className="data-ready">Listo</span>:<span className="data-missing">Falta {(item.datos_faltantes||[]).join(' + ')}</span>}</td>
       <td><button className={item.datos_completos?'add-btn':'complete-btn'} onClick={()=>item.datos_completos?addItem(item):chooseCurrent(item)}>{item.datos_completos?'Agregar':'Completar'}</button></td>
      </tr>)}
     </tbody>
    </table>
   </div>
  </div>

  {current&&!current.datos_completos&&<div className="learning-box">
   <div className="learning-copy"><span className="learning-tag">APRENDIZAJE</span><strong>{current.plan_trabajo}</strong><p>Falta: {(current.datos_faltantes||[]).join(', ')}. Se guardará como dato del plan para próximas programaciones.</p></div>
   <label>Condición<select value={learnCondition} onChange={e=>setLearnCondition(e.target.value)}><option value="">Definir</option>{CONDITIONS.map(x=><option key={x}>{x}</option>)}</select></label>
   <label>Número de personas<input type="number" min="1" step="1" value={learnPeople} onChange={e=>setLearnPeople(e.target.value)} placeholder="Ej. 2"/></label>
   <button onClick={completePlan} disabled={learning}>{learning?'Guardando...':'Guardar dato'}</button>
  </div>}

  <div className={'message '+(message.includes('agregada')||message.includes('guardada')||message.includes('aprendido')?'success':'')}>{message}</div>

  <div className="programmed-head">
   <div><span className="step-number">4</span><div><h3>Programación de {specialtyName}</h3><p>{selected.length} actividades seleccionadas · {used.toFixed(1)} de {target.toFixed(1)} H-H.</p></div></div>
   <div className="table-actions"><button onClick={()=>exportCsv(selected,specialty)}>Exportar CSV</button><button className="primary" onClick={save}>Guardar semana</button></div>
  </div>

  <div className="table-wrap selected-table">
   <table>
    <thead><tr><th></th><th>OT</th><th>Área</th><th>Activo</th><th>Plan</th><th>Crit.</th><th>Personas</th><th>H-H</th><th>Origen</th></tr></thead>
    <tbody>
     {!selected.length&&<tr><td colSpan="9" className="empty">La programación está vacía. Agrega actividades desde la tabla superior.</td></tr>}
     {selected.map(x=><tr key={x.pmp_id}>
      <td><button className="remove-btn" onClick={()=>setSelected(p=>p.filter(i=>i.pmp_id!==x.pmp_id))}>×</button></td>
      <td><b>{x.numero_orden||'—'}</b></td><td>{x.area_nombre}</td>
      <td><span className="asset-code">{x.activo_codigo}</span><small className="asset-name">{x.activo_descripcion}</small></td>
      <td>{x.plan_trabajo}</td><td>{x.criticidad}</td><td>{x.personas_usar}</td><td><b>{hh(x.hh_pmp)}</b></td><td>{x.origen}</td>
     </tr>)}
    </tbody>
   </table>
  </div>
 </div>
}
