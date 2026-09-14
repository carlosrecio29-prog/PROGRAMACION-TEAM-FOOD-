import assert from 'node:assert/strict'
import test from 'node:test'
import {readFileSync} from 'node:fs'
import {NAV_GROUPS,navigationIds,VIEW_META} from '../src/app/navigation.js'
import {getV2Backlog} from '../src/api.js'

const shell=readFileSync(new URL('../src/app/AppShell.jsx',import.meta.url),'utf8')
const backlog=readFileSync(new URL('../src/components/AccumulatedBacklog.jsx',import.meta.url),'utf8')
const closure=readFileSync(new URL('../src/components/WeeklyClosure.jsx',import.meta.url),'utf8')
const app=readFileSync(new URL('../src/App.jsx',import.meta.url),'utf8')

test('maps every existing module into the five operational flows',()=>{
  assert.deepEqual(NAV_GROUPS.map(group=>group.label),['Inicio','Planificación','Cierre','Backlog','Administración'])
  assert.deepEqual(new Set(navigationIds()),new Set(['summary','programming','pmp','closure','backlog','pending','technicians']))
  for(const id of navigationIds())assert.ok(VIEW_META[id],`missing metadata for ${id}`)
})

test('shell exposes accessible navigation, current page, period and connection status',()=>{
  for(const marker of ['aria-label="Navegación principal"','aria-label="Flujos operativos"','aria-current','aria-label="Periodo de trabajo"','role="status"']){
    assert.ok(shell.includes(marker),marker)
  }
})

test('active module is addressable and preserved in the URL hash',()=>{
  assert.ok(app.includes('window.location.hash'))
  assert.ok(app.includes('window.history.replaceState'))
})

test('backlog API keeps all independent filters and closure entry context',async()=>{
  let requested=''
  const previous=globalThis.fetch
  globalThis.fetch=async url=>{requested=String(url);return {ok:true,json:async()=>({rows:[],summary:{}})}}
  try{
    await getV2Backlog({state:'PENDIENTE_DISPONIBLE',specialty:'MEC',area:'ENV',search:'OT-7',age_min:7,age_max:30,order_id:42})
  }finally{
    globalThis.fetch=previous
  }
  for(const pair of ['state=PENDIENTE_DISPONIBLE','specialty=MEC','area=ENV','search=OT-7','age_min=7','age_max=30','order_id=42']){
    assert.ok(requested.includes(pair),pair)
  }
})

test('backlog renders lifecycle indicators, traceability and age controls',()=>{
  for(const marker of ['OT movidas a Backlog','Finalizadas por ingeniero','Pendientes activas','PENDIENTE_PROGRAMADA','reprogramaciones','Antigüedad mínima en días','Antigüedad máxima en días']){
    assert.ok(backlog.includes(marker),marker)
  }
})

test('closure uses backend HH summary and only offers backlog action for non-finalized results',()=>{
  assert.ok(closure.includes('summary.hh_programmed'))
  assert.ok(closure.includes('summary.hh_finalized'))
  assert.ok(closure.includes('summary.hh_pending'))
  assert.ok(closure.includes('summary.compliance_pct'))
  assert.ok(closure.includes('r.finalizado !== true && r.estado_cierre'))
  assert.ok(closure.includes('onOpenBacklog?.(r.orden_mantenimiento_id)'))
})
