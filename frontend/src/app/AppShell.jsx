import { useEffect, useState } from "react";
import MaintenanceBaseUpload from "../components/MaintenanceBaseUpload";
import PendingDataIndicators from "../components/PendingDataIndicators";
import ShiftSettings from "../components/ShiftSettings";
import companyLogo from "../assets/cekLogoData";
import alianzaTeamLogo from "../assets/alianzaTeamLogoData";
import "../admin-improvements.css";
import { MONTHS, NAV_GROUPS, VIEW_META } from "./navigation";


function SidebarIcon({ type }) {
  const common = { viewBox: "0 0 24 24", "aria-hidden": "true", focusable: "false" };
  if (type === "Inicio") {
    return <svg {...common}><path d="M4 4h6v6H4V4Zm10 0h6v6h-6V4ZM4 14h6v6H4v-6Zm10 0h6v6h-6v-6Z" /></svg>;
  }
  if (type === "Planificación") {
    return <svg {...common}><path d="M14.7 5.3 18.7 9l-2 2-1.2-1.1-5.8 5.8 1.1 1.2-2 2-3.7-4 2-2 1.2 1.1 5.8-5.8L12.7 7l2-1.7ZM5 3h5v2H7v3H5V3Zm9 16h3v-3h2v5h-5v-2Z" /></svg>;
  }
  if (type === "Cierre") {
    return <svg {...common}><path d="M12 3a9 9 0 1 1-8.5 6H6a7 7 0 1 0 2-2.4L10 9H3V2l2.5 2.5A9 9 0 0 1 12 3Zm-1 5h2v5l4 2-1 1.8-5-2.8V8Z" /></svg>;
  }
  if (type === "Backlog") {
    return <svg {...common}><path d="M4 19h16v2H4v-2Zm1-3 3-4 3 2 4-6 4 3v3l-3.5-2.5-4 6-3-2L5 18v-2Z" /></svg>;
  }
  return <svg {...common}><path d="M12 8.3A3.7 3.7 0 1 1 12 15.7 3.7 3.7 0 0 1 12 8.3Zm9 2.8v1.8l-2 .7a7.4 7.4 0 0 1-.7 1.7l.9 1.9-1.3 1.3-1.9-.9a7.4 7.4 0 0 1-1.7.7l-.7 2h-1.8l-.7-2a7.4 7.4 0 0 1-1.7-.7l-1.9.9-1.3-1.3.9-1.9a7.4 7.4 0 0 1-.7-1.7l-2-.7v-1.8l2-.7c.2-.6.4-1.2.7-1.7l-.9-1.9 1.3-1.3 1.9.9c.5-.3 1.1-.5 1.7-.7l.7-2h1.8l.7 2c.6.2 1.2.4 1.7.7l1.9-.9 1.3 1.3-.9 1.9c.3.5.5 1.1.7 1.7l2 .7Z" /></svg>;
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
  const [sidebarOpen, setSidebarOpen] = useState(false);

  useEffect(() => {
    if (activeGroup) setOpenGroup(activeGroup);
  }, [activeGroup]);

  return (
    <div className={`v2-shell ${sidebarOpen ? "sidebar-open" : "sidebar-collapsed"}`}>
      <aside className="v2-sidebar" aria-label="Navegación principal">
        <div className="v2-sidebar-head">
          <button
            type="button"
            className="v2-sidebar-menu"
            aria-label={sidebarOpen ? "Contraer menú" : "Abrir menú"}
            aria-expanded={sidebarOpen}
            onClick={() => setSidebarOpen((open) => !open)}
          >
            <span />
            <span />
            <span />
          </button>
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
        </div>
        <nav className="tf-side-nav" aria-label="Flujos operativos">
          {NAV_GROUPS.map((group) => {
            const isHome = group.label === "Inicio";
            const isOpen = isHome || openGroup === group.label;
            const hasActiveItem = group.items.some((item) => item.id === view);
            const homeItem = isHome ? group.items[0] : null;

            if (isHome) {
              return (
                <div className="tf-side-section" key={group.label}>
                  <button
                    type="button"
                    className={`tf-side-root ${view === homeItem.id ? "is-active" : ""}`}
                    title={!sidebarOpen ? homeItem.label : undefined}
                    aria-current={view === homeItem.id ? "page" : undefined}
                    onClick={() => onNavigate(homeItem.id)}
                  >
                    <span className="tf-side-icon"><SidebarIcon type="Inicio" /></span>
                    <span className="tf-side-label">{homeItem.label}</span>
                  </button>
                </div>
              );
            }

            return (
              <div className={`tf-side-section ${hasActiveItem ? "has-active" : ""}`} key={group.label}>
                <button
                  type="button"
                  className={`tf-side-root tf-side-group ${hasActiveItem ? "is-active" : ""}`}
                  aria-expanded={isOpen}
                  title={!sidebarOpen ? group.label : undefined}
                  onClick={() => {
                    if (!sidebarOpen) {
                      setSidebarOpen(true);
                      setOpenGroup(group.label);
                      return;
                    }
                    setOpenGroup((current) => current === group.label ? "" : group.label);
                  }}
                >
                  <span className="tf-side-icon"><SidebarIcon type={group.label} /></span>
                  <span className="tf-side-label">{group.label}</span>
                  <span className={`tf-side-chevron ${isOpen ? "is-open" : ""}`} aria-hidden="true">›</span>
                </button>

                {sidebarOpen && isOpen && (
                  <div className="tf-side-submenu">
                    {group.items.map((item) => (
                      <button
                        type="button"
                        key={item.id}
                        className={`tf-side-subitem ${view === item.id ? "is-active" : ""}`}
                        aria-current={view === item.id ? "page" : undefined}
                        onClick={() => onNavigate(item.id)}
                      >
                        <span className="tf-side-code">{item.code}</span>
                        <span className="tf-side-sub-label">{item.label}</span>
                        {item.indicator && Number(indicators[item.indicator]) > 0 && (
                          <span className="tf-side-count" aria-label={`${indicators[item.indicator]} pendientes`}>
                            {indicators[item.indicator]}
                          </span>
                        )}
                      </button>
                    ))}
                  </div>
                )}
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
              <img className="v2-dashboard-logo" src={alianzaTeamLogo} alt="Alianza Team" />
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
