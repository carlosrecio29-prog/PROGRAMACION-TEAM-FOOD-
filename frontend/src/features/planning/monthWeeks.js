const MONTHS = ['Enero','Febrero','Marzo','Abril','Mayo','Junio','Julio','Agosto','Septiembre','Octubre','Noviembre','Diciembre']

const iso = date => date.toISOString().slice(0,10)
const atUtc = (year,month,day) => new Date(Date.UTC(year,month-1,day))

// Corte operativo de jueves a miércoles. Los días previos al primer jueves
// son la transición del corte anterior; no se pierden en el mes.
export function monthWeeks(year,month){
  const first = atUtc(year,month,1)
  const last = new Date(Date.UTC(year,month,0)).getUTCDate()
  const untilThursday = (4-first.getUTCDay()+7)%7
  const firstThursday = 1+untilThursday
  const weeks = []
  if(firstThursday>1){
    weeks.push({
      from: iso(first),
      to: iso(atUtc(year,month,firstThursday-1)),
      label: `1–${firstThursday-1} ${MONTHS[month-1]} (transición)`,
      transition:true,
    })
  }
  let weekNumber=1
  for(let day=firstThursday;day<=last;day+=7){
    const start=atUtc(year,month,day)
    const end=atUtc(year,month,day+6)
    const sameMonth=start.getUTCMonth()===end.getUTCMonth()
    weeks.push({
      from:iso(start), to:iso(end),
      label:sameMonth
        ? `${day}–${end.getUTCDate()} ${MONTHS[month-1]}`
        : `${day} ${MONTHS[month-1]} – ${end.getUTCDate()} ${MONTHS[end.getUTCMonth()]}`,
      weekNumber:weekNumber++,
      transition:false,
    })
  }
  return weeks
}

export function initialWeekIndex(weeks){
  return Math.max(0,weeks.findIndex(week=>!week.transition))
}
