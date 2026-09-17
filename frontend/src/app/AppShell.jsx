import MaintenanceBaseUpload from "../components/MaintenanceBaseUpload";
import PendingDataIndicators from "../components/PendingDataIndicators";
import ShiftSettings from "../components/ShiftSettings";
import companyLogo from "../assets/cek-global-inspection.jpg";
import "../admin-improvements.css";
import { MONTHS, NAV_GROUPS, VIEW_META } from "./navigation";

export default function AppShell({
  view,
  onNavigate,
  year,
  month,
  onMonthChange,
  health,
  indicators = {},
  children,
}) {
  const [title, description] = VIEW_META[view] || VIEW_META.summary;
  return (
    <div className="v2-shell">
      <aside className="v2-sidebar" aria-label="Navegación principal">
        <div className="v2-brand">
          <img
            className="v2-brand-logo"
            src={companyLogo}
            alt="C.E.K Global Inspection Services"
          />
          <span>
            <b>PROGRAMACIÓN</b>
            <small>TEAM FOOD · Barranquilla</small>
          </span>
        </div>
        <nav aria-label="Flujos operativos">
          {NAV_GROUPS.map((group) => (
            <div className="v2-nav-group" key={group.label}>
              <span className="v2-nav-label">{group.label}</span>
              {group.items.map((item) => (
                <button
                  type="button"
                  key={item.id}
                  className={view === item.id ? "active" : ""}
                  aria-current={view === item.id ? "page" : undefined}
                  onClick={() => onNavigate(item.id)}
                >
                  <span>{item.code}</span>
                  {item.label}
                  {item.indicator && Number(indicators[item.indicator]) > 0 && (
                    <i aria-label={`${indicators[item.indicator]} pendientes`}>
                      {indicators[item.indicator]}
                    </i>
                  )}
                </button>
              ))}
            </div>
          ))}
        </nav>
        <div className="v2-side-note">
          <small>Fuente principal</small>
          <b>Software de mantenimiento</b>
          <span>TEAM FOOD planea, concilia y conserva el historial operativo.</span>
        </div>
        <div className="v2-profile">
          <span>Equipo de mantenimiento</span>
          <small>C.E.K GLOBAL INSPECTION</small>
        </div>
      </aside>
      <main className={`v2-main v2-view-${view}`} id="contenido-principal">
        <header className="v2-topbar">
          <div>
            <span className="v2-kicker">PLANTA BARRANQUILLA</span>
            <h1>{title}</h1>
            <p>{description}</p>
          </div>
          <div className="v2-top-actions">
            <label>
              Periodo
              <select
                aria-label="Periodo de trabajo"
                value={month}
                onChange={(event) => onMonthChange(Number(event.target.value))}
              >
                {MONTHS.map((label, index) => (
                  <option key={label} value={index + 1}>
                    {label} {year}
                  </option>
                ))}
              </select>
            </label>
            <div className={`v2-health ${health}`} role="status">
              <i />
              {health === "ok"
                ? "Base conectada"
                : health === "error"
                  ? "Sin conexión"
                  : "Conectando..."}
            </div>
          </div>
        </header>

        {view === "pending" && <PendingDataIndicators year={year} month={month} />}
        {view === "imports" && <MaintenanceBaseUpload year={year} month={month} />}
        {children}
        {view === "technicians" && <ShiftSettings year={year} month={month} />}
      </main>
    </div>
  );
}
