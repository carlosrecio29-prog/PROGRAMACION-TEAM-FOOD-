import {useEffect,useMemo,useRef,useState} from 'react'
import {monthWeeks,initialWeekIndex} from '../features/planning/monthWeeks.js'
import {getV2WeekProgramming,saveV2WeekProgramming,downloadV2WeeklyReport} from '../api'
import {emptyFilters,matchesFilters,updateGroupFilters} from '../features/planning/weeklyProgrammingFilters'
import {toggleWeeklySelection} from '../features/planning/weeklyProgrammingSelection'
import Badge from '../shared/Badge'
import alianzaTeamLogo from '../assets/alianzaTeamLogoData.js'

const SPEC_NAMES={MEC:'Mecánica',ELE:'Eléctrica',MET:'Metrología',SER:'Servicios'}
const SPECS=['MEC','ELE','MET','SER']

function number(value,fallback=0){const parsed=Number(value);return Number.isFinite(parsed)?parsed:fallback}
function fmt(value,decimals=1){return number(value).toLocaleString('es-CO',{minimumFractionDigits:decimals,maximumFractionDigits:decimals})}
function round2(value){return Math.round((number(value)+Number.EPSILON)*100)/100}

function ActivityGroup({kind,rows,dashboard,editing,selected,filters,onFiltersChange,onToggle}){
  const config={
    operating:{title:'Equipo operando',description:'Actividades que no requieren detener el equipo.',tone:'ok'},
    stopped:{title:'Equipo detenido',description:'Actividades que requieren coordinación de parada.',tone:'stop'},
    backlog:{title:'Backlog',description:'Pendientes provenientes de programaciones anteriores.',tone:'backlog'}
  }[kind]
  const availableRows=rows.filter(row=>!selected.has(Number(row.orden_mantenimiento_id)))
  const visible=matchesFilters(availableRows,filters)
  const visibleHH=visible.reduce((sum,row)=>sum+number(row.hh),0)
  return <section className={'v2-activity-section tf-program-table-section '+kind} aria-label={config.title}>
    <div className="tf-program-table-head">
      <div><h3>{config.title}</h3><p>{config.description}</p></div>
      <div className={'tf-table-mini-kpi '+config.tone}>
        <span><b>{visible.length}</b> OT</span>
        <span><b>{fmt(visibleHH,1)}</b> H-H</span>
      </div>
    </div>
    <div className="tf-table-filterbar" aria-label={'Filtros de '+config.title}>
      <label><span>Área</span><select aria-label={'Área en '+config.title} value={filters.area} onChange={event=>onFiltersChange({area:event.target.value})}><option value="">Todas</option>{(dashboard?.areas||[]).map(area=><option key={area.codigo} value={area.codigo}>{area.codigo} · {area.nombre||area.codigo}</option>)}</select></label>
      <label className="search"><span>Buscar</span><input aria-label={'Buscar en '+config.title} placeholder="OT, equipo o plan..." value={filters.search} onChange={event=>onFiltersChange({search:event.target.value})}/></label>
    </div>
    <div className="v2-table-wrap v2-program-table"><table><thead><tr>{kind==='backlog'&&<th>Origen</th>}<th>OT</th><th>Área</th><th>Equipo</th><th>Plan de trabajo</th><th>Personas</th><th>Tiempo</th><th>H-H</th><th>Acción</th></tr></thead><tbody>
      {visible.map(row=>{
        const id=Number(row.orden_mantenimiento_id)
        return <tr key={id}>
          {kind==='backlog'&&<td><div className="v2-backlog-origin"><b>Backlog</b><small>{row.semana_origen_inicio||'Semana anterior'} {row.semana_origen_fin?'→ '+row.semana_origen_fin:''}</small></div></td>}
          <td><b>{row.numero_ot||'SIN ASIGNAR'}</b></td>
          <td><Badge>{row.area_codigo||'—'}</Badge><small>{row.area_nombre||''}</small></td>
          <td><b>{row.activo_codigo}</b><small>{row.activo_descripcion}</small></td>
          <td><span className="v2-plan">{row.plan_trabajo}</span><small>{row.descripcion_grupo||''}</small></td>
          <td><b>{row.numero_personas_efectivo}</b></td>
          <td>{fmt(row.tiempo_min,0)} min</td>
          <td><b>{fmt(row.hh,1)}</b></td>
          <td>{editing
            ? <button type="button" className="v2-select" onClick={()=>onToggle(row)}>Agregar</button>
            : <span className="tf-readonly-dash">—</span>}
          </td>
        </tr>
      })}
      {!visible.length&&<tr><td colSpan={kind==='backlog'?9:8} className="v2-empty">No hay actividades con estos filtros.</td></tr>}
    </tbody></table></div>
  </section>
}

function SelectionSummary({rows,editing,onToggle,dashboard}){
  const [area,setArea]=useState('')
  const [search,setSearch]=useState('')
  const term=search.trim().toLowerCase()
  const visibleRows=rows.filter(row=>{
    if(area&&String(row.area_codigo||'')!==area)return false
    if(!term)return true
    return [
      row.numero_ot,row.area_codigo,row.area_nombre,row.activo_codigo,row.activo_descripcion,
      row.plan_trabajo,row.descripcion_grupo,row.origen
    ].some(value=>String(value||'').toLowerCase().includes(term))
  })
  const operatingHH=rows.filter(row=>row.requiere_parada===false).reduce((sum,row)=>sum+number(row.hh),0)
  const stoppedHH=rows.filter(row=>row.requiere_parada===true).reduce((sum,row)=>sum+number(row.hh),0)
  const totalHH=operatingHH+stoppedHH
  return <section className={'v2-selected-section '+(!editing?'readonly':'')}>
    <div className="v2-selected-head">
      <div>
        <span className="v2-kicker">{editing?'PROGRAMACIÓN EN EDICIÓN':'PROGRAMACIÓN GUARDADA'}</span>
        <h3>{editing?'Selección actual':'Programación actual de la semana'}</h3>
        <p>{editing?'Aquí ves únicamente las actividades que estás programando.':'Estas son las actividades guardadas para la semana.'}</p>
      </div>
      <div className="tf-programmed-mini-wrap">
        <div className="tf-table-mini-kpi programmed">
          <span><b>{rows.length}</b> OT</span>
          <span><b>{fmt(totalHH,1)}</b> H-H</span>
        </div>
        <small>{fmt(operatingHH,1)} H-H operando · {fmt(stoppedHH,1)} H-H detenido</small>
      </div>
    </div>
    <div className="tf-table-filterbar tf-selected-filterbar">
      <label><span>Área</span><select value={area} onChange={event=>setArea(event.target.value)}><option value="">Todas</option>{(dashboard?.areas||[]).map(item=><option key={item.codigo} value={item.codigo}>{item.codigo} · {item.nombre||item.codigo}</option>)}</select></label>
      <label className="search"><span>Buscar</span><input placeholder="OT, equipo o plan..." value={search} onChange={event=>setSearch(event.target.value)}/></label>
      <small>{visibleRows.length} de {rows.length}</small>
    </div>
    <div className="v2-table-wrap v2-selected-table"><table>
      <thead><tr><th>Condición</th><th>Origen</th><th>OT</th><th>Área</th><th>Equipo</th><th>Plan de trabajo</th><th>Personas</th><th>Tiempo</th><th>H-H</th>{editing&&<th>Acción</th>}</tr></thead>
      <tbody>
        {visibleRows.map(row=><tr key={row.orden_mantenimiento_id}>
          <td>{row.requiere_parada?<Badge tone="stop">Equipo detenido</Badge>:<Badge tone="ok">Equipo funcionando</Badge>}</td>
          <td>{row.origen==='BACKLOG'||row.origen_backlog?<Badge tone="backlog">BACKLOG</Badge>:<Badge>PMP DEL MES</Badge>}</td>
          <td><b>{row.numero_ot||'SIN ASIGNAR'}</b></td>
          <td><Badge>{row.area_codigo||'—'}</Badge><small>{row.area_nombre||''}</small></td>
          <td><b>{row.activo_codigo}</b><small>{row.activo_descripcion}</small></td>
          <td><span className="v2-plan">{row.plan_trabajo}</span><small>{row.descripcion_grupo||''}</small></td>
          <td><b>{row.numero_personas_efectivo}</b></td>
          <td>{fmt(row.tiempo_min,0)} min</td>
          <td><b>{fmt(row.hh,1)}</b></td>
          {editing&&<td><button type="button" className="v2-unselect" onClick={()=>onToggle(row)}>Quitar</button></td>}
        </tr>)}
        {!visibleRows.length&&<tr><td colSpan={editing?10:9} className="v2-empty">{rows.length?'No hay actividades con estos filtros.':'Todavía no has seleccionado actividades para esta semana.'}</td></tr>}
      </tbody>
    </table></div>
  </section>
}

export default function WeeklyProgramming({year,month,dashboard}){
  const weeks=useMemo(()=>monthWeeks(year,month),[year,month])
  const [weekIndex,setWeekIndex]=useState(()=>initialWeekIndex(weeks));const [specialty,setSpecialty]=useState('MEC');const [data,setData]=useState(null);const [selected,setSelected]=useState(new Set());const [filters,setFilters]=useState(emptyFilters);const [loading,setLoading]=useState(false);const [saving,setSaving]=useState(false);const [error,setError]=useState('');const [message,setMessage]=useState('');const [dirty,setDirty]=useState(false);const [programmingId,setProgrammingId]=useState(null);const [editing,setEditing]=useState(true)
  const loadSequence=useRef(0)
  const week=weeks[Math.min(weekIndex,weeks.length-1)]||weeks[0]
  async function load(){
    if(!week)return
    const sequence=++loadSequence.current
    const requestWeek={from:week.from,to:week.to}
    const requestSpecialty=specialty
    try{
      setLoading(true)
      setError('')
      const result=await getV2WeekProgramming(requestWeek.from,requestWeek.to,requestSpecialty)
      if(sequence!==loadSequence.current)return
      setData(result)
      setSelected(new Set((result.selected_ids||[]).map(Number)))
      setProgrammingId(result.programming?.id||null)
      setEditing(!result.programming)
      setDirty(false)
    }catch(cause){
      if(sequence===loadSequence.current)setError(cause.message)
    }finally{
      if(sequence===loadSequence.current)setLoading(false)
    }
  }
  useEffect(()=>{setWeekIndex(initialWeekIndex(weeks))},[month])
  useEffect(()=>{
    loadSequence.current+=1
    setData(null)
    setSelected(new Set())
    setProgrammingId(null)
    setFilters({
      operating:{area:'',search:''},
      stopped:{area:'',search:''},
      backlog:{area:'',search:''}
    })
  },[week?.from,week?.to,specialty])
  useEffect(()=>{load()},[week?.from,week?.to,specialty])
  const allRows=useMemo(()=>[...(data?.operating||[]),...(data?.stopped||[]),...(data?.backlog||[])],[data])
  const rowMap=useMemo(()=>new Map(allRows.map(row=>[Number(row.orden_mantenimiento_id),row])),[allRows])
  const selectedRows=useMemo(()=>[...selected].map(id=>rowMap.get(Number(id))).filter(Boolean).sort((left,right)=>Number(left.requiere_parada)-Number(right.requiere_parada)||String(left.area_codigo||'').localeCompare(String(right.area_codigo||''))||String(left.numero_ot||'').localeCompare(String(right.numero_ot||''))),[selected,rowMap])
  const selectedHH=useMemo(()=>selectedRows.reduce((sum,row)=>sum+number(row.hh),0),[selectedRows])
  const target=number(data?.capacity?.target)
  const techniciansAvailable=number(data?.capacity?.technicians_available,data?.capacity?.technicians||0)
  const techniciansAssigned=number(data?.capacity?.technicians_assigned,data?.capacity?.technicians||0)
  const remaining=Math.max(0,target-selectedHH)

  const monthlyBase=data?.monthly_demand||{}
  const monthPmpCount=number(monthlyBase.workload_pmp_month_count,monthlyBase.pmp_count)
  const monthPmpHH=number(monthlyBase.workload_pmp_month_hh,monthlyBase.pmp_hh)
  const initialBacklogCount=number(monthlyBase.workload_initial_backlog_count)
  const initialBacklogHH=number(monthlyBase.workload_initial_backlog_hh)
  const workloadBaseCount=number(monthlyBase.workload_base_count,monthPmpCount+initialBacklogCount)
  const workloadBaseHH=number(monthlyBase.workload_base_hh,monthPmpHH+initialBacklogHH)
  const remainingWorkCount=number(monthlyBase.remaining_for_week_count)
  const remainingWorkHH=number(monthlyBase.remaining_for_week_hh)
  const remainingMissingHH=number(monthlyBase.remaining_for_week_missing_hh)
  const remainingPmpHH=number(monthlyBase.remaining_pmp_hh)
  const remainingBacklogHH=number(monthlyBase.remaining_backlog_hh)
  const technicianMonthHH=number(monthlyBase.technician_month_preventive_hh)
  const technicianRemainingHH=number(monthlyBase.technician_remaining_preventive_hh)
  const weeklyProgressPct=target>0?Math.min(100,selectedHH/target*100):0

  const groupedRows=useMemo(()=>({
    operating:[...(data?.operating||[])],
    stopped:[...(data?.stopped||[])],
    backlog:[...(data?.backlog||[])]
  }),[data])
  function updateFilters(kind,patch){setFilters(current=>updateGroupFilters(current,kind,patch))}
  function toggle(row){if(!editing)return;const id=Number(row.orden_mantenimiento_id);setError('');setMessage('');setSelected(current=>{const result=toggleWeeklySelection({selected:current,id,row,rowMap,target});if(result.error){setError(`No se puede seleccionar esta actividad: llegarías a ${fmt(result.nextHH,1)} H-H y la meta máxima es ${fmt(target,1)} H-H.`);return current}if(result.changed)setDirty(true);return result.selected})}
  async function save(){if(!selected.size){setError('Selecciona al menos una orden para guardar la semana.');return}try{setSaving(true);setError('');setMessage('');const result=await saveV2WeekProgramming({date_from:week.from,date_to:week.to,specialty,order_ids:[...selected]});setProgrammingId(result.programming_id);setDirty(false);await load();setMessage(`Programación guardada: ${fmt(result.hh_programmed,1)} H-H de ${fmt(result.hh_target,1)} H-H objetivo.${result.moved_to_backlog?` ${result.moved_to_backlog} OT movida(s) a BACKLOG.`:''}`)}catch(cause){setError(cause.message)}finally{setSaving(false)}}
  async function report(format){if(!programmingId||dirty){setError('Guarda la programación antes de generar el reporte.');return}try{setError('');await downloadV2WeeklyReport(programmingId,format)}catch(cause){setError(cause.message)}}
  function cancelEdit(){load();setMessage('Cambios descartados. La programación vuelve a la última versión guardada.')}
  const groups=[
    {kind:'operating',rows:groupedRows.operating},
    {kind:'stopped',rows:groupedRows.stopped},
    {kind:'backlog',rows:groupedRows.backlog}
  ]
  const capacityChange=useMemo(()=>{
    const programming=data?.programming
    const previous=Number(programming?.hh_objetivo_anterior)
    if(!programmingId||!programming?.capacidad_modificada_en||!Number.isFinite(previous)||Math.abs(previous-target)<.01)return null
    const delta=round2(target-previous)
    const excess=round2(Math.max(0,selectedHH-target))
    const free=round2(Math.max(0,target-selectedHH))
    if(excess>.01){
      return {
        tone:'danger',
        kicker:'CAPACIDAD MODIFICADA',
        title:'Programación por encima de la nueva capacidad',
        text:'La meta preventiva cambió de '+fmt(previous,1)+' a '+fmt(target,1)+' H-H. Tienes '+fmt(selectedHH,1)+' H-H programadas y un exceso de '+fmt(excess,1)+' H-H.',
        previous,delta,excess,free,
      }
    }
    if(delta<0){
      return {
        tone:'warn',
        kicker:'CAPACIDAD REDUCIDA',
        title:'La programación sigue dentro de la nueva capacidad',
        text:'La meta preventiva bajó de '+fmt(previous,1)+' a '+fmt(target,1)+' H-H. Todavía quedan '+fmt(free,1)+' H-H disponibles.',
        previous,delta,excess,free,
      }
    }
    return {
      tone:'ok',
      kicker:'CAPACIDAD ADICIONAL DISPONIBLE',
      title:'Aumentó la capacidad preventiva de la semana',
      text:'La meta preventiva subió de '+fmt(previous,1)+' a '+fmt(target,1)+' H-H. Ahora tienes '+fmt(free,1)+' H-H disponibles para agregar actividades.',
      previous,delta,excess,free,
    }
  },[data?.programming,programmingId,target,selectedHH])
  return <div className="v2-stack v2-weekly-programming tf-weekly-compact">
    <section className="tf-program-controls">
      <div className="tf-program-selectors">
        <label><span>Semana</span><select value={weekIndex} onChange={event=>setWeekIndex(Number(event.target.value))}>{weeks.map((item,index)=><option key={item.from} value={index}>{item.transition?'Transición':'Semana '+item.weekNumber} · {item.label}</option>)}</select></label>
        <label><span>Especialidad</span><select value={specialty} onChange={event=>setSpecialty(event.target.value)}>{SPECS.map(item=><option key={item} value={item}>{item} · {SPEC_NAMES[item]}</option>)}</select></label>
        <div className="tf-tech-count">{loading?'Calculando...':<><b>{techniciansAvailable}</b> disponibles / {techniciansAssigned} asignados</>}</div>
      </div>
      <div className="tf-program-actions">
        {programmingId&&!editing&&<button type="button" className="v2-primary" onClick={()=>{setEditing(true);setMessage('Modo edición activado.')}}>Modificar</button>}
        {programmingId&&editing&&<button type="button" onClick={cancelEdit}>Cancelar cambios</button>}
        {programmingId&&<button type="button" disabled={dirty} onClick={()=>report('xlsx')}>Excel</button>}
        {programmingId&&<button type="button" disabled={dirty} onClick={()=>report('pdf')}>PDF</button>}
      </div>
    </section>

    <section className="tf-program-indicator-board" aria-label="Indicadores de programación semanal">
      <div className="tf-program-month-ref">
        <span>TOTAL PMP + BACKLOG · {SPEC_NAMES[specialty]}</span>
        <b>{workloadBaseCount} OT</b>
        <i>·</i>
        <b>{fmt(workloadBaseHH,1)} H-H</b>
        <small>{monthPmpCount} PMP del mes + {initialBacklogCount} Backlog heredado · dato fijo</small>
      </div>

      <div className="tf-program-status-row">
        <article className="tf-program-remaining-card">
          <div>
            <span>PENDIENTE A LA FECHA</span>
            <small>Saldo real del PMP del mes + Backlog después de los cierres anteriores a esta semana</small>
          </div>
          <div className="tf-program-remaining-values">
            <div><b>{remainingWorkCount}</b><span>OT pendientes</span></div>
            <div>
              <b>{fmt(remainingWorkHH,1)}</b>
              <span>H-H pendientes</span>
              <small className="tf-program-hh-breakdown">PMP pendientes: {fmt(remainingPmpHH,1)} H-H · Backlog pendiente: {fmt(remainingBacklogHH,1)} H-H</small>
            </div>
          </div>
        </article>

        <article className="tf-program-tech-card">
          <div>
            <span>H-H TÉCNICOS PROGRAMABLES</span>
            <small>Capacidad preventiva restante · 80% efectivo × 80% preventivo</small>
          </div>
          <b>{fmt(technicianRemainingHH,1)} H-H</b>
          <small>Total mensual programable: {fmt(technicianMonthHH,1)} H-H · 20% del efectivo reservado para correctivo</small>
        </article>
      </div>

      {remainingMissingHH>0&&(
        <div className="tf-program-data-warning">{remainingMissingHH} actividad(es) pendientes no tienen H-H calculables y no están incluidas en la comparación de horas.</div>
      )}

      <div className="tf-week-progress-card">
        <div className="tf-week-progress-head">
          <div>
            <span>PROGRAMACIÓN DE ESTA SEMANA</span>
            <strong>{fmt(selectedHH,1)} / {fmt(target,1)} H-H</strong>
          </div>
          <div className="tf-week-progress-meta">
            <b>{selected.size}</b><span>actividades seleccionadas</span>
          </div>
        </div>
        <div className="tf-week-progress-track">
          <div className="tf-week-progress-fill" style={{width:String(weeklyProgressPct)+'%'}} />
        </div>
        <div className="tf-week-progress-foot">
          <span>{fmt(weeklyProgressPct,1)}% programado</span>
          <b>{selectedHH>target?fmt(selectedHH-target,1)+' H-H sobre la meta':fmt(Math.max(0,target-selectedHH),1)+' H-H por programar'}</b>
        </div>
      </div>
    </section>

    {capacityChange&&<section className={'tf-capacity-change '+capacityChange.tone}>
      <div className="tf-capacity-change-copy">
        <span>{capacityChange.kicker}</span>
        <strong>{capacityChange.title}</strong>
        <small>{capacityChange.text} No se eliminó ninguna actividad automáticamente.</small>
      </div>
      <div className="tf-capacity-change-actions">
        {capacityChange.tone==='danger'&&<b>Exceso {fmt(capacityChange.excess,1)} H-H</b>}
        {capacityChange.tone==='ok'&&<b>+{fmt(Math.max(0,capacityChange.delta),1)} H-H</b>}
        {capacityChange.tone==='warn'&&<b>{fmt(capacityChange.delta,1)} H-H</b>}
        {!editing&&<button type="button" onClick={()=>{setEditing(true);setMessage('Revisa la programación frente a la nueva capacidad y guarda cuando quede ajustada.')}}>Revisar programación</button>}
      </div>
    </section>}

    <SelectionSummary key={week.from+'-'+specialty} rows={selectedRows} editing={editing} onToggle={toggle} dashboard={dashboard}/>

    {(editing||!programmingId)&&<section className="tf-save-strip">
      <div><b>{selected.size} actividades · {fmt(selectedHH,1)} H-H</b><span>{dirty?'Cambios sin guardar':'Selección actual'}</span></div>
      <div className="tf-save-strip-actions">
        {programmingId&&<button type="button" onClick={cancelEdit}>Descartar</button>}
        <button type="button" className="v2-primary" disabled={saving||!selected.size||selectedHH>target+.001||(!dirty&&!!programmingId&&!capacityChange)} onClick={save}>{saving?'Guardando...':programmingId?(capacityChange&&!dirty?'Aceptar nueva capacidad':'Guardar cambios'):'Guardar programación'}</button>
      </div>
    </section>}

    {error&&<div className="v2-error">{error}</div>}
    {message&&<div className="v2-success">{message}</div>}

    <section className="v2-panel tf-three-program-tables">
      {groups.map(group=><ActivityGroup key={group.kind} {...group} dashboard={dashboard} editing={editing} selected={selected} filters={filters[group.kind]} onFiltersChange={patch=>updateFilters(group.kind,patch)} onToggle={toggle}/>)}
    </section>
  </div>
}
