import {useEffect,useMemo,useState} from 'react'
import {getCandidates,learnPlan,saveProgramming} from '../api'

const CONDITIONS=['OPERANDO','EQUIPO DETENIDO','LINEA DETENIDA','AREA/PLANTA DETENIDA']
function hh(v){return v===null||v===undefined?'Pendiente':Number(v).toFixed(1)+' HH'}
function exportCsv(rows,specialty){
 if(!rows.length)return
 const headers=['Orden','Área','Línea','Activo','Descripción','Grupo','Plan','Criticidad','Condición','Personas','Tiempo min','HH','Origen']
 const data=rows.map(x=>[x.numero_orden||'',x.area_nombre||'',x.linea_nombre||'',x.activo_codigo,x.activo_descripcion,x.grupo_plan,x.plan_trabajo,x.criticidad||'',x.condicion,x.personas_usar,x.tiempo_planeado_min,x.hh_pmp,x.origen])
 const csv=[headers,...data].map(r=>r.map(v=>`"${String(v??'').replaceAll('"','""')}"`).join(',')).join('\n')
 const blob=new Blob(['\ufeff'+csv],{type:'text/csv;charset=utf-8'}),url=URL.createObjectURL(blob),a=document.createElement('a')
 a.href=url;a.download=`programacion_${specialty}.csv`;a.click();URL.revokeObjectURL(url)
}

export default function SpecialtyPlanner({specialty,capacity,week}){
 const [candidates,setCandidates]=useState([]),[selected,setSelected]=useState([])
 const [area,setArea]=useState(''),[criticality,setCriticality]=useState(''),[condition,setCondition]=useState('')
 const [origin,setOrigin]=useState('MES'),[group,setGroup]=useState(''),[planText,setPlanText]=useState('')
 const [chosenPlan,setChosenPlan]=useState(''),[equipmentId,setEquipmentId]=useState('')
 const [message,setMessage]=useState(''),[refresh,setRefresh]=useState(0)
 const [learnCondition,setLearnCondition]=useState(''),[learnPeople,setLearnPeople]=useState(''),[learning,setLearning]=useState(false)

 useEffect(()=>{
  const timer=setTimeout(async()=>{
   try{
    const rows=await getCandidates({specialty,area:area||undefined,criticality:criticality||undefined,
      condition:condition||undefined,origin,plan_search:planText||undefined,limit:1500})
    setCandidates(rows.filter(x=>!selected.some(s=>s.pmp_id===x.pmp_id)))
   }catch(e){setMessage(e.message)}
  },180)
  return()=>clearTimeout(timer)
 },[specialty,area,criticality,condition,origin,planText,selected,refresh])

 useEffect(()=>{setGroup('');setChosenPlan('');setEquipmentId('');setPlanText('')},[specialty,origin])

 const areaOptions=useMemo(()=>[...new Set(candidates.map(x=>x.area_nombre).filter(Boolean))].sort(),[candidates])
 const groupOptions=useMemo(()=>[...new Set(candidates.map(x=>x.grupo_plan).filter(Boolean))].sort(),[candidates])
 const groupRows=useMemo(()=>group?candidates.filter(x=>x.grupo_plan===group):candidates,[candidates,group])
 const planOptions=useMemo(()=>[...new Set(groupRows.map(x=>x.plan_trabajo))].sort(),[groupRows])
 const equipment=useMemo(()=>groupRows.filter(x=>x.plan_trabajo===chosenPlan),[groupRows,chosenPlan])
 const current=useMemo(()=>candidates.find(x=>String(x.pmp_id)===equipmentId),[candidates,equipmentId])
 const target=Number(capacity?.target||0)
 const used=selected.reduce((s,x)=>s+Number(x.hh_pmp||0),0)

 function choosePlan(plan){setChosenPlan(plan);setPlanText(plan);setEquipmentId('')}
 function selectEquipment(value){
  setEquipmentId(value)
  const item=candidates.find(x=>String(x.pmp_id)===value)
  if(item){
   setLearnCondition(item.condicion==='SIN CLASIFICAR'?'':item.condicion)
   setLearnPeople(item.personas_usar??'')
  }
 }
 async function completePlan(){
  if(!current)return
  if((current.datos_faltantes||[]).includes('CONDICION')&&!learnCondition)return setMessage('Define si el equipo opera o debe detenerse')
  if((current.datos_faltantes||[]).includes('PERSONAS')&&!learnPeople)return setMessage('Indica cuántas personas requiere el plan')
  try{
   setLearning(true)
   await learnPlan(current.plan_trabajo_id,{condition:learnCondition||current.condicion,people:learnPeople?Number(learnPeople):null})
   setMessage('Datos guardados. Este plan ya quedó aprendido para próximas programaciones.')
   setRefresh(x=>x+1)
  }catch(e){setMessage(e.message)}finally{setLearning(false)}
 }
 function add(){
  const item=current
  if(!item)return setMessage('Selecciona un equipo')
  if(!item.datos_completos)return setMessage('Completa los datos faltantes del plan antes de agregarlo')
  const next=used+Number(item.hh_pmp||0)
  if(target<=0)return setMessage('Primero calcula la disponibilidad de la semana')
  if(next>target+.0001)return setMessage(`No se puede agregar: ${next.toFixed(1)} HH supera la meta ${target.toFixed(1)} HH`)
  setSelected(p=>[...p,item]);setEquipmentId('');setMessage('Actividad agregada')
 }
 async function save(){
  if(!week?.from||!week?.to)return setMessage('Selecciona y calcula la semana primero')
  if(!selected.length)return setMessage('No hay actividades seleccionadas')
  try{
   const r=await saveProgramming({date_from:week.from,date_to:week.to,specialty,pmp_ids:selected.map(x=>x.pmp_id)})
   setMessage(`Programación guardada · ${Number(r.hh_programmed).toFixed(1)} HH · versión ${r.version}`)
   setSelected([]);setRefresh(x=>x+1)
  }catch(e){setMessage(e.message)}
 }

 return <section className="planner">
  <div className="metrics">
   <div><span>Técnicos</span><b>{Number(capacity?.technicians||0)}</b></div>
   <div><span>Disponibles</span><b>{Number(capacity?.available||0).toFixed(1)} HH</b></div>
   <div><span>Meta 80%</span><b>{target.toFixed(1)} HH</b></div>
   <div><span>Asignadas</span><b>{used.toFixed(1)} HH</b></div>
   <div><span>Standby / margen</span><b>{Number(capacity?.standby||0).toFixed(1)} HH</b></div>
  </div>

  <div className="filters">
   <select value={area} onChange={e=>setArea(e.target.value)}><option value="">Todas las áreas</option>{areaOptions.map(x=><option key={x}>{x}</option>)}</select>
   <select value={criticality} onChange={e=>setCriticality(e.target.value)}><option value="">Todas las criticidades</option><option>A</option><option>B</option><option>C</option></select>
   <select value={condition} onChange={e=>setCondition(e.target.value)}><option value="">Equipo detenido u operativo</option><option>OPERANDO</option><option>EQUIPO DETENIDO</option><option>LINEA DETENIDA</option><option>AREA/PLANTA DETENIDA</option><option>SIN CLASIFICAR</option></select>
   <select value={origin} onChange={e=>setOrigin(e.target.value)}><option value="MES">Mes actual</option><option value="BACKLOG">Solo backlog</option><option value="ALL">Mes + backlog</option></select>
  </div>

  <div className="selector-flow">
   <label>1. Planeación / grupo<select value={group} onChange={e=>{setGroup(e.target.value);setChosenPlan('');setPlanText('');setEquipmentId('')}}><option value="">— Selecciona —</option>{groupOptions.map(x=><option key={x}>{x}</option>)}</select></label>
   <div className="plan-combo"><label>2. Plan de trabajo</label><input value={planText} disabled={!group} onChange={e=>{setPlanText(e.target.value);setChosenPlan('')}} placeholder="Escribe para buscar..."/>{group&&planText&&!chosenPlan&&<div className="suggestions">{planOptions.filter(p=>p.toLowerCase().includes(planText.toLowerCase())).slice(0,80).map(p=><button key={p} onClick={()=>choosePlan(p)}>{p}</button>)}</div>}</div>
   <label>3. Equipo / activo<select value={equipmentId} onChange={e=>selectEquipment(e.target.value)} disabled={!chosenPlan}><option value="">— Selecciona equipo —</option>{equipment.map(x=><option key={x.pmp_id} value={x.pmp_id}>{x.activo_codigo} — {x.activo_descripcion} — {hh(x.hh_pmp)}</option>)}</select></label>
   <button className="primary" onClick={add}>Agregar a semana</button>
  </div>

  {current&&!current.datos_completos&&<div className="learning-box">
   <div><strong>Este plan necesita completar información</strong><p>Falta: {(current.datos_faltantes||[]).join(', ')}. Lo que guardes aquí se reutilizará cuando vuelva a aparecer este plan.</p></div>
   <label>Condición<select value={learnCondition} onChange={e=>setLearnCondition(e.target.value)}><option value="">— Definir —</option>{CONDITIONS.map(x=><option key={x}>{x}</option>)}</select></label>
   <label>Número de personas<input type="number" min="1" step="1" value={learnPeople} onChange={e=>setLearnPeople(e.target.value)}/></label>
   <button onClick={completePlan} disabled={learning}>{learning?'Guardando...':'Guardar y aprender'}</button>
  </div>}

  <div className="message">{message}</div>
  <div className="table-actions"><button onClick={()=>exportCsv(selected,specialty)}>Exportar programación</button><button className="primary" onClick={save}>Guardar programación</button></div>
  <div className="table-wrap"><table><thead><tr><th>Quitar</th><th>Orden</th><th>Área</th><th>Activo</th><th>Plan</th><th>Crit.</th><th>Condición</th><th>Personas</th><th>HH</th><th>Origen</th></tr></thead><tbody>
   {!selected.length&&<tr><td colSpan="10" className="empty">Aún no has seleccionado PMP.</td></tr>}
   {selected.map(x=><tr key={x.pmp_id}><td><button onClick={()=>setSelected(p=>p.filter(i=>i.pmp_id!==x.pmp_id))}>Quitar</button></td><td>{x.numero_orden||'SIN ASIGNAR'}</td><td>{x.area_nombre}</td><td>{x.activo_codigo} — {x.activo_descripcion}</td><td>{x.plan_trabajo}</td><td>{x.criticidad}</td><td>{x.condicion}</td><td>{x.personas_usar}</td><td>{hh(x.hh_pmp)}</td><td>{x.origen}</td></tr>)}
  </tbody></table></div>
 </section>
}
