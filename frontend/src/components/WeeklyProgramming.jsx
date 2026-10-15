import {useEffect,useMemo,useState} from 'react'
import {monthWeeks,initialWeekIndex} from '../features/planning/monthWeeks.js'
import {getV2WeekProgramming,getV2WeekTracking,saveV2WeekProgramming,downloadV2WeeklyReport} from '../api'
import {emptyFilters,matchesFilters,updateGroupFilters} from '../features/planning/weeklyProgrammingFilters'
import {toggleWeeklySelection} from '../features/planning/weeklyProgrammingSelection'
import Badge from '../shared/Badge'
import alianzaTeamLogo from '../assets/alianzaTeamLogoData.js'

const SPEC_NAMES={MEC:'Mecánica',ELE:'Eléctrica',MET:'Metrología',SER:'Servicios'}
const SPECS=['MEC','ELE','MET','SER']

function number(value,fallback=0){const parsed=Number(value);return Number.isFinite(parsed)?parsed:fallback}
function fmt(value,decimals=1){return number(value).toLocaleString('es-CO',{minimumFractionDigits:decimals,maximumFractionDigits:decimals})}
function round2(value){return Math.round((number(value)+Number.EPSILON)*100)/100}

function ActivityGroup({kind,rows,dashboard,editing,selected,closedWeek,filters,onFiltersChange,onToggle}){
  const config={
    operating:{title:'Equipo operando',description:'Actividades que no requieren detener el equipo.',tone:'ok'},
    stopped:{title:'Equipo detenido',description:'Actividades que requieren coordinación de parada.',tone:'stop'},
    backlog:{title:'Backlog',description:'Pendientes provenientes de programaciones anteriores.',tone:'backlog'}
  }[kind]
  const visible=matchesFilters(rows,filters)
  const selectedVisible=visible.filter(row=>selected.has(Number(row.orden_mantenimiento_id))).length
  return <section className={'v2-activity-section tf-program-table-section '+kind} aria-label={config.title}>
    <div className="tf-program-table-head">
      <div><h3>{config.title}</h3><p>{config.description}</p>
        {!editing&&<small className="tf-program-color-legend">Verde y subrayado: programadas en esta semana. Las no seleccionadas siguen al próximo corte sólo si el cierre confirma que continúan pendientes.</small>}
      </div>
      <Badge tone={config.tone}>{editing?`${selectedVisible} seleccionadas · ${visible.length} total`:`${selectedVisible} programadas ✓ · ${visible.length-selectedVisible} no seleccionadas`}</Badge>
    </div>
    <div className="tf-table-filterbar" aria-label={'Filtros de '+config.title}>
      <label><span>Área</span><select aria-label={'Área en '+config.title} value={filters.area} onChange={event=>onFiltersChange({area:event.target.value})}><option value="">Todas</option>{(dashboard?.areas||[]).map(area=><option key={area.codigo} value={area.codigo}>{area.codigo} · {area.nombre||area.codigo}</option>)}</select></label>
      <label className="search"><span>Buscar</span><input aria-label={'Buscar en '+config.title} placeholder="OT, equipo o plan..." value={filters.search} onChange={event=>onFiltersChange({search:event.target.value})}/></label>
    </div>
    <div className="v2-table-wrap v2-program-table"><table><thead><tr>{kind==='backlog'&&<th>Origen</th>}<th>OT</th><th>Área</th><th>Equipo</th><th>Plan de trabajo</th><th>Personas</th><th>Tiempo</th><th>H-H</th><th>Acción</th></tr></thead><tbody>
      {visible.map(row=>{
        const id=Number(row.orden_mantenimiento_id)
        const chosen=selected.has(id)
        return <tr key={id} className={chosen?'v2-selected-row tf-programmed-highlight':'tf-unselected-activity'}>
          {kind==='backlog'&&<td><div className="v2-backlog-origin"><b>Backlog</b><small>{row.semana_origen_inicio||'Semana anterior'} {row.semana_origen_fin?'→ '+row.semana_origen_fin:''}</small></div></td>}
          <td><b className={chosen?'tf-ot-programmed-underline':''}>{row.numero_ot||'SIN ASIGNAR'}</b>{chosen&&<small className="tf-programmed-note">✓ Seleccionada en esta semana</small>}</td>
          <td><Badge>{row.area_codigo||'—'}</Badge><small>{row.area_nombre||''}</small></td>
          <td><b>{row.activo_codigo}</b><small>{row.activo_descripcion}</small></td>
          <td><span className="v2-plan">{row.plan_trabajo}</span><small>{row.descripcion_grupo||''}</small></td>
          <td><b>{row.numero_personas_efectivo}</b></td>
          <td>{fmt(row.tiempo_min,0)} min</td>
          <td><b>{fmt(row.hh,1)}</b></td>
          <td>{editing
            ? <button type="button" className={chosen?'v2-unselect':'v2-select'} onClick={()=>onToggle(row)}>{chosen?'Quitar':'Agregar'}</button>
            : <span className={chosen?'tf-programmed-tag':'tf-not-programmed-tag'}>{chosen?'✓ Programada':'No seleccionada'}</span>}
          </td>
        </tr>
      })}
      {!visible.length&&<tr><td colSpan={kind==='backlog'?9:8} className="v2-empty">No hay actividades con estos filtros.</td></tr>}
    </tbody></table></div>
  </section>
}

function SelectionSummary({rows,editing,onToggle,dashboard,trackingByOrder,closedWeek}){
  function executionState(row){
    // El cierre histórico es la fuente de verdad cuando la semana está cerrada.
    if(closedWeek){
      if(String(row.estado_cierre||'').toUpperCase()==='ANULADA')return 'annulled'
      if(row.finalizado===true)return 'done'
      if(row.finalizado===false)return 'pending'
    }
    const snapshot=trackingByOrder.get(Number(row.orden_mantenimiento_id))
    if(snapshot?.finalizado===true)return 'done'
    if(snapshot?.finalizado===false)return 'pending'
    return 'unchecked'
  }
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
        <p>{editing?'Aquí ves únicamente las actividades que estás programando.':'Estas son las actividades guardadas. Verde = finalizada, amarillo = pendiente y gris = sin validar; la selección no implica ejecución.'}</p>
      </div>
      <div className="v2-selected-totals">
        <span><b>{rows.length}</b> actividades</span>
        <span><b>{fmt(operatingHH,1)}</b> H-H operando</span>
        <span><b>{fmt(stoppedHH,1)}</b> H-H detenido</span>
        <span className="total"><b>{fmt(totalHH,1)}</b> H-H total</span>
      </div>
    </div>
    <div className="tf-table-filterbar tf-selected-filterbar">
      <label><span>Área</span><select value={area} onChange={event=>setArea(event.target.value)}><option value="">Todas</option>{(dashboard?.areas||[]).map(item=><option key={item.codigo} value={item.codigo}>{item.codigo} · {item.nombre||item.codigo}</option>)}</select></label>
      <label className="search"><span>Buscar</span><input placeholder="OT, equipo o plan..." value={search} onChange={event=>setSearch(event.target.value)}/></label>
      <small>{visibleRows.length} de {rows.length}</small>
    </div>
    <div className="v2-table-wrap v2-selected-table"><table>
      <thead><tr><th>Condición</th><th>Origen</th><th>OT</th><th>Estado de ejecución</th><th>Área</th><th>Equipo</th><th>Plan de trabajo</th><th>Personas</th><th>Tiempo</th><th>H-H</th>{editing&&<th>Acción</th>}</tr></thead>
      <tbody>
        {visibleRows.map(row=>{
          const state=executionState(row)
          const statusLabel={done:'FINALIZADA ✓',pending:'PENDIENTE',annulled:'ANULADA',unchecked:'SIN VALIDAR'}[state]
          return <tr className={'tf-selected-summary-row tf-summary-'+state} key={row.orden_mantenimiento_id}>
          <td>{row.requiere_parada?<Badge tone="stop">Equipo detenido</Badge>:<Badge tone="ok">Equipo funcionando</Badge>}</td>
          <td>{row.origen==='BACKLOG'||row.origen_backlog?<Badge tone="backlog">BACKLOG</Badge>:<Badge>PMP DEL MES</Badge>}</td>
          <td><b>{row.numero_ot||'SIN ASIGNAR'}</b><small className="tf-summary-programmed-note">Seleccionada para esta semana</small></td>
          <td><span className={'tf-execution-state tf-execution-'+state}>{statusLabel}</span></td>
          <td><Badge>{row.area_codigo||'—'}</Badge><small>{row.area_nombre||''}</small></td>
          <td><b>{row.activo_codigo}</b><small>{row.activo_descripcion}</small></td>
          <td><span className="v2-plan">{row.plan_trabajo}</span><small>{row.descripcion_grupo||''}</small></td>
          <td><b>{row.numero_personas_efectivo}</b></td>
          <td>{fmt(row.tiempo_min,0)} min</td>
          <td><b>{fmt(row.hh,1)}</b></td>
          {editing&&<td><button type="button" className="v2-unselect" onClick={()=>onToggle(row)}>Quitar</button></td>}
        </tr>})}
        {!visibleRows.length&&<tr><td colSpan={editing?11:10} className="v2-empty">{rows.length?'No hay actividades con estos filtros.':'Todavía no has seleccionado actividades para esta semana.'}</td></tr>}
      </tbody>
    </table></div>
  </section>
}

export default function WeeklyProgramming({year,month,dashboard}){
  const weeks=useMemo(()=>monthWeeks(year,month),[year,month])
  const [weekIndex,setWeekIndex]=useState(()=>initialWeekIndex(weeks));const [specialty,setSpecialty]=useState('MEC');const [data,setData]=useState(null);const [tracking,setTracking]=useState(null);const [selected,setSelected]=useState(new Set());const [filters,setFilters]=useState(emptyFilters);const [loading,setLoading]=useState(false);const [saving,setSaving]=useState(false);const [error,setError]=useState('');const [message,setMessage]=useState('');const [dirty,setDirty]=useState(false);const [programmingId,setProgrammingId]=useState(null);const [editing,setEditing]=useState(true)
  const week=weeks[Math.min(weekIndex,weeks.length-1)]||weeks[0]
  async function load(){if(!week)return;try{setLoading(true);setError('');const result=await getV2WeekProgramming(week.from,week.to,specialty);setData(result);setSelected(new Set((result.selected_ids||[]).map(Number)));setProgrammingId(result.programming?.id||null);setEditing(!result.programming);setDirty(false)}catch(cause){setError(cause.message)}finally{setLoading(false)}}
  useEffect(()=>{setWeekIndex(initialWeekIndex(weeks))},[month]);useEffect(()=>{load()},[week?.from,week?.to,specialty])
  // Lectura del último seguimiento. No escribe ni altera programación/cierres.
  useEffect(()=>{
    const programmingId=data?.programming?.id
    let active=true
    setTracking(null)
    if(programmingId){
      getV2WeekTracking(programmingId)
        .then(result=>{if(active)setTracking({programmingId,...result})})
        .catch(()=>{if(active)setTracking(null)})
    }
    return ()=>{active=false}
  },[data?.programming?.id,data?.programming?.actualizado_en])
  const trackingByOrder=useMemo(()=>new Map(
    (tracking?.programmingId===data?.programming?.id?tracking?.rows||[]:[])
      .map(row=>[Number(row.orden_mantenimiento_id),row])
  ),[tracking,data?.programming?.id])
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
  const isFirstWeek=week?.weekNumber===1
  const remainingMissingHH=number(isFirstWeek?monthlyBase.workload_base_missing_hh:monthlyBase.remaining_for_week_missing_hh)
  const closedWeek=data?.programming?.estado==='CERRADA'
  // El seguimiento puede detectar OT finalizadas fuera del programa antes
  // del cierre. No volver a ofrecerlas para programar, pero tampoco restarlas
  // del balance oficial de PMP hasta que ese cierre sea confirmado.
  const executedPendingClose=useMemo(()=>allRows.filter(row=>
    row.ejecutada_pendiente_cierre===true
    && !selected.has(Number(row.orden_mantenimiento_id))
  ),[allRows,selected])
  // Conservar en las tablas de su semana las OT seleccionadas, también después
  // del cierre, para resaltarlas sin alterar la programación ni el saldo.
  // Sólo se apartan del programador las detectadas como finalizadas en un
  // seguimiento aún pendiente de cierre (otras semanas).
  const listedRows=useMemo(()=>allRows.filter(row=>
    row.ejecutada_pendiente_cierre!==true
  ),[allRows])
  // El indicador muestra la carga al COMIENZO del corte: nunca resta
  // las OT seleccionadas en la misma semana antes de su cierre.
  const availableWorkMetrics=useMemo(()=>allRows.reduce((totals,row)=>{
    const hh=number(row.hh)
    const isBacklog=row.origen==='BACKLOG'||row.origen_backlog===true||row.es_backlog===true
    totals.count+=1
    totals.hh+=hh
    if(isBacklog)totals.backlogHH+=hh
    else totals.pmpHH+=hh
    return totals
  },{count:0,hh:0,pmpHH:0,backlogHH:0}),[allRows])
  // Primer corte = PMP del mes + backlog inicial completo (incluso OT sin HH).
  // Cortes siguientes = suma exacta de las 3 tablas, ya descontados los cierres previos.
  const remainingWorkCount=isFirstWeek?workloadBaseCount:availableWorkMetrics.count
  const remainingWorkHH=isFirstWeek?workloadBaseHH:round2(availableWorkMetrics.hh)
  const remainingPmpHH=isFirstWeek?monthPmpHH:round2(availableWorkMetrics.pmpHH)
  const remainingBacklogHH=isFirstWeek?initialBacklogHH:round2(availableWorkMetrics.backlogHH)
  const reconciliation=data?.weekly_reconciliation||null
  const showReconciliation=!!(week?.weekNumber>1&&reconciliation)
  const technicianMonthHH=number(monthlyBase.technician_month_preventive_hh)
  const technicianRemainingHH=number(monthlyBase.technician_remaining_preventive_hh)
  const weeklyProgressPct=target>0?Math.min(100,selectedHH/target*100):0

  const groupedRows=useMemo(()=>{
    const backlog=[]
    const stopped=[]
    const operating=[]
    for(const row of listedRows){
      const isBacklog=row.origen==='BACKLOG'||row.origen_backlog===true||row.es_backlog===true
      if(isBacklog)backlog.push(row)
      else if(row.requiere_parada===true)stopped.push(row)
      else operating.push(row)
    }
    return {operating,stopped,backlog}
  },[listedRows])
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
            <span>OT PENDIENTES AL INICIO DE LA SEMANA</span>
            <small>{isFirstWeek
              ? 'PMP total del mes + backlog heredado, antes de descontar cualquier cierre'
              : 'Equipo operando + Equipo detenido + Backlog; solo descuentan cierres anteriores confirmados'}</small>
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

      {showReconciliation&&<section className="tf-week-reconciliation" aria-label="Conciliación de órdenes pendientes">
        <div className="tf-week-reconciliation-title">
          <div>
            <strong>¿Cómo se calcula el pendiente de esta semana?</strong>
            <small>Se descuentan únicamente los resultados de cierres semanales anteriores confirmados.</small>
          </div>
          <span>CONCILIACIÓN DEL CORTE</span>
        </div>
        <div className="tf-week-reconciliation-flow">
          <div className="tf-week-reconciliation-cell start">
            <small>PMP + backlog inicial</small><strong>{fmt(reconciliation.initial_count,0)}</strong><span>OT</span>
          </div>
          <b className="tf-week-reconciliation-operator">−</b>
          <div className="tf-week-reconciliation-cell">
            <small>Programadas finalizadas</small><strong>{fmt(reconciliation.finalized_programmed_count,0)}</strong><span>OT</span>
          </div>
          <b className="tf-week-reconciliation-operator">−</b>
          <div className="tf-week-reconciliation-cell">
            <small>Finalizadas fuera del programa</small><strong>{fmt(reconciliation.finalized_unplanned_count,0)}</strong><span>OT del PMP/backlog</span>
          </div>
          <b className="tf-week-reconciliation-operator">−</b>
          <div className="tf-week-reconciliation-cell">
            <small>Anuladas en cierre</small><strong>{fmt(reconciliation.annulled_count,0)}</strong><span>OT</span>
          </div>
          <b className="tf-week-reconciliation-operator">=</b>
          <div className="tf-week-reconciliation-cell total">
            <small>Saldo tras los cierres</small><strong>{fmt(reconciliation.remaining_count,0)}</strong><span>OT pendientes</span>
          </div>
        </div>
        {number(reconciliation.external_executed_count)>0&&<div className="tf-week-reconciliation-extra">
          <b>{fmt(number(reconciliation.finalized_unplanned_count)+number(reconciliation.external_executed_count),0)} OT finalizadas fuera de programación:</b>
          {' '}{fmt(reconciliation.finalized_unplanned_count,0)} del PMP/backlog descontadas del saldo y {fmt(reconciliation.external_executed_count,0)} emergentes ajenas a la base inicial contabilizadas solo como ejecución adicional.
        </div>}
      </section>}

      {executedPendingClose.length>0&&<div className="tf-program-executed-warning" role="status">
        <strong>{executedPendingClose.length} OT ejecutadas fuera de la selección semanal</strong>
        <span>La Lista de Calendario las registra como finalizadas, pero no estaban seleccionadas
          en la programación de este corte. Por eso se apartan de las tres tablas para que no vuelvas a programarlas.</span>
        <div className="tf-executed-reconciliation">
          <span><b>{remainingWorkCount}</b> OT al iniciar la semana</span>
          <span className="tf-executed-reconciliation-minus">− {executedPendingClose.length} ya ejecutadas</span>
          <span><b>{listedRows.length}</b> OT visibles, incluidas las ya seleccionadas</span>
        </div>
        <span>El seguimiento detecta su ejecución de inmediato. El cierre semanal sigue pendiente de confirmación
          y es el que actualiza el saldo oficial para la semana siguiente.</span>
        <details className="tf-executed-details">
          <summary>Ver las {executedPendingClose.length} OT identificadas</summary>
          <small>{executedPendingClose.map(row=>row.numero_ot||'SIN ASIGNAR').join(' · ')}</small>
        </details>
      </div>}

      {remainingMissingHH>0&&(
        <div className="tf-program-data-warning">{remainingMissingHH} actividad(es) sin H-H calculables: {isFirstWeek
          ? 'se incluyen en las OT iniciales, pero no en las H-H ni en las tablas programables.'
          : 'requieren completar datos y no se incluyen en el total de las tres tablas ni en sus H-H.'}</div>
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

    <SelectionSummary rows={selectedRows} editing={editing} onToggle={toggle} dashboard={dashboard} trackingByOrder={trackingByOrder} closedWeek={closedWeek}/>

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
      {groups.map(group=><ActivityGroup key={group.kind} {...group} dashboard={dashboard} editing={editing} selected={selected} closedWeek={closedWeek} filters={filters[group.kind]} onFiltersChange={patch=>updateFilters(group.kind,patch)} onToggle={toggle}/>)}
    </section>
  </div>
}
