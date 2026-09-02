import {useEffect,useMemo,useState} from 'react'
import {
  getHealth,getV2Dashboard,getV2PendingPlans,saveV2PlanComplement,
  getV2Technicians,saveV2TechnicianComplement,getV2Pmp,
  getV2WeekProgramming,saveV2WeekProgramming,downloadV2WeeklyReport
} from './api'
import './styles.css'

const MONTHS=['Enero','Febrero','Marzo','Abril','Mayo','Junio','Julio','Agosto','Septiembre','Octubre','Noviembre','Diciembre']
const SPEC_NAMES={MEC:'Mecánica',ELE:'Eléctrica',MET:'Metrología',SER:'Servicios'}
const SPECS=['MEC','ELE','MET','SER']

function number(v,d=0){const n=Number(v);return Number.isFinite(n)?n:d}
function fmt(v,d=1){return number(v).toLocaleString('es-CO',{minimumFractionDigits:d,maximumFractionDigits:d})}

function Badge({children,tone=''}){return <span className={'v2-badge '+tone}>{children}</span>}

function Summary({data,onGoPending}){
  const s=data?.summary||{}
  const p=data?.pending||{}
  return <div className="v2-stack">
    <section className="v2-hero">
      <div>
        <span className="v2-kicker">BASE OPERATIVA · SEPTIEMBRE 2026</span>
        <h2>Primero completamos la información. Después programamos.</h2>
        <p>La aplicación usa lo que entrega el software y te muestra únicamente los datos que todavía hacen falta para calcular y programar correctamente.</p>
      </div>
      <button className="v2-primary" onClick={onGoPending}>Completar datos pendientes</button>
    </section>

    <section className="v2-kpis">
      <div><span>Registros PMP</span><b>{number(s.registros_pmp)}</b><small>{number(s.ot_distintas)} OT distintas</small></div>
      <div><span>H-H calculables</span><b>{fmt(s.hh_calculables,1)}</b><small>con datos disponibles hoy</small></div>
      <div><span>H-H técnicos mes</span><b>{fmt(s.hh_tecnicos_mes,1)}</b><small>antes del 80 / 20</small></div>
      <div className="warn"><span>Planes pendientes</span><b>{number(p.planes_pendientes)}</b><small>usados en el PMP del mes</small></div>
      <div className="warn"><span>Sin Nº personas</span><b>{number(p.planes_sin_personas)}</b><small>planes diferentes</small></div>
      <div className={number(s.tecnicos_sin_especialidad)?'warn':'ok'}><span>Técnicos sin especialidad</span><b>{number(s.tecnicos_sin_especialidad)}</b><small>requieren completar dato</small></div>
    </section>

    <section className="v2-panel">
      <div className="v2-section-head">
        <div><span className="v2-kicker">POR ESPECIALIDAD</span><h3>Carga preventiva del mes</h3></div>
      </div>
      <div className="v2-spec-grid">
        {(data?.specialties||[]).map(x=><div key={x.especialidad} className="v2-spec-card">
          <div><Badge>{x.especialidad}</Badge><b>{SPEC_NAMES[x.especialidad]||x.especialidad}</b></div>
          <strong>{number(x.ot_distintas)}</strong>
          <span>OT distintas</span>
          <small>{fmt(x.hh_calculables,1)} H-H calculables</small>
        </div>)}
      </div>
    </section>

    <section className="v2-panel">
      <div className="v2-section-head">
        <div><span className="v2-kicker">CALIDAD DE DATOS</span><h3>Qué falta antes de programar</h3></div>
      </div>
      <div className="v2-quality-grid">
        <div className="good"><b>{number(s.registros_listos)}</b><span>registros del PMP listos</span></div>
        <div><b>{number(s.registros_sin_personas)}</b><span>registros afectados por Nº personas</span></div>
        <div><b>{number(s.registros_sin_tiempo_parada)}</b><span>registros afectados por TiempoParada</span></div>
        <div><b>{number(s.registros_sin_plan_maestro)}</b><span>registros cuyo plan no está en el maestro</span></div>
      </div>
    </section>
  </div>
}

function PendingPlans({year,month,onChanged}){
  const [data,setData]=useState(null)
  const [spec,setSpec]=useState('')
  const [search,setSearch]=useState('')
  const [draft,setDraft]=useState({})
  const [saving,setSaving]=useState(null)
  const [error,setError]=useState('')

  const load=()=>getV2PendingPlans(year,month,spec).then(setData).catch(e=>setError(e.message))
  useEffect(()=>{load()},[year,month,spec])

  const rows=useMemo(()=>{
    const q=search.trim().toLowerCase()
    if(!q)return data?.plans||[]
    return (data?.plans||[]).filter(x=>
      String(x.descripcion_grupo||'').toLowerCase().includes(q)||
      String(x.plan_trabajo||'').toLowerCase().includes(q)
    )
  },[data,search])

  function value(id,field,current){
    return draft[id]?.[field] ?? (current??'')
  }
  function setValue(id,field,v){setDraft(d=>({...d,[id]:{...(d[id]||{}),[field]:v}}))}

  async function save(row){
    const peopleRaw=value(row.id,'people',row.numero_personas_app)
    const stopRaw=value(row.id,'stop',row.tiempo_parada_app_min)
    const people=peopleRaw===''?null:Number(peopleRaw)
    const stop=stopRaw===''?null:Number(stopRaw)
    try{
      setSaving(row.id);setError('')
      await saveV2PlanComplement(row.id,{people:Number.isFinite(people)?people:null,stop_minutes:Number.isFinite(stop)?stop:null})
      setDraft(d=>{const n={...d};delete n[row.id];return n})
      await load()
      onChanged?.()
    }catch(e){setError(e.message)}
    finally{setSaving(null)}
  }

  return <div className="v2-stack">
    <section className="v2-panel">
      <div className="v2-section-head">
        <div><span className="v2-kicker">APRENDIZAJE DE LA APP</span><h3>Datos que faltan en los planes usados este mes</h3><p>Si el software ya trae el dato, se usa automáticamente. Si viene vacío, puedes completarlo aquí.</p></div>
        <Badge tone="warn">{data?.plans?.length||0} planes pendientes</Badge>
      </div>

      <div className="v2-toolbar">
        <input placeholder="Buscar grupo o plan de trabajo..." value={search} onChange={e=>setSearch(e.target.value)}/>
        <select value={spec} onChange={e=>setSpec(e.target.value)}>
          <option value="">Todas las especialidades</option>
          {SPECS.map(s=><option key={s} value={s}>{SPEC_NAMES[s]}</option>)}
        </select>
      </div>
      {error&&<div className="v2-error">{error}</div>}

      <div className="v2-table-wrap">
        <table>
          <thead><tr><th>Grupo</th><th>Plan de trabajo</th><th>Esp.</th><th>PMP mes</th><th>Nº personas</th><th>Tiempo parada</th><th>Acción</th></tr></thead>
          <tbody>
          {rows.map(row=>{
            const peopleSoftware=row.numero_personas_software
            const stopSoftware=row.tiempo_parada_software
            return <tr key={row.id}>
              <td><b>{row.descripcion_grupo||row.grupo}</b></td>
              <td><span className="v2-plan">{row.plan_trabajo}</span><small>{row.descripcion_plan_trabajo}</small></td>
              <td><Badge>{row.especialidad||'—'}</Badge></td>
              <td><b>{number(row.registros_pmp)}</b><small>{number(row.ot_distintas)} OT</small></td>
              <td>
                {peopleSoftware!=null
                  ? <div><b>{peopleSoftware}</b><small>Software</small></div>
                  : <label className="v2-inline-field"><input type="number" min="1" step="1" placeholder="Ej. 2" value={value(row.id,'people',row.numero_personas_app)} onChange={e=>setValue(row.id,'people',e.target.value)}/><small>Completar en app</small></label>}
              </td>
              <td>
                {stopSoftware!=null
                  ? <div><b>{stopSoftware} min</b><small>{number(stopSoftware)>0?'Equipo detenido':'Equipo operando'} · Software</small></div>
                  : <label className="v2-inline-field"><input type="number" min="0" step="1" placeholder="0 = operando" value={value(row.id,'stop',row.tiempo_parada_app_min)} onChange={e=>setValue(row.id,'stop',e.target.value)}/><small>0 = no requiere parada</small></label>}
              </td>
              <td><button className="v2-save" disabled={saving===row.id} onClick={()=>save(row)}>{saving===row.id?'Guardando...':'Guardar'}</button></td>
            </tr>
          })}
          {!rows.length&&<tr><td colSpan="7" className="v2-empty">No hay planes pendientes con este filtro.</td></tr>}
          </tbody>
        </table>
      </div>
    </section>

    {!!data?.missing_master?.length&&<section className="v2-panel v2-alert-panel">
      <div className="v2-section-head"><div><span className="v2-kicker">REVISAR EN SOFTWARE</span><h3>Planes usados por el PMP que no están en Plan de Trabajo</h3></div></div>
      <div className="v2-missing-list">
        {data.missing_master.map(x=><div key={x.plan_clave_software}><b>{x.plan_clave_software}</b><span>{number(x.registros_pmp)} registros · {number(x.ot_distintas)} OT</span></div>)}
      </div>
    </section>}
  </div>
}

function Technicians({year,month,onChanged}){
  const [data,setData]=useState(null)
  const [draft,setDraft]=useState({})
  const [saving,setSaving]=useState(null)
  const [error,setError]=useState('')
  const load=()=>getV2Technicians(year,month).then(setData).catch(e=>setError(e.message))
  useEffect(()=>{load()},[year,month])

  async function save(t){
    const specialty=draft[t.id]
    if(!specialty)return
    try{
      setSaving(t.id);setError('')
      await saveV2TechnicianComplement(t.id,specialty)
      setDraft(d=>({...d,[t.id]:''}))
      await load();onChanged?.()
    }catch(e){setError(e.message)}finally{setSaving(null)}
  }

  return <section className="v2-panel">
    <div className="v2-section-head">
      <div><span className="v2-kicker">PERSONAL</span><h3>Programación mensual de técnicos</h3><p>La especialidad del software tiene prioridad. Solo completamos los técnicos que vienen sin ella.</p></div>
      <Badge tone={data?.technicians?.some(t=>!t.especialidad_efectiva)?'warn':'ok'}>{data?.technicians?.filter(t=>!t.especialidad_efectiva).length||0} pendientes</Badge>
    </div>
    {error&&<div className="v2-error">{error}</div>}
    <div className="v2-table-wrap">
      <table>
        <thead><tr><th>Técnico</th><th>Especialidad</th><th>Fuente</th><th>H-H mes</th><th>Acción</th></tr></thead>
        <tbody>
        {(data?.technicians||[]).map(t=><tr key={t.id}>
          <td><b>{t.nombre}</b><small>{t.identificacion||''}</small></td>
          <td>{t.especialidad_efectiva?<Badge>{SPEC_NAMES[t.especialidad_efectiva]||t.especialidad_efectiva}</Badge>:
            <select value={draft[t.id]||''} onChange={e=>setDraft(d=>({...d,[t.id]:e.target.value}))}>
              <option value="">Seleccionar...</option>{SPECS.map(s=><option key={s} value={s}>{SPEC_NAMES[s]}</option>)}
            </select>}</td>
          <td><small>{t.especialidad_software?'SOFTWARE':t.especialidad_app?'APP':'PENDIENTE'}</small></td>
          <td><b>{fmt(t.hh_mes,1)}</b></td>
          <td>{!t.especialidad_efectiva?<button className="v2-save" disabled={!draft[t.id]||saving===t.id} onClick={()=>save(t)}>{saving===t.id?'Guardando...':'Guardar'}</button>:<Badge tone="ok">Completo</Badge>}</td>
        </tr>)}
        </tbody>
      </table>
    </div>
  </section>
}


function monthWeeks(year,month){
  const days=new Date(year,month,0).getDate()
  const weeks=[]
  for(let start=1;start<=days;start+=7){
    const end=Math.min(start+6,days)
    const from=`${year}-${String(month).padStart(2,'0')}-${String(start).padStart(2,'0')}`
    const to=`${year}-${String(month).padStart(2,'0')}-${String(end).padStart(2,'0')}`
    weeks.push({from,to,label:`${start}–${end} ${MONTHS[month-1]}`})
  }
  return weeks
}

function WeeklyProgramming({year,month,dashboard}){
  const weeks=useMemo(()=>monthWeeks(year,month),[year,month])
  const [weekIndex,setWeekIndex]=useState(0)
  const [specialty,setSpecialty]=useState('MEC')
  const [data,setData]=useState(null)
  const [selected,setSelected]=useState(new Set())
  const [search,setSearch]=useState('')
  const [area,setArea]=useState('')
  const [loading,setLoading]=useState(false)
  const [saving,setSaving]=useState(false)
  const [error,setError]=useState('')
  const [message,setMessage]=useState('')
  const [dirty,setDirty]=useState(false)
  const [programmingId,setProgrammingId]=useState(null)

  const week=weeks[Math.min(weekIndex,weeks.length-1)]||weeks[0]

  async function load(){
    if(!week)return
    try{
      setLoading(true);setError('');setMessage('')
      const r=await getV2WeekProgramming(week.from,week.to,specialty)
      setData(r)
      setSelected(new Set((r.selected_ids||[]).map(Number)))
      setProgrammingId(r.programming?.id||null)
      setDirty(false)
    }catch(e){setError(e.message)}
    finally{setLoading(false)}
  }

  useEffect(()=>{setWeekIndex(0)},[month])
  useEffect(()=>{load()},[week?.from,week?.to,specialty])

  const allRows=useMemo(()=>[...(data?.operating||[]),...(data?.stopped||[])],[data])
  const rowMap=useMemo(()=>new Map(allRows.map(r=>[Number(r.orden_mantenimiento_id),r])),[allRows])
  const selectedHH=useMemo(()=>[...selected].reduce((sum,id)=>sum+number(rowMap.get(id)?.hh),0),[selected,rowMap])
  const target=number(data?.capacity?.target)
  const available=number(data?.capacity?.available)
  const reserve=number(data?.capacity?.reserve)
  const remaining=Math.max(0,target-selectedHH)
  const progress=target>0?Math.min(100,selectedHH/target*100):0

  function toggle(row){
    const id=Number(row.orden_mantenimiento_id)
    setError('');setMessage('')
    setSelected(prev=>{
      const next=new Set(prev)
      if(next.has(id)){
        next.delete(id)
        setDirty(true)
        return next
      }
      const nextHH=selectedHH+number(row.hh)
      if(nextHH>target+.001){
        setError(`No se puede seleccionar: llegarías a ${fmt(nextHH,1)} H-H y la meta del 80% es ${fmt(target,1)} H-H.`)
        return prev
      }
      next.add(id)
      setDirty(true)
      return next
    })
  }

  function filtered(rows){
    const q=search.trim().toLowerCase()
    return rows.filter(r=>{
      if(area&&r.area_codigo!==area)return false
      if(!q)return true
      return String(r.numero_ot||'').toLowerCase().includes(q)||
        String(r.activo_codigo||'').toLowerCase().includes(q)||
        String(r.activo_descripcion||'').toLowerCase().includes(q)||
        String(r.plan_trabajo||'').toLowerCase().includes(q)
    })
  }

  async function save(){
    if(!selected.size){setError('Selecciona al menos una orden para guardar la semana.');return}
    try{
      setSaving(true);setError('');setMessage('')
      const r=await saveV2WeekProgramming({
        date_from:week.from,date_to:week.to,specialty,
        order_ids:[...selected],
        created_by:'CARLOS ANDRÉS RECIO MUÑOZ'
      })
      setProgrammingId(r.programming_id)
      setDirty(false)
      setMessage(`Programación guardada: ${fmt(r.hh_programmed,1)} H-H de ${fmt(r.hh_target,1)} H-H objetivo.`)
      await load()
    }catch(e){setError(e.message)}
    finally{setSaving(false)}
  }

  async function report(format){
    if(!programmingId||dirty){
      setError('Guarda la programación antes de generar el reporte.')
      return
    }
    try{setError('');await downloadV2WeeklyReport(programmingId,format)}
    catch(e){setError(e.message)}
  }

  function ActivityTable({rows,title,stopped}){
    const visible=filtered(rows)
    return <section className={'v2-activity-section '+(stopped?'stopped':'operating')}>
      <div className="v2-activity-head">
        <div>
          <span className="v2-kicker">{stopped?'PARADA REQUERIDA':'EQUIPO OPERANDO'}</span>
          <h3>{title}</h3>
          <p>{stopped?'Actividades que necesitan el equipo detenido.':'Actividades que pueden ejecutarse con el equipo funcionando.'}</p>
        </div>
        <Badge tone={stopped?'stop':'ok'}>{visible.length} disponibles</Badge>
      </div>
      <div className="v2-table-wrap v2-program-table">
        <table>
          <thead><tr><th>Semana</th><th>OT</th><th>Área</th><th>Equipo</th><th>Plan de trabajo</th><th>Personas</th><th>Tiempo</th><th>H-H</th><th>Seleccionar</th></tr></thead>
          <tbody>
          {visible.map(r=>{
            const id=Number(r.orden_mantenimiento_id)
            const isSelected=selected.has(id)
            return <tr key={id} className={isSelected?'v2-selected-row':''}>
              <td>{isSelected?<Badge tone="ok">Esta semana</Badge>:<span className="v2-muted">Disponible</span>}</td>
              <td><b>{r.numero_ot||'SIN ASIGNAR'}</b></td>
              <td><Badge>{r.area_codigo||'—'}</Badge><small>{r.area_nombre||''}</small></td>
              <td><b>{r.activo_codigo}</b><small>{r.activo_descripcion}</small></td>
              <td><span className="v2-plan">{r.plan_trabajo}</span><small>{r.descripcion_grupo||''}</small></td>
              <td><b>{r.numero_personas_efectivo}</b></td>
              <td>{fmt(r.tiempo_min,0)} min</td>
              <td><b>{fmt(r.hh,1)}</b></td>
              <td><button className={isSelected?'v2-unselect':'v2-select'} onClick={()=>toggle(r)}>{isSelected?'Quitar':'Seleccionar'}</button></td>
            </tr>
          })}
          {!visible.length&&<tr><td colSpan="9" className="v2-empty">No hay actividades listas con estos filtros.</td></tr>}
          </tbody>
        </table>
      </div>
    </section>
  }

  return <div className="v2-stack">
    <section className="v2-panel">
      <div className="v2-section-head">
        <div><span className="v2-kicker">PROGRAMACIÓN SEMANAL</span><h3>Selecciona semana y especialidad</h3><p>Solo aparecen actividades con PlanTrabajo, Nº personas, TiempoParada y tiempo de ejecución listos.</p></div>
        <Badge>{loading?'Calculando...':`${data?.capacity?.technicians||0} técnicos`}</Badge>
      </div>

      <div className="v2-week-selector">
        <div className="v2-week-buttons">
          {weeks.map((w,i)=><button key={w.from} className={weekIndex===i?'active':''} onClick={()=>setWeekIndex(i)}><b>Semana {i+1}</b><span>{w.label}</span></button>)}
        </div>
        <div className="v2-specialty-buttons">
          {SPECS.map(s=><button key={s} className={specialty===s?'active':''} onClick={()=>setSpecialty(s)}><b>{s}</b><span>{SPEC_NAMES[s]}</span></button>)}
        </div>
      </div>
    </section>

    <section className="v2-capacity-panel">
      <div className="v2-capacity-cards">
        <div><span>H-H disponibles</span><b>{fmt(available,1)}</b><small>100% de capacidad</small></div>
        <div className="target"><span>Meta programable</span><b>{fmt(target,1)}</b><small>80% que debes programar</small></div>
        <div><span>Reserva</span><b>{fmt(reserve,1)}</b><small>20% correctivos, traslados e imprevistos</small></div>
        <div className="selected"><span>H-H seleccionadas</span><b>{fmt(selectedHH,1)}</b><small>{selected.size} órdenes / actividades</small></div>
        <div className={remaining<=.01?'complete':'remaining'}><span>{remaining<=.01?'Meta alcanzada':'Faltan para meta'}</span><b>{fmt(remaining,1)}</b><small>H-H</small></div>
      </div>
      <div className="v2-progress-block">
        <div className="v2-progress-copy"><span>Avance hacia el 80%</span><b>{fmt(progress,1)}%</b></div>
        <div className="v2-progress-track"><i style={{width:`${progress}%`}}/></div>
        <div className="v2-progress-foot"><span>{fmt(selectedHH,1)} H-H programadas</span><span>Objetivo {fmt(target,1)} H-H</span></div>
      </div>
      {available===0&&<div className="v2-warning">Esta especialidad no tiene disponibilidad cargada para esta semana. Revisa la programación de técnicos.</div>}
      {error&&<div className="v2-error">{error}</div>}
      {message&&<div className="v2-success">{message}</div>}
    </section>

    <section className="v2-panel">
      <div className="v2-program-toolbar">
        <div><span className="v2-kicker">FILTROS</span><h3>Actividades listas para seleccionar</h3></div>
        <div>
          <select value={area} onChange={e=>setArea(e.target.value)}>
            <option value="">Todas las áreas</option>
            {(dashboard?.areas||[]).map(a=><option key={a.codigo} value={a.codigo}>{a.codigo} · {a.nombre||a.codigo}</option>)}
          </select>
          <input placeholder="Buscar OT, equipo o plan..." value={search} onChange={e=>setSearch(e.target.value)}/>
        </div>
      </div>

      <ActivityTable rows={data?.operating||[]} title="Se puede ejecutar con el equipo funcionando" stopped={false}/>
      <ActivityTable rows={data?.stopped||[]} title="Requiere equipo detenido" stopped={true}/>
    </section>

    <section className="v2-save-program">
      <div>
        <span className="v2-kicker">CIERRE DE PROGRAMACIÓN</span>
        <h3>{dirty?'Hay cambios sin guardar':programmingId?'Semana guardada':'Guarda la selección de esta semana'}</h3>
        <p>El reporte mostrará la capacidad, la meta del 80%, la reserva del 20% y las órdenes que el ingeniero debe responder.</p>
      </div>
      <div className="v2-report-actions">
        <button className="v2-primary" disabled={saving||!selected.size} onClick={save}>{saving?'Guardando...':'Guardar programación'}</button>
        <button disabled={!programmingId||dirty} onClick={()=>report('xlsx')}>Reporte Excel</button>
        <button disabled={!programmingId||dirty} onClick={()=>report('pdf')}>Reporte PDF</button>
      </div>
    </section>
  </div>
}

function Pmp({year,month,dashboard}){
  const [filters,setFilters]=useState({specialty:'',area:'',search:''})
  const [data,setData]=useState(null)
  const [loading,setLoading]=useState(false)
  const [error,setError]=useState('')
  const load=async()=>{
    try{setLoading(true);setError('');setData(await getV2Pmp({year,month,...filters,limit:400}))}
    catch(e){setError(e.message)}finally{setLoading(false)}
  }
  useEffect(()=>{load()},[year,month])

  return <section className="v2-panel">
    <div className="v2-section-head">
      <div><span className="v2-kicker">PMP DEL MES</span><h3>Órdenes y planes exportados por el software</h3><p>El día de ejecución del software no gobierna nuestra programación interna; aquí usamos el mes como cartera de trabajo.</p></div>
      <Badge>{loading?'Consultando...':(data?.rows?.length||0)+' registros visibles'}</Badge>
    </div>

    <div className="v2-toolbar v2-toolbar-4">
      <select value={filters.specialty} onChange={e=>setFilters(f=>({...f,specialty:e.target.value}))}><option value="">Todas las especialidades</option>{SPECS.map(s=><option key={s} value={s}>{SPEC_NAMES[s]}</option>)}</select>
      <select value={filters.area} onChange={e=>setFilters(f=>({...f,area:e.target.value}))}><option value="">Todas las áreas</option>{(dashboard?.areas||[]).map(a=><option key={a.codigo} value={a.codigo}>{a.codigo} · {a.nombre||'Sin nombre raíz'}</option>)}</select>
      <input placeholder="OT, equipo o plan..." value={filters.search} onChange={e=>setFilters(f=>({...f,search:e.target.value}))}/>
      <button className="v2-primary" onClick={load}>Aplicar filtros</button>
    </div>
    {error&&<div className="v2-error">{error}</div>}

    <div className="v2-table-wrap v2-pmp-table">
      <table>
        <thead><tr><th>OT</th><th>Área</th><th>Equipo</th><th>Plan</th><th>Esp.</th><th>Personas</th><th>Parada</th><th>Tiempo</th><th>H-H</th><th>Dato</th></tr></thead>
        <tbody>
        {(data?.rows||[]).map(r=><tr key={r.id}>
          <td><b>{r.numero_ot||'SIN ASIGNAR'}</b></td>
          <td><Badge>{r.area_codigo||'—'}</Badge><small>{r.area_nombre||''}</small></td>
          <td><b>{r.activo_codigo}</b><small>{r.activo_descripcion}</small></td>
          <td><span className="v2-plan">{r.plan_trabajo||r.plan_clave_software}</span><small>{r.descripcion_grupo||''}</small></td>
          <td><Badge>{r.especialidad||'—'}</Badge></td>
          <td>{r.numero_personas_efectivo??'—'}</td>
          <td>{r.requiere_parada==null?<Badge tone="warn">Falta</Badge>:r.requiere_parada?<Badge tone="stop">Sí</Badge>:<Badge tone="ok">No</Badge>}</td>
          <td>{r.tiempo_min!=null?fmt(r.tiempo_min,0)+' min':'—'}</td>
          <td><b>{r.hh!=null?fmt(r.hh,1):'—'}</b></td>
          <td><Badge tone={r.calidad_dato==='LISTO'?'ok':'warn'}>{r.calidad_dato}</Badge></td>
        </tr>)}
        {!data?.rows?.length&&!loading&&<tr><td colSpan="10" className="v2-empty">No hay registros para estos filtros.</td></tr>}
        </tbody>
      </table>
    </div>
  </section>
}

export default function App(){
  const [view,setView]=useState('summary')
  const [year]=useState(2026)
  const [month,setMonth]=useState(9)
  const [dashboard,setDashboard]=useState(null)
  const [health,setHealth]=useState('checking')
  const [error,setError]=useState('')

  const refresh=()=>{
    getV2Dashboard(year,month).then(setDashboard).catch(e=>setError(e.message))
  }
  useEffect(()=>{
    getHealth().then(()=>setHealth('ok')).catch(()=>setHealth('error'))
  },[])
  useEffect(()=>{refresh()},[year,month])

  const titles={
    summary:['Resumen mensual','Estado de la información antes de empezar a programar.'],
    pending:['Completar datos','Solo aparecen datos que hacen falta en los planes usados este mes.'],
    programming:['Programación semanal','Selecciona actividades por especialidad hasta completar la meta programable del 80%.'],
    pmp:['PMP del mes','Cartera preventiva exportada desde el software de mantenimiento.'],
    technicians:['Técnicos','Turnos, disponibilidad y especialidades del personal.']
  }

  return <div className="v2-shell">
    <aside className="v2-sidebar">
      <div className="v2-brand"><div>CEK</div><span><b>PROGRAMACIÓN</b><small>TEAM FOOD · Barranquilla</small></span></div>
      <nav>
        <button className={view==='summary'?'active':''} onClick={()=>setView('summary')}><span>01</span>Resumen</button>
        <button className={view==='pending'?'active':''} onClick={()=>setView('pending')}><span>02</span>Completar datos{number(dashboard?.pending?.planes_pendientes)>0&&<i>{dashboard.pending.planes_pendientes}</i>}</button>
        <button className={view==='programming'?'active':''} onClick={()=>setView('programming')}><span>03</span>Programación semanal</button>
        <button className={view==='pmp'?'active':''} onClick={()=>setView('pmp')}><span>04</span>PMP del mes</button>
        <button className={view==='technicians'?'active':''} onClick={()=>setView('technicians')}><span>05</span>Técnicos{number(dashboard?.summary?.tecnicos_sin_especialidad)>0&&<i>{dashboard.summary.tecnicos_sin_especialidad}</i>}</button>
      </nav>
      <div className="v2-side-note"><small>Fuente principal</small><b>Software de mantenimiento</b><span>La app complementa únicamente los datos faltantes.</span></div>
      <div className="v2-profile"><span>CARLOS ANDRÉS RECIO MUÑOZ</span><small>C.E.K GLOBAL INSPECTION</small></div>
    </aside>

    <main className="v2-main">
      <header className="v2-topbar">
        <div><span className="v2-kicker">PLANTA BARRANQUILLA</span><h1>{titles[view][0]}</h1><p>{titles[view][1]}</p></div>
        <div className="v2-top-actions">
          <label>Periodo<select value={month} onChange={e=>setMonth(Number(e.target.value))}>{MONTHS.map((m,i)=><option key={m} value={i+1}>{m} 2026</option>)}</select></label>
          <div className={'v2-health '+health}><i/>{health==='ok'?'Base conectada':health==='error'?'Sin conexión':'Conectando...'}</div>
        </div>
      </header>

      {error&&<div className="v2-error">{error}</div>}
      {view==='summary'&&<Summary data={dashboard} onGoPending={()=>setView('pending')}/>}
      {view==='pending'&&<PendingPlans year={year} month={month} onChanged={refresh}/>}
      {view==='programming'&&<WeeklyProgramming year={year} month={month} dashboard={dashboard}/>}
      {view==='pmp'&&<Pmp year={year} month={month} dashboard={dashboard}/>}
      {view==='technicians'&&<Technicians year={year} month={month} onChanged={refresh}/>}
    </main>
  </div>
}
