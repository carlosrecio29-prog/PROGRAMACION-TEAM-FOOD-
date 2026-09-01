async function check(res){if(!res.ok){let detail=`HTTP ${res.status}`;try{const b=await res.json();detail=b.detail||JSON.stringify(b)}catch{}throw new Error(detail)}return res.json()}
export async function uploadFile(path,file,params={}){const qs=new URLSearchParams();Object.entries(params).forEach(([k,v])=>{if(v!==undefined&&v!==null&&v!=='')qs.set(k,v)});const form=new FormData();form.append('file',file);return check(await fetch(`${path}${qs.size?`?${qs}`:''}`,{method:'POST',body:form}))}
export async function getCapacity(dateFrom,dateTo){return check(await fetch(`/api/capacity?${new URLSearchParams({date_from:dateFrom,date_to:dateTo})}`))}
export async function getCandidates(filters){const qs=new URLSearchParams();Object.entries(filters).forEach(([k,v])=>{if(v!==undefined&&v!==null&&v!=='')qs.set(k,v)});return check(await fetch(`/api/candidates?${qs}`))}
export async function getMasterStatus(){return check(await fetch('/api/master-status'))}
export async function learnPlan(planId,payload){return check(await fetch(`/api/plans/${planId}/learn`,{method:'POST',headers:{'Content-Type':'application/json'},body:JSON.stringify(payload)}))}
export async function saveProgramming(payload){return check(await fetch('/api/programming',{method:'POST',headers:{'Content-Type':'application/json'},body:JSON.stringify(payload)}))}
export async function getProgrammingHistory(limit=50){return check(await fetch(`/api/programming/history?limit=${limit}`))}
export async function getProgrammingVersion(versionId){return check(await fetch(`/api/programming/version/${versionId}`))}
export async function closeProgramming(payload){return check(await fetch('/api/programming/close',{method:'POST',headers:{'Content-Type':'application/json'},body:JSON.stringify(payload)}))}

export async function getHealth(){return check(await fetch('/api/health'))}

export async function getMonthReconciliation(year,month){return check(await fetch(`/api/month-reconciliation?${new URLSearchParams({year,month})}`))}


export async function downloadProgrammingExport(versionId,format){
 const res=await fetch(`/api/programming/version/${versionId}/export.${format}`)
 if(!res.ok){
  let detail=`HTTP ${res.status}`
  try{const b=await res.json();detail=b.detail||JSON.stringify(b)}catch{}
  throw new Error(detail)
 }
 const blob=await res.blob()
 const disposition=res.headers.get('content-disposition')||''
 const match=disposition.match(/filename="?([^";]+)"?/i)
 const filename=match?.[1]||`programacion.${format}`
 const url=URL.createObjectURL(blob)
 const a=document.createElement('a')
 a.href=url;a.download=filename
 document.body.appendChild(a);a.click();a.remove()
 URL.revokeObjectURL(url)
}


export async function resetTestingData(){
 return check(await fetch('/api/testing/reset',{
  method:'POST',
  headers:{'Content-Type':'application/json'},
  body:JSON.stringify({confirmation:'REINICIAR PRUEBAS'})
 }))
}


export async function getPendingDefinitions(year,month,specialty=''){
 const qs=new URLSearchParams({year,month})
 if(specialty)qs.set('specialty',specialty)
 return check(await fetch(`/api/definitions/pending?${qs}`))
}

export async function savePlanDefinition(planId,payload){
 return check(await fetch(`/api/definitions/plans/${planId}`,{
  method:'POST',
  headers:{'Content-Type':'application/json'},
  body:JSON.stringify(payload)
 }))
}


export async function analyzeProgrammingClose(versionId,file){
 const form=new FormData()
 form.append('file',file)
 return check(await fetch(`/api/programming/version/${versionId}/analyze-close`,{
  method:'POST',
  body:form
 }))
}
