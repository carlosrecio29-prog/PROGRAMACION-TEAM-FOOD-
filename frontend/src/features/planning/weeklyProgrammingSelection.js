export function toggleWeeklySelection({selected,id,row,rowMap,target}){
  const next=new Set(selected)
  if(next.has(id)){
    next.delete(id)
    return {selected:next,changed:true,error:''}
  }
  const selectedHH=[...selected].reduce((sum,selectedId)=>sum+Number(rowMap.get(selectedId)?.hh||0),0)
  const nextHH=selectedHH+Number(row.hh||0)
  if(nextHH>target+.001)return {selected,changed:false,error:'capacity_exceeded',nextHH}
  next.add(id)
  return {selected:next,changed:true,error:''}
}
