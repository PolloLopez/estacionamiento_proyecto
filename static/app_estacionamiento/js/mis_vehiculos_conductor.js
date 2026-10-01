/**
 * MisVehiculos — componente React para la sección "Mis vehículos" del conductor.
 *
 * Lee los datos de vehiculos[] que ya vienen en la respuesta del dashboard
 * (GET /api/conductor/dashboard/) — no hace un fetch propio.
 * Los datos llegan como prop desde el mount point vía data-*.
 *
 * Los botones de acción (agregar, historial, infracciones) siguen siendo
 * links Django — no hay POST ni lógica de negocio en este componente.
 *
 * Fallback: si React no monta, el HTML Django original sigue visible.
 */

"use strict";

const ce = React.createElement;

// ── FilaVehiculo ──────────────────────────────────────────────────────────────
/**
 * Una fila por vehículo con estado, patente, tipo y botones de acción.
 */
function FilaVehiculo({ vehiculo, urlHistorialBase, urlInfraccionesBase, esUltimo }) {
  const icono = vehiculo.tipo === "moto" ? "🛵" : "🚗";

  // Badge de estado: primero estacionado, después abono, si no nada
  function BadgeEstado() {
    if (vehiculo.tiene_estacionamiento_activo) {
      return ce("span", {
        title: "Estacionado ahora",
        style: { fontSize: "1rem" },
      }, "🟢");
    }
    if (vehiculo.tiene_abono_activo) {
      return ce("span", {
        title: "Abono activo este mes",
        style: { fontSize: "1rem" },
      }, "🔵");
    }
    return ce("span", {
      title: "Sin estacionamiento activo",
      style: { fontSize: "1rem", opacity: "0.35" },
    }, "⚪");
  }

  return ce("div", {
    style: {
      display: "flex", alignItems: "center", justifyContent: "space-between",
      flexWrap: "wrap", gap: "0.5rem", padding: "0.5rem 0",
      borderBottom: esUltimo ? "none" : "1px solid var(--color-border)",
    }
  },
    // Lado izquierdo: estado + datos
    ce("div", { style: { display: "flex", alignItems: "center", gap: "0.5rem", flexWrap: "wrap" } },
      ce(BadgeEstado),
      ce("strong", { style: { letterSpacing: "1px" } }, vehiculo.patente),
      ce("span", { style: { color: "var(--color-text-muted)", fontSize: "0.88rem" } },
        icono + " " + vehiculo.tipo_display
      ),
      vehiculo.infracciones_pendientes > 0 && ce("span", {
        style: { fontSize: "0.8rem", color: "var(--color-danger, #c0392b)", fontWeight: "700" },
        title: vehiculo.infracciones_pendientes + " infracción(es) pendiente(s)",
      }, "⚠️ " + vehiculo.infracciones_pendientes),
      vehiculo.exento && ce("span", {
        style: {
          fontSize: "0.75rem", background: "var(--color-primary)", color: "#fff",
          borderRadius: "4px", padding: "0.1rem 0.35rem",
        },
        title: "Exento ANDIS/SIA",
      }, "🏷️ exento")
    ),

    // Lado derecho: botones (links Django)
    ce("div", { style: { display: "flex", gap: "0.35rem" } },
      ce("a", {
        href: urlHistorialBase + "?patente=" + encodeURIComponent(vehiculo.patente),
        className: "btn btn-outline",
        style: { fontSize: "0.78rem", padding: "0.2rem 0.55rem" },
        title: "Historial de estacionamientos",
      }, "📜"),
      ce("a", {
        href: urlInfraccionesBase + "?patente=" + encodeURIComponent(vehiculo.patente),
        className: "btn btn-outline",
        style: { fontSize: "0.78rem", padding: "0.2rem 0.55rem" },
        title: "Ver infracciones",
      }, "⚠️")
    )
  );
}

// ── MisVehiculos ──────────────────────────────────────────────────────────────
/**
 * Componente raíz. Recibe los vehículos ya cargados (sin fetch propio).
 * urlHistorialBase y urlInfraccionesBase son las URLs base de Django (sin patente).
 */
function MisVehiculos({ vehiculos, urlHistorialBase, urlInfraccionesBase, urlAgregarVehiculo }) {
  if (!vehiculos || vehiculos.length === 0) return null;

  return ce("div", { className: "card", style: { marginTop: "1rem" } },
    ce("h3", { style: { marginBottom: "0.75rem" } }, "🚗 Mis vehículos"),

    ce("div", {
      style: {
        display: "flex", flexDirection: "column", gap: "0",
        maxHeight: "215px", overflowY: "auto",
      }
    },
      ...vehiculos.map((v, i) =>
        ce(FilaVehiculo, {
          key: v.id,
          vehiculo: v,
          urlHistorialBase,
          urlInfraccionesBase,
          esUltimo: i === vehiculos.length - 1,
        })
      )
    ),

    ce("div", { style: { marginTop: "0.6rem" } },
      ce("a", {
        href: urlAgregarVehiculo,
        className: "btn btn-outline",
        style: { fontSize: "0.82rem" },
      }, "+ Agregar vehículo")
    )
  );
}

// ── Mount ─────────────────────────────────────────────────────────────────────
/**
 * Hace fetch al dashboard para obtener vehiculos[], luego monta el componente.
 * Oculta el fallback Django al montar correctamente.
 */
(function montarMisVehiculos() {
  const mountEl = document.getElementById("mis-vehiculos-react");
  if (!mountEl) return;

  const urlDashboard      = mountEl.dataset.urlDashboard;
  const urlHistorialBase  = mountEl.dataset.urlHistorialBase;
  const urlInfraccionesBase = mountEl.dataset.urlInfraccionesBase;
  const urlAgregarVehiculo  = mountEl.dataset.urlAgregarVehiculo;

  fetch(urlDashboard)
    .then(r => {
      if (!r.ok) throw new Error("HTTP " + r.status);
      return r.json();
    })
    .then(data => {
      const vehiculos = data.vehiculos || [];
      if (vehiculos.length === 0) return; // sin vehículos: dejar el fallback Django

      // Ocultar fallback Django
      const fallback = document.getElementById("mis-vehiculos-fallback-django");
      if (fallback) fallback.style.display = "none";

      const root = ReactDOM.createRoot(mountEl);
      root.render(
        ce(MisVehiculos, { vehiculos, urlHistorialBase, urlInfraccionesBase, urlAgregarVehiculo })
      );
    })
    .catch(e => {
      // Error de red: el fallback Django sigue visible, no hay mensaje de error al usuario
      console.error("[MisVehiculos] error cargando dashboard:", e);
    });
})();
