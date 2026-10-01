import {useEffect,useMemo,useState} from 'react'
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

function ActivityGroup({kind,rows,dashboard,editing,selected,filters,onFiltersChange,onToggle}){
  const config={
    operating:{title:'Equipo operando',description:'Actividades que no requieren detener el equipo.',tone:'ok'},
    stopped:{title:'Equipo detenido',description:'Actividades que requieren coordinación de parada.',tone:'stop'},
    backlog:{title:'Backlog',description:'Pendientes provenientes de programaciones anteriores.',tone:'backlog'}
  }[kind]
  const visible=matchesFilters(rows,filters)
  const selectedVisible=visible.filter(row=>selected.has(Number(row.orden_mantenimiento_id))).length
  return <section className={'v2-activity-section tf-program-table-section '+kind} aria-label={config.title}>
    <div className="tf-program-table-head">
      <div><h3>{config.title}</h3><p>{config.description}</p></div>
      <Badge tone={config.tone}>{selectedVisible} seleccionadas · {visible.length} total</Badge>
    </div>
    <div className="tf-table-filterbar" aria-label={'Filtros de '+config.title}>
      <label><span>Área</span><select aria-label={'Área en '+config.title} value={filters.area} onChange={event=>onFiltersChange({area:event.target.value})}><option value="">Todas</option>{(dashboard?.areas||[]).map(area=><option key={area.codigo} value={area.codigo}>{area.codigo} · {area.nombre||area.codigo}</option>)}</select></label>
      <label className="search"><span>Buscar</span><input aria-label={'Buscar en '+config.title} placeholder="OT, equipo o plan..." value={filters.search} onChange={event=>onFiltersChange({search:event.target.value})}/></label>
    </div>
    <div className="v2-table-wrap v2-program-table"><table><thead><tr>{kind==='backlog'&&<th>Origen</th>}<th>OT</th><th>Área</th><th>Equipo</th><th>Plan de trabajo</th><th>Personas</th><th>Tiempo</th><th>H-H</th><th>Acción</th></tr></thead><tbody>
      {visible.map(row=>{
        const id=Number(row.orden_mantenimiento_id)
        const chosen=selected.has(id)
        return <tr key={id} className={chosen?'v2-selected-row':''}>
          {kind==='backlog'&&<td><div className="v2-backlog-origin"><b>Backlog</b><small>{row.semana_origen_inicio||'Semana anterior'} {row.semana_origen_fin?'→ '+row.semana_origen_fin:''}</small></div></td>}
          <td><b>{row.numero_ot||'SIN ASIGNAR'}</b></td>
          <td><Badge>{row.area_codigo||'—'}</Badge><small>{row.area_nombre||''}</small></td>
          <td><b>{row.activo_codigo}</b><small>{row.activo_descripcion}</small></td>
          <td><span className="v2-plan">{row.plan_trabajo}</span><small>{row.descripcion_grupo||''}</small></td>
          <td><b>{row.numero_personas_efectivo}</b></td>
          <td>{fmt(row.tiempo_min,0)} min</td>
          <td><b>{fmt(row.hh,1)}</b></td>
          <td>{editing
            ? <button type="button" className={chosen?'v2-unselect':'v2-select'} onClick={()=>onToggle(row)}>{chosen?'Quitar':'Agregar'}</button>
            : <span className={chosen?'tf-programmed-tag':'tf-readonly-dash'}>{chosen?'Programada ✓':'—'}</span>}
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
  const week=weeks[Math.min(weekIndex,weeks.length-1)]||weeks[0]
  async function load(){if(!week)return;try{setLoading(true);setError('');const result=await getV2WeekProgramming(week.from,week.to,specialty);setData(result);setSelected(new Set((result.selected_ids||[]).map(Number)));setProgrammingId(result.programming?.id||null);setEditing(!result.programming);setDirty(false)}catch(cause){setError(cause.message)}finally{setLoading(false)}}
  useEffect(()=>{setWeekIndex(initialWeekIndex(weeks))},[month]);useEffect(()=>{load()},[week?.from,week?.to,specialty])
  const allRows=useMemo(()=>[...(data?.operating||[]),...(data?.stopped||[]),...(data?.backlog||[])],[data])
  const rowMap=useMemo(()=>new Map(allRows.map(row=>[Number(row.orden_mantenimiento_id),row])),[allRows])
  const selectedRows=useMemo(()=>[...selected].map(id=>rowMap.get(Number(id))).filter(Boolean).sort((left,right)=>Number(left.requiere_parada)-Number(right.requiere_parada)||String(left.area_codigo||'').localeCompare(String(right.area_codigo||''))||String(left.numero_ot||'').localeCompare(String(right.numero_ot||''))),[selected,rowMap])
  const selectedHH=useMemo(()=>selectedRows.reduce((sum,row)=>sum+number(row.hh),0),[selectedRows])
  const target=number(data?.capacity?.target)
  const techniciansAvailable=number(data?.capacity?.technicians_available,data?.capacity?.technicians||0)
  const techniciansAssigned=number(data?.capacity?.technicians_assigned,data?.capacity?.technicians||0)
  const remaining=Math.max(0,target-selectedHH)

  const monthly=useMemo(()=>{
    const base=data?.monthly_demand||{}
    const monthKey=String(week?.from||'').slice(0,7)
    const selectedMonthRows=selectedRows.filter(row=>String(row.periodo||'').slice(0,7)===monthKey)
    const selectedMonthHH=selectedMonthRows.reduce((sum,row)=>sum+number(row.hh),0)
    const pmpCount=number(base.pmp_count)
    const pmpHH=number(base.pmp_hh)
    const coveredCount=Math.min(pmpCount,number(base.covered_count_base)+selectedMonthRows.length)
    const coveredHH=Math.min(pmpHH,number(base.covered_hh_base)+selectedMonthHH)
    const pendingCount=Math.max(0,pmpCount-coveredCount)
    const pendingHH=Math.max(0,pmpHH-coveredHH)
    const demandBeforeWeekHH=Math.max(0,pmpHH-number(base.covered_hh_base))
    const coveragePossible=demandBeforeWeekHH>0?Math.min(100,target/demandBeforeWeekHH*100):100
    return {
      pmpCount,pmpHH,coveredCount,coveredHH,pendingCount,pendingHH,
      demandBeforeWeekHH,coveragePossible,missingHH:number(base.missing_hh_count)
    }
  },[data,selectedRows,target,week?.from])

  const groupedRows=useMemo(()=>{
    const backlog=[]
    const stopped=[]
    const operating=[]
    for(const row of allRows){
      const isBacklog=row.origen==='BACKLOG'||row.origen_backlog===true||row.es_backlog===true
      if(isBacklog)backlog.push(row)
      else if(row.requiere_parada===true)stopped.push(row)
      else operating.push(row)
    }
    return {operating,stopped,backlog}
  },[allRows])
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
  const coverageText=monthly.demandBeforeWeekHH<=.01
    ? 'PMP mensual cubierto'
    : target>=monthly.demandBeforeWeekHH-.01
      ? 'La capacidad de esta semana puede cubrir todo el PMP pendiente'
      : 'Cobertura posible esta semana: '+fmt(monthly.coveragePossible,1)+'% de las H-H PMP pendientes'
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

    <section className="tf-key-kpis">
      <article><span>PMP del mes</span><b>{monthly.pmpCount}</b><small>{monthly.coveredCount} cubiertos</small></article>
      <article><span>H-H PMP del mes</span><b>{fmt(monthly.pmpHH,1)}</b><small>demanda mensual</small></article>
      <article className="pending"><span>H-H pendientes mes</span><b>{fmt(monthly.pendingHH,1)}</b><small>{monthly.pendingCount} PMP pendientes</small></article>
      <article className="target"><span>Meta preventiva semana</span><b>{fmt(target,1)}</b><small>capacidad máxima</small></article>
      <article className="selected"><span>H-H seleccionadas</span><b>{fmt(selectedHH,1)}</b><small>{selected.size} actividades</small></article>
      <article className={remaining<=.01?'complete':'remaining'}><span>Disponible semana</span><b>{fmt(remaining,1)}</b><small>H-H por programar</small></article>
    </section>

    <div className={'tf-coverage-note '+(target>=monthly.demandBeforeWeekHH-.01?'enough':'partial')}>
      <span>{coverageText}</span>
      {monthly.missingHH>0&&<small>{monthly.missingHH} PMP sin H-H calculables</small>}
    </div>

    <SelectionSummary rows={selectedRows} editing={editing} onToggle={toggle} dashboard={dashboard}/>

    {(editing||!programmingId)&&<section className="tf-save-strip">
      <div><b>{selected.size} actividades · {fmt(selectedHH,1)} H-H</b><span>{dirty?'Cambios sin guardar':'Selección actual'}</span></div>
      <div className="tf-save-strip-actions">
        {programmingId&&<button type="button" onClick={cancelEdit}>Descartar</button>}
        <button type="button" className="v2-primary" disabled={saving||!selected.size||selectedHH>target+.001||(!dirty&&!!programmingId)} onClick={save}>{saving?'Guardando...':programmingId?'Guardar cambios':'Guardar programación'}</button>
      </div>
    </section>}

    {error&&<div className="v2-error">{error}</div>}
    {message&&<div className="v2-success">{message}</div>}

    <section className="v2-panel tf-three-program-tables">
      {groups.map(group=><ActivityGroup key={group.kind} {...group} dashboard={dashboard} editing={editing} selected={selected} filters={filters[group.kind]} onFiltersChange={patch=>updateFilters(group.kind,patch)} onToggle={toggle}/>)}
    </section>
  </div>
}
