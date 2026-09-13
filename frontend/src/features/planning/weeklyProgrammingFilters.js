export const emptyFilters={operating:{area:'',search:''},stopped:{area:'',search:''},backlog:{area:'',search:''}}

export function matchesFilters(rows,{area,search}){
  const query=search.trim().toLowerCase()
  return rows.filter(row=>{
    if(area&&row.area_codigo!==area)return false
    if(!query)return true
    return [row.numero_ot,row.activo_codigo,row.activo_descripcion,row.plan_trabajo].some(value=>String(value||'').toLowerCase().includes(query))
  })
}

export function updateGroupFilters(filters,group,patch){
  return {...filters,[group]:{...filters[group],...patch}}
}
