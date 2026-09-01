import {useEffect,useState} from 'react'
import ImportPanel from './components/ImportPanel'
import SpecialtyPlanner from './components/SpecialtyPlanner'
import MasterImportPanel from './components/MasterImportPanel'
import {getHealth,getMasterStatus,resetTestingData} from './api'
import './styles.css'

const SPECS=['MEC','ELE','SER','MET']
const NAMES={MEC:'Mecánica',ELE:'Eléctrica',SER:'Servicios',MET:'Metrología'}
const ICONS={MEC:'ME',ELE:'EL',SER:'SE',MET:'MT'}

export default function App(){
  const [active,setActive]=useState('MEC')
  const [capacity,setCapacity]=useState({})
  const [week,setWeek]=useState({from:'2026-09-01',to:'2026-09-07'})
  const [master,setMaster]=useState(null)
  const [health,setHealth]=useState('checking')
  const [healthError,setHealthError]=useState('')
  const [resetting,setResetting]=useState(false)

  useEffect(()=>{
    getMasterStatus().then(setMaster).catch(()=>{})
    getHealth().then(()=>{setHealth('ok');setHealthError('')}).catch(e=>{setHealth('error');setHealthError(e.message)})
  },[])
  async function resetTests(){
    const ok=window.confirm(
      '¿Reiniciar todas las pruebas?\n\nSe borrarán únicamente programaciones y aprendizajes marcados como PRUEBA_WEB. Los maestros, PMP, activos, técnicos y turnos NO se tocarán.'
    )
    if(!ok)return
    try{
      setResetting(true)
      const r=await resetTestingData()
      window.alert(
        'Pruebas reiniciadas.\nProgramaciones: '+r.programming_deleted+
        '\nActividades: '+r.items_deleted+
        '\nAprendizajes: '+r.learning_reset
      )
      window.location.reload()
    }catch(e){
      window.alert('No se pudo reiniciar: '+e.message)
    }finally{
      setResetting(false)
    }
  }

  const latest=master?.latest_period
  const period=latest?String(latest.mes).padStart(2,'0')+'/'+latest.anio:'09/2026'

  return <div className="app-shell">
    <aside className="sidebar">
      <div className="brand">
        <div className="brand-mark">CEK</div>
        <div><strong>Programación</strong><span>Mantenimiento preventivo</span></div>
      </div>
      <nav>
        <a className="nav-active" href="#planner"><span>01</span> Programación semanal</a>
        <a href="#master"><span>02</span> Fuente maestra</a>
      </nav>
      <div className="test-reset-box">
        <span>MODO PRUEBAS</span>
        <button className="reset-tests-btn" onClick={resetTests} disabled={resetting}>
          {resetting?'Reiniciando...':'Reiniciar pruebas'}
        </button>
        <small>Solo borra datos creados durante las pruebas.</small>
      </div>
      <div className="sidebar-foot">
        <small>Periodo activo</small>
        <strong>{period}</strong>
        <span>TEAM FOOD · Supabase</span>
      </div>
    </aside>

    <main>
      <header className="topbar">
        <div>
          <div className="eyebrow">PLANTA BARRANQUILLA · PMP</div>
          <h1>Programación semanal de mantenimiento</h1>
          <p>Selecciona la semana, revisa la capacidad de la especialidad y arma el paquete de trabajo.</p>
        </div>
        <div className={'status-pill '+(health==='error'?'status-error':health==='checking'?'status-checking':'')}>
          <i/> {health==='ok'?'Base conectada':health==='error'?'Error de conexión':'Verificando base...'}
        </div>
      </header>
      {health==='error'&&<div className="backend-error">
        <b>El backend no logra conectarse a Supabase.</b>
        <span>{healthError}</span>
      </div>}

      <ImportPanel onCapacity={(c,w)=>{setCapacity(c);setWeek(w)}} initialWeek={week}/>

      <section id="planner" className="panel planner-panel">
        <div className="section-head">
          <div>
            <span className="section-kicker">PASO 2</span>
            <h2>Selecciona la especialidad</h2>
            <p>La capacidad se calcula con los turnos reales y solo se programa hasta el 80%.</p>
          </div>
          <div className="week-badge">{week?.from} → {week?.to}</div>
        </div>

        <div className="specialty-tabs">
          {SPECS.map(s=>{
            const c=capacity[s]||{}
            return <button className={active===s?'active':''} key={s} onClick={()=>setActive(s)}>
              <span className="spec-icon">{ICONS[s]}</span>
              <span className="spec-copy"><b>{NAMES[s]}</b><small>{Number(c.technicians||0)} técnicos · {Number(c.target||0).toFixed(1)} H-H meta</small></span>
            </button>
          })}
        </div>

        <SpecialtyPlanner specialty={active} specialtyName={NAMES[active]} capacity={capacity[active]} week={week} year={2026} month={9}/>
      </section>

      <div id="master"><MasterImportPanel/></div>
    </main>
  </div>
}
