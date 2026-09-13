import assert from 'node:assert/strict'
import test from 'node:test'
import {emptyFilters,matchesFilters,updateGroupFilters} from '../src/features/planning/weeklyProgrammingFilters.js'
import {toggleWeeklySelection} from '../src/features/planning/weeklyProgrammingSelection.js'

const rows=[
  {numero_ot:'OT-100',area_codigo:'ENV',activo_codigo:'BOM-01',activo_descripcion:'Bomba principal',plan_trabajo:'Inspección'},
  {numero_ot:'OT-200',area_codigo:'PRO',activo_codigo:'MOT-02',activo_descripcion:'Motor auxiliar',plan_trabajo:'Lubricación'}
]

test('filters each activity group without sharing area or search state',()=>{
  const operating=updateGroupFilters(emptyFilters,'operating',{area:'ENV',search:'bomba'})
  assert.equal(operating.operating.area,'ENV')
  assert.equal(operating.operating.search,'bomba')
  assert.deepEqual(operating.stopped,emptyFilters.stopped)
  assert.deepEqual(operating.backlog,emptyFilters.backlog)
  assert.deepEqual(matchesFilters(rows,operating.operating),[rows[0]])
})

test('preserves another group filters when a group receives a new patch',()=>{
  const withStoppedSearch=updateGroupFilters(emptyFilters,'stopped',{search:'motor'})
  const withBacklogArea=updateGroupFilters(withStoppedSearch,'backlog',{area:'ENV'})
  assert.equal(withBacklogArea.stopped.search,'motor')
  assert.equal(withBacklogArea.backlog.area,'ENV')
  assert.equal(withBacklogArea.operating.search,'')
  assert.deepEqual(matchesFilters(rows,withStoppedSearch.stopped),[rows[1]])
})

test('selects and removes activities without mutating the previous selection',()=>{
  const first={orden_mantenimiento_id:1,hh:2};const second={orden_mantenimiento_id:2,hh:3};const rowMap=new Map([[1,first],[2,second]])
  const initial=new Set([1]);const added=toggleWeeklySelection({selected:initial,id:2,row:second,rowMap,target:8})
  assert.deepEqual([...initial],[1])
  assert.deepEqual([...added.selected],[1,2])
  const removed=toggleWeeklySelection({selected:added.selected,id:1,row:first,rowMap,target:8})
  assert.deepEqual([...removed.selected],[2])
})

test('keeps the current selection when an activity exceeds the capacity target',()=>{
  const first={orden_mantenimiento_id:1,hh:4};const second={orden_mantenimiento_id:2,hh:3};const rowMap=new Map([[1,first],[2,second]])
  const selected=new Set([1]);const result=toggleWeeklySelection({selected,id:2,row:second,rowMap,target:6})
  assert.equal(result.error,'capacity_exceeded')
  assert.equal(result.changed,false)
  assert.equal(result.selected,selected)
  assert.equal(result.nextHH,7)
})
