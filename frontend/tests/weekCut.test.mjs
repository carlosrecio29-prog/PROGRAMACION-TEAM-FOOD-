import assert from 'node:assert/strict'
import test from 'node:test'
import {monthWeeks, initialWeekIndex} from '../src/features/planning/monthWeeks.js'

test('September 2026 first complete Thursday-Wednesday cut is 3-9', ()=>{
  const weeks=monthWeeks(2026,9)
  assert.deepEqual(weeks.map(w=>[w.from,w.to]),[
    ['2026-09-01','2026-09-02'],
    ['2026-09-03','2026-09-09'],
    ['2026-09-10','2026-09-16'],
    ['2026-09-17','2026-09-23'],
    ['2026-09-24','2026-09-30'],
  ])
  assert.equal(initialWeekIndex(weeks),1)
  assert.equal(weeks[1].weekNumber,1)
})

test('crosses month when Thursday-Wednesday cut crosses its boundary', ()=>{
  const weeks=monthWeeks(2026,10)
  assert.deepEqual(weeks.at(-1).from,'2026-10-29')
  assert.deepEqual(weeks.at(-1).to,'2026-11-04')
  assert.equal(initialWeekIndex(weeks),0)
})
