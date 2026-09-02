import {useEffect,useMemo,useState} from 'react'
import {getPendingDefinitions,savePlanDefinition} from '../api'

const SPECS=['ALL','MEC','ELE','SER','MET']
const NAMES={ALL:'Todos',MEC:'Mecánica',ELE:'Eléctrica',SER:'Servicios',MET:'Metrología'}
const CONDITIONS=[
 {value:'OPERANDO',label:'No — se puede atender con el equipo operando'},
 {value:'EQUIPO DETENIDO',label:'Sí — requiere detener el equipo'}
]

function MissingBadge({children}){
 return <span className="definition-missing">{children}</span>
}

export default function PendingDefinitions({year=2026,month=9}){
 const [rows,setRows]=useState([])
 const [specialty,setSpecialty]=useState('ALL')
 const [search,setSearch]=useState('')
 const [selectedId,setSelectedId]=useState('')
 const [people,setPeople]=useState('')
 const [condition,setCondition]=useState('')
 const [loading,setLoading]=useState(true)
 const [saving,setSaving]=useState(false)
 const [message,setMessage]=useState('')

 async function load(){
  try{
   setLoading(true)
   const data=await getPendingDefinitions(year,month)
   setRows(data)
  }catch(e){setMessage(e.message)}
  finally{setLoading(false)}
 }

 useEffect(()=>{load()},[year,month])

 const filtered=useMemo(()=>{
  const q=search.trim().toLowerCase()
  return rows.filter(r=>{
   if(specialty!=='ALL'&&r.especialidad!==specialty)return false
   if(!q)return true
   return [
    r.descripcion_grupo,r.plan_trabajo,r.especialidad,r.area_ejemplo,r.equipo_ejemplo
   ].some(v=>String(v||'').toLowerCase().includes(q))
  })
 },[rows,specialty,search])

 const selected=useMemo(
  ()=>rows.find(r=>String(r.plan_trabajo_id)===String(selectedId)),
  [rows,selectedId]
 )

 const counts=useMemo(()=>{
  const out={ALL:rows.length,MEC:0,ELE:0,SER:0,MET:0}
  rows.forEach(r=>{if(out[r.especialidad]!==undefined)out[r.especialidad]++})
  return out
 },[rows])

 const missingCounts=useMemo(()=>({
  personas:rows.filter(r=>r.falta_personas).length,
  condicion:rows.filter(r=>r.falta_condicion).length,
 }),[rows])

 function choose(row){
  setSelectedId(String(row.plan_trabajo_id))
  setPeople(row.personas_usar??'')
  setCondition(row.condicion==='SIN CLASIFICAR'?'':row.condicion||'')
  setMessage('')
 }

 async function save(){
  if(!selected)return
  if(selected.falta_personas&&(!people||Number(people)<=0))return setMessage('Debes definir el número de personas.')
  if(selected.falta_condicion&&!condition)return setMessage('Debes definir si el plan se atiende operando o con detención.')

  const payload={updated_by:'PRUEBA_WEB'}
  if(selected.falta_personas)payload.people=Number(people)
  if(selected.falta_condicion)payload.condition=condition

  try{
   setSaving(true)
   await savePlanDefinition(selected.plan_trabajo_id,payload)
   setMessage('Definición guardada. El plan ya puede pasar automáticamente a Programación semanal.')
   setSelectedId('')
   await load()
  }catch(e){setMessage(e.message)}
  finally{setSaving(false)}
 }

 return <section className="definitions-page">
  <div className="page-intro">
   <div>
    <span className="section-kicker">PREPARACIÓN DEL PMP</span>
    <h2>Pendientes por definir</h2>
    <p>Completa aquí los datos faltantes y responde si el equipo debe detenerse. Cuando el plan queda completo, pasa automáticamente a Programación semanal.</p>
   </div>
   <button className="ghost" onClick={load}>Actualizar</button>
  </div>

  <div className="definition-summary">
   <div><span>Planes pendientes</span><b>{rows.length}</b><small>del periodo {String(month).padStart(2,'0')}/{year}</small></div>
   <div><span>Sin personas</span><b>{missingCounts.personas}</b><small>requieren definir NumeroPersonas</small></div>
   <div><span>Sin condición</span><b>{missingCounts.condicion}</b><small>operando o con detención</small></div>
  </div>

  <div className="definition-toolbar">
   <div className="definition-tabs">
    {SPECS.map(s=><button key={s} className={specialty===s?'active':''} onClick={()=>setSpecialty(s)}>
     {NAMES[s]} <span>{counts[s]}</span>
    </button>)}
   </div>
   <input value={search} onChange={e=>setSearch(e.target.value)} placeholder="Buscar grupo, plan, área o equipo..."/>
  </div>

  <div className="definition-layout">
   <section className="panel definition-list-panel">
    <div className="section-head">
     <div><span className="section-kicker">LISTA DE TRABAJO</span><h2>Planes que requieren información</h2><p>{filtered.length} planes visibles con los filtros actuales.</p></div>
    </div>
    <div className="table-wrap definition-table">
     <table>
      <thead><tr><th>Esp.</th><th>DescripcionGrupo / PlanTrabajo</th><th>PMP afectados</th><th>Equipos</th><th>Falta definir</th><th></th></tr></thead>
      <tbody>
       {loading&&<tr><td colSpan="6" className="empty">Cargando pendientes...</td></tr>}
       {!loading&&!filtered.length&&<tr><td colSpan="6" className="empty">No hay planes pendientes con estos filtros.</td></tr>}
       {!loading&&filtered.map(r=><tr key={r.plan_trabajo_id} className={String(r.plan_trabajo_id)===String(selectedId)?'row-active':''}>
        <td><b>{r.especialidad}</b></td>
        <td><b>{r.descripcion_grupo||'SIN GRUPO'}</b><small className="asset-name">{r.plan_trabajo}</small><small className="asset-name">{r.area_ejemplo||'—'} · {r.equipo_ejemplo||'—'}</small></td>
        <td>{r.pmp_afectados}</td>
        <td>{r.equipos_afectados}</td>
        <td><div className="definition-badges">
         {r.falta_personas&&<MissingBadge>PERSONAS</MissingBadge>}
         {r.falta_condicion&&<MissingBadge>CONDICIÓN</MissingBadge>}
        </div></td>
        <td><button className="complete-btn" onClick={()=>choose(r)}>Definir</button></td>
       </tr>)}
      </tbody>
     </table>
    </div>
   </section>

   <aside className="panel definition-editor">
    {!selected&&<>
     <span className="section-kicker">DEFINICIÓN</span>
     <h3>Selecciona un plan</h3>
     <p>Elige un plan de la tabla para completar únicamente la información que le hace falta.</p>
     <div className="definition-help">
      <b>¿Qué pasa al guardarlo?</b>
      <span>Si todos los datos quedan completos, el plan desaparece de aquí y sus PMP pasan al grupo correcto de Programación semanal.</span>
     </div>
    </>}

    {selected&&<>
     <span className="section-kicker">{selected.especialidad} · {selected.pmp_afectados} PMP</span>
     <h3>{selected.plan_trabajo}</h3>
     <p>Completa todos los campos marcados como pendientes.</p>

     <div className="definition-fields">
      <label className={!selected.falta_personas?'field-complete':''}>
       NumeroPersonas
       <input type="number" min="1" step="1" value={people} disabled={!selected.falta_personas} onChange={e=>setPeople(e.target.value)} placeholder="Ej. 2"/>
       <small>{selected.falta_personas?'Pendiente por definir':'Ya definido en el maestro'}</small>
      </label>

      <label className={!selected.falta_condicion?'field-complete':''}>
       EquipoDetenido
       <select value={condition} disabled={!selected.falta_condicion} onChange={e=>setCondition(e.target.value)}>
        <option value="">Seleccionar SI / NO...</option>
        {CONDITIONS.map(x=><option key={x.value} value={x.value}>{x.label}</option>)}
       </select>
       <small>{selected.falta_condicion?'SI = requiere detener el equipo · NO = puede ejecutarse operando.':'Ya definido en el historial maestro'}</small>
      </label>
     </div>

     <div className="definition-destination">
      <span>Destino al quedar completo</span>
      <b>{condition==='OPERANDO'?'PMP DISPONIBLE · OPERANDO':condition==='EQUIPO DETENIDO'?'PMP DISPONIBLE · REQUIERE DETENCIÓN':'Se definirá según tu respuesta'}</b>
     </div>

     <button className="primary definition-save" onClick={save} disabled={saving}>{saving?'Guardando...':'Guardar definición'}</button>
    </>}
   </aside>
  </div>

  <div className={'message '+(message.includes('guardada')?'success':'')}>{message}</div>
 </section>
}
