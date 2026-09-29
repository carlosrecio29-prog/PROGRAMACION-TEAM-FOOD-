import { useEffect, useState } from "react";
import MaintenanceBaseUpload from "../components/MaintenanceBaseUpload";
import PendingDataIndicators from "../components/PendingDataIndicators";
import ShiftSettings from "../components/ShiftSettings";
import companyLogo from "../assets/cekLogoData";
import "../admin-improvements.css";
import { MONTHS, NAV_GROUPS, VIEW_META } from "./navigation";

function TeamFoodsMark() {
  return (
    <div className="v2-team-mark" aria-label="Team Foods">
      <svg viewBox="0 0 52 52" aria-hidden="true">
        <path className="drop-a" d="M26 4c7 7 11 12 11 18a11 11 0 1 1-22 0c0-6 4-11 11-18Z" />
        <path className="drop-b" d="M44 20c1 10-1 17-6 21a10 10 0 0 1-13-15c4-4 10-5 19-6Z" />
        <path className="drop-c" d="M8 20c9 1 15 2 19 6a10 10 0 0 1-13 15c-5-4-7-11-6-21Z" />
      </svg>
      <span>
        <small>ALIANZA</small>
        <b>TEAM</b>
      </span>
    </div>
  );
}


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
  const activeGroup = NAV_GROUPS.find(
    (group) => group.label !== "Inicio" && group.items.some((item) => item.id === view),
  )?.label || "";
  const [openGroup, setOpenGroup] = useState(activeGroup);

  useEffect(() => {
    if (activeGroup) setOpenGroup(activeGroup);
  }, [activeGroup]);

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
          {NAV_GROUPS.map((group) => {
            const isHome = group.label === "Inicio";
            const isOpen = isHome || openGroup === group.label;
            const hasActiveItem = group.items.some((item) => item.id === view);
            return (
              <div
                className={`v2-nav-group${isOpen ? " open" : ""}${hasActiveItem ? " current" : ""}`}
                key={group.label}
              >
                {isHome ? (
                  <span className="v2-nav-label">{group.label}</span>
                ) : (
                  <button
                    type="button"
                    className="v2-nav-group-toggle"
                    aria-expanded={isOpen}
                    aria-controls={`nav-group-${group.label.toLowerCase().replace(/[^a-z0-9]+/g, "-")}`}
                    onClick={() => setOpenGroup((current) => current === group.label ? "" : group.label)}
                  >
                    <span>{group.label}</span>
                    <b aria-hidden="true">⌄</b>
                  </button>
                )}
                <div
                  className="v2-nav-items"
                  id={`nav-group-${group.label.toLowerCase().replace(/[^a-z0-9]+/g, "-")}`}
                  hidden={!isOpen}
                >
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
              </div>
            );
          })}
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
        {view === "summary" ? (
          <header className="v2-dashboard-header">
            <div className="v2-dashboard-brand">
              <TeamFoodsMark />
              <div className="v2-dashboard-title">
                <span>OPERACIÓN DE MANTENIMIENTO</span>
                <h1>Panel de control</h1>
                <p>Planta Barranquilla · Gestión de mantenimiento</p>
                <small>Planeación · Programación · Cierre · Seguimiento</small>
              </div>
            </div>
            <div className="v2-dashboard-meta">
              <label className="v2-dashboard-period">
                <span>PERÍODO</span>
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
              <span className="v2-pilot-badge">PILOTO ACTIVO</span>
              <small className="v2-dashboard-provider">Gestión técnica · C.E.K Global Inspection</small>
            </div>
          </header>
        ) : (
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
        )}

        {view === "pending" && <PendingDataIndicators year={year} month={month} />}
        {view === "imports" && <MaintenanceBaseUpload year={year} month={month} />}
        {children}
        {view === "technicians" && <ShiftSettings year={year} month={month} />}
      </main>
    </div>
  );
}
