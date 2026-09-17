import { useEffect, useState } from "react";

function number(value) {
  const parsed = Number(value);
  return Number.isFinite(parsed) ? parsed : 0;
}

export default function PendingDataIndicators({ year, month }) {
  const [data, setData] = useState(null);
  const [error, setError] = useState("");

  useEffect(() => {
    let active = true;
    setError("");
    fetch(`/api/v2/dashboard?${new URLSearchParams({ year, month })}`)
      .then(async (response) => {
        if (!response.ok) {
          let message = `HTTP ${response.status}`;
          try {
            const body = await response.json();
            message = body.detail || message;
          } catch {}
          throw new Error(message);
        }
        return response.json();
      })
      .then((result) => {
        if (active) setData(result);
      })
      .catch((cause) => {
        if (active) setError(cause.message);
      });
    return () => {
      active = false;
    };
  }, [year, month]);

  if (error) return <div className="v2-error">{error}</div>;

  const pending = data?.pending || {};
  const summary = data?.summary || {};

  return (
    <section className="v2-pending-data-summary" aria-label="Indicadores de datos pendientes">
      <div className="v2-section-head">
        <div>
          <span className="v2-kicker">CONTROL DE DATOS</span>
          <h3>Pendientes antes de programar</h3>
          <p>Estos controles se gestionan aquí y ya no ocupan espacio en el Resumen Operativo.</p>
        </div>
      </div>
      <div className="v2-kpis v2-pending-kpis">
        <div className="warn">
          <span>Planes pendientes</span>
          <b>{number(pending.planes_pendientes)}</b>
          <small>planes usados en el PMP del mes</small>
        </div>
        <div className="warn">
          <span>Sin Nº personas</span>
          <b>{number(pending.planes_sin_personas)}</b>
          <small>planes que requieren completar dato</small>
        </div>
        <div className={number(summary.tecnicos_sin_especialidad) ? "warn" : "ok"}>
          <span>Técnicos sin especialidad</span>
          <b>{number(summary.tecnicos_sin_especialidad)}</b>
          <small>requieren completar especialidad</small>
        </div>
      </div>
    </section>
  );
}
