import { useState } from 'react'
import ImportPanel from './components/ImportPanel'
import SpecialtyPlanner from './components/SpecialtyPlanner'
import MasterImportPanel from './components/MasterImportPanel'
import './styles.css'

const SPECS=['MEC','ELE','MET','SER']
const NAMES={MEC:'Mecánica',ELE:'Eléctrica',MET:'Metrología',SER:'Servicios'}

export default function App(){
  const [active,setActive]=useState('MEC')
  const [capacity,setCapacity]=useState({})
  const [week,setWeek]=useState(null)
  return <div className="app-shell">
    <aside><h1>Programador de Mantenimiento</h1><p>React + FastAPI + Supabase</p><a href="#imports">Archivos</a><a href="#planner">Programación</a></aside>
    <main><header><div><h2>Programación semanal</h2><p>Importa, calcula capacidad y selecciona PMP.</p></div><span>BASE DE DATOS</span></header>
      <div id="imports"><ImportPanel onCapacity={(c,w)=>{setCapacity(c);setWeek(w)}}/><MasterImportPanel/></div>
      <section id="planner" className="panel"><h2>Programación por especialidad</h2>
        <div className="tabs">{SPECS.map(s=><button className={active===s?'active':''} key={s} onClick={()=>setActive(s)}>{NAMES[s]}</button>)}</div>
        <SpecialtyPlanner specialty={active} capacity={capacity[active]} week={week}/>
      </section>
    </main>
  </div>
}
