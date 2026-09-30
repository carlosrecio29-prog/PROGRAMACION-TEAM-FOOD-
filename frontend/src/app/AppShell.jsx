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
    return (
      <svg {...common}>
        <path d="M3 3h8v8H3V3Zm10 0h8v8h-8V3ZM3 13h8v8H3v-8Zm10 0h8v8h-8v-8Z" />
      </svg>
    );
  }

  if (type === "Planificación") {
    return (
      <svg {...common}>
        <path d="M7 2h2v2h6V2h2v2h4v18H3V4h4V2Zm12 8H5v10h14V10ZM5 8h14V6H5v2Zm3 4h3v3H8v-3Zm5 0h3v3h-3v-3Z" />
      </svg>
    );
  }

  if (type === "Cierre") {
    return (
      <svg {...common}>
        <path d="M6 2h9l5 5v15H6V2Zm8 2v5h4l-4-5Zm-3 9-2 2 3 3 6-6-2-2-4 4-1-1Z" />
      </svg>
    );
  }

  if (type === "Backlog") {
    return (
      <svg {...common}>
        <path d="M5 3h14v4H5V3Zm0 7h14v4H5v-4Zm0 7h9v4H5v-4Zm11.5-.5H19V19h2.5v2H19v2.5h-2V21H14v-2h3v-2.5Z" />
      </svg>
    );
  }

  return (
    <svg {...common}>
      <path d="M12 8.2A3.8 3.8 0 1 1 12 15.8 3.8 3.8 0 0 1 12 8.2Zm8.8 2.3 1.7 1.1-1.4 2.5-2-.4c-.2.6-.5 1.1-.9 1.6l1.1 1.8-2.2 2.2-1.8-1.1c-.5.4-1 .7-1.6.9l-.4 2h-2.6l-.4-2c-.6-.2-1.1-.5-1.6-.9l-1.8 1.1-2.2-2.2 1.1-1.8c-.4-.5-.7-1-.9-1.6l-2 .4-1.4-2.5 1.7-1.1c0-.6 0-1.2.2-1.8L1.7 7l2.2-2.2 1.8 1.1c.5-.4 1-.7 1.6-.9l.4-2h2.6l.4 2c.6.2 1.1.5 1.6.9l1.8-1.1L16.3 7l-1.1 1.7c.2.6.2 1.2.2 1.8h5.4Z" />
    </svg>
  );
}

function SubmenuIcon({ id }) {
  const common = { viewBox: "0 0 24 24", "aria-hidden": "true", focusable: "false" };

  if (id === "advanceStops") {
    return (
      <svg {...common}>
        <path d="M7 2h2v2h6V2h2v2h4v18H3V4h4V2Zm12 8H5v10h14V10Zm-8 2h2v4h-2v-4Zm0 5h2v2h-2v-2Z" />
      </svg>
    );
  }

  if (id === "programming" || id === "programmingTest") {
    return (
      <svg {...common}>
        <path d="M4 3h16v18H4V3Zm2 5h12V5H6v3Zm0 2v9h12v-9H6Zm2 2h3v2H8v-2Zm5 0h3v2h-3v-2Zm-5 4h3v2H8v-2Zm5 0h3v2h-3v-2Z" />
      </svg>
    );
  }

  if (id === "pmp") {
    return (
      <svg {...common}>
        <path d="M6 2h9l4 4v16H6V2Zm8 2v4h4l-4-4ZM9 11h7v2H9v-2Zm0 4h7v2H9v-2Zm0 4h5v2H9v-2Z" />
      </svg>
    );
  }

  if (id === "operationExclusions") {
    return (
      <svg {...common}>
        <path d="M4 3h16v18H4V3Zm2 2v14h12V5H6Zm2 4h8v2H8V9Zm0 4h5v2H8v-2Zm7.6 1.2 1.4 1.4-4.6 4.6-2.4-2.4 1.4-1.4 1 1 3.2-3.2Z" />
      </svg>
    );
  }

  if (id === "closure") {
    return (
      <svg {...common}>
        <path d="M5 3h14v18H5V3Zm3 9 3 3 6-7 1.5 1.4L11 18l-4.5-4.5L8 12Z" />
      </svg>
    );
  }

  if (id === "monthly") {
    return (
      <svg {...common}>
        <path d="M4 20h16v2H4v-2Zm2-2V9h3v9H6Zm5 0V4h3v14h-3Zm5 0v-6h3v6h-3Z" />
      </svg>
    );
  }

  if (id === "indicators") {
    return (
      <svg {...common}>
        <path d="M3 21h19v-2H5V3H3v18Zm4-4h3v-6H7v6Zm5 0h3V7h-3v10Zm5 0h3V4h-3v13Z" />
      </svg>
    );
  }

  if (id === "backlog") {
    return (
      <svg {...common}>
        <path d="M5 3h14v3H5V3Zm0 6h14v3H5V9Zm0 6h9v3H5v-3Zm11 0h3v2h2v3h-2v2h-3v-2h-2v-3h2v-2Z" />
      </svg>
    );
  }

  if (id === "imports") {
    return (
      <svg {...common}>
        <path d="M5 2h10l4 4v16H5V2Zm9 2v4h4l-4-4ZM8 12h8v2H8v-2Zm0 4h8v2H8v-2Zm3-8h2v3h3v2h-3v3h-2v-3H8v-2h3V8Z" />
      </svg>
    );
  }

  if (id === "pending") {
    return (
      <svg {...common}>
        <path d="M4 4h10v2H6v12h12v-8h2v10H4V4Zm11.7 1.3 3 3L10 17H7v-3l8.7-8.7Zm1.4-1.4 1.2-1.2a1.5 1.5 0 0 1 2.1 0l.9.9a1.5 1.5 0 0 1 0 2.1l-1.2 1.2-3-3Z" />
      </svg>
    );
  }

  if (id === "technicians") {
    return (
      <svg {...common}>
        <path d="M8 3a4 4 0 1 1 0 8 4 4 0 0 1 0-8Zm8 2a3 3 0 1 1 0 6 3 3 0 0 1 0-6ZM2 20v-3c0-3 2.5-5 5.5-5h1C11.5 12 14 14 14 17v3H2Zm13-7.2c.3-.1.7-.1 1-.1h1c2.8 0 5 2.2 5 5V20h-6v-3c0-1.7-.4-3.1-1-4.2Z" />
      </svg>
    );
  }

  return (
    <svg {...common}>
      <path d="M5 5h14v14H5V5Z" />
    </svg>
  );
}

export default function AppShell({
  view,
  onNavigate,
  year,
  month,
  onMonthChange,
  health,
  onTechnicianDataChanged,
  indicators = {},
  children,
}) {
  const [title, description] = VIEW_META[view] || VIEW_META.summary;
  const activeGroup = NAV_GROUPS.find(
    (group) => group.label !== "Inicio" && group.items.some((item) => item.id === view),
  )?.label || "";
  const [openGroup, setOpenGroup] = useState(activeGroup);
  const [sidebarOpen, setSidebarOpen] = useState(false);
  const [hoverGroup, setHoverGroup] = useState("");

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
              <div
                className={`tf-side-section ${hasActiveItem ? "has-active" : ""}`}
                key={group.label}
                onMouseEnter={() => {
                  if (!sidebarOpen) setHoverGroup(group.label);
                }}
                onMouseLeave={() => {
                  if (!sidebarOpen) setHoverGroup("");
                }}
              >
                <button
                  type="button"
                  className={`tf-side-root tf-side-group ${hasActiveItem ? "is-active" : ""}`}
                  aria-expanded={sidebarOpen ? isOpen : hoverGroup === group.label}
                  title={!sidebarOpen ? group.label : undefined}
                  onClick={() => {
                    if (!sidebarOpen) {
                      setSidebarOpen(true);
                      setHoverGroup("");
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

                {!sidebarOpen && hoverGroup === group.label && (
                  <div className="tf-side-flyout" role="menu" aria-label={group.label}>
                    <div className="tf-side-flyout-head">
                      <span className="tf-side-flyout-icon"><SidebarIcon type={group.label} /></span>
                      <b>{group.label}</b>
                    </div>
                    <div className="tf-side-flyout-items">
                      {group.items.map((item) => (
                        <button
                          type="button"
                          key={item.id}
                          className={`tf-side-flyout-item ${view === item.id ? "is-active" : ""}`}
                          role="menuitem"
                          onClick={() => {
                            onNavigate(item.id);
                            setHoverGroup("");
                          }}
                        >
                          <span className="tf-side-flyout-item-icon"><SubmenuIcon id={item.id} /></span>
                          <span>{item.label}</span>
                          {item.indicator && Number(indicators[item.indicator]) > 0 && (
                            <i>{indicators[item.indicator]}</i>
                          )}
                        </button>
                      ))}
                    </div>
                  </div>
                )}

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
                        <span className="tf-side-subicon"><SubmenuIcon id={item.id} /></span>
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
          <header className="v2-topbar v2-module-topbar">
            <div className="v2-module-topbar-copy">
              <div className="v2-topbar-heading has-icon">
                <span className="v2-topbar-view-icon"><SubmenuIcon id={view} /></span>
                <div className="v2-topbar-title-copy">
                  <span className="v2-kicker">PLANTA BARRANQUILLA</span>
                  <h1>{title}</h1>
                  <p>{description}</p>
                </div>
              </div>
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
        {view === "technicians" && (
          <ShiftSettings
            year={year}
            month={month}
            onChanged={onTechnicianDataChanged}
          />
        )}
      </main>
    </div>
  );
}
