/**
 * HistorialConductor — componente React para el historial de estacionamientos.
 *
 * Reemplaza la lista Django de historial_estacionamientos.html.
 * Sin JSX, sin build step: usa React.createElement directamente (misma técnica que PanelEstado).
 *
 * Funcionalidades:
 *   - Paginación sin recarga de página (llama a la API al cambiar de página)
 *   - Expand/collapse por tarjeta (tap para ver el detalle)
 *   - Filtro por patente preservado como query param en la URL
 *   - Fallback: si React no monta, el HTML Django original sigue visible
 */

"use strict";

var ce = React.createElement;
const { useState, useEffect } = React;

// ── Helpers ──────────────────────────────────────────────────────────────────

function pad(n) {
  return String(n).padStart(2, "0");
}

/** Formatea Unix timestamp (segundos) como "dd/mm/yyyy" */
function formatearFecha(unixSeg) {
  const d = new Date(unixSeg * 1000);
  return pad(d.getDate()) + "/" + pad(d.getMonth() + 1) + "/" + d.getFullYear();
}

/** Formatea Unix timestamp (segundos) como "HH:MM" */
function formatearHora(unixSeg) {
  const d = new Date(unixSeg * 1000);
  return pad(d.getHours()) + ":" + pad(d.getMinutes());
}

/** Formatea Unix timestamp (segundos) como "dd/mm/yyyy HH:MM:SS" para el detalle */
function formatearFechaHora(unixSeg) {
  const d = new Date(unixSeg * 1000);
  return (
    pad(d.getDate()) + "/" + pad(d.getMonth() + 1) + "/" + d.getFullYear() +
    " " + pad(d.getHours()) + ":" + pad(d.getMinutes()) + ":" + pad(d.getSeconds())
  );
}

// ── IconoEstado ───────────────────────────────────────────────────────────────
/**
 * Emoji de estado: verde si activo, gris si finalizado, negro si otro.
 */
function IconoEstado({ estado }) {
  if (estado === "ACTIVO")     return ce("span", { style: { fontSize: "1.2rem" }, title: "Activo" }, "🟢");
  if (estado === "FINALIZADO") return ce("span", { style: { fontSize: "1.2rem", opacity: "0.5" }, title: "Finalizado" }, "⚪");
  return ce("span", { style: { fontSize: "1.2rem", opacity: "0.5" } }, "⚫");
}

// ── TarjetaEstacionamiento ────────────────────────────────────────────────────
/**
 * Una sola tarjeta del historial con expand/collapse al hacer tap.
 * Muestra resumen en el header y detalles expandibles debajo.
 */
function TarjetaEstacionamiento({ est, urlRenovar }) {
  const [expandido, setExpandido] = useState(false);

  const fechaStr      = formatearFecha(est.hora_inicio_unix);
  const inicioHoraStr = formatearHora(est.hora_inicio_unix);
  const finHoraStr    = formatearHora(est.hora_fin_unix);

  return ce("div", { className: "card", style: { padding: "0", overflow: "hidden" } },

    // Botón de resumen (tap para expandir)
    ce("button", {
      type: "button",
      onClick: () => setExpandido(v => !v),
      style: {
        width: "100%", background: "none", border: "none",
        cursor: "pointer", textAlign: "left", padding: "0.85rem 1rem",
      },
    },
      ce("div", { className: "page-header" },

        ce(IconoEstado, { estado: est.estado }),

        // Patente + fecha
        ce("div", { style: { flex: "1", minWidth: "0" } },
          ce("div", { style: { display: "flex", alignItems: "baseline", gap: "0.5rem", flexWrap: "wrap" } },
            ce("strong", { style: { letterSpacing: "1px" } }, est.patente),
            ce("span", { style: { color: "var(--color-text-muted)", fontSize: "0.82rem" } }, fechaStr)
          ),
          ce("div", { style: { fontSize: "0.88rem", color: "var(--color-text-muted)", marginTop: "0.1rem" } },
            inicioHoraStr + " → " + finHoraStr,
            est.estado === "ACTIVO"
              ? ce("span", { style: { color: "var(--color-success, green)" } }, " · Activo")
              : null,
            " · 📍 " + (est.subcuadra || "—")
          )
        ),

        // Costo + flecha
        ce("div", { style: { textAlign: "right", flexShrink: "0" } },
          ce("div", { style: { fontSize: "1.1rem", fontWeight: "800", color: "var(--color-primary)" } },
            "$" + Number(est.costo).toFixed(2)
          ),
          ce("div", { style: { fontSize: "0.75rem", color: "var(--color-text-muted)" } },
            expandido ? "cerrar ↑" : "ver más ›"
          )
        )
      )
    ),

    // Detalle expandible
    expandido && ce("div", {
      style: {
        borderTop: "1px solid var(--color-border)",
        padding: "1rem",
        background: "var(--color-surface)",
      }
    },
      ce("table", { style: { width: "100%", fontSize: "0.88rem", borderCollapse: "collapse" } },
        ce("tbody", null,
          ce("tr", null,
            ce("td", { style: { padding: "0.2rem 0.75rem 0.2rem 0", color: "var(--color-text-muted)" } }, "#"),
            ce("td", null, est.id)
          ),
          ce("tr", null,
            ce("td", { style: { padding: "0.2rem 0.75rem 0.2rem 0", color: "var(--color-text-muted)" } }, "Inicio"),
            ce("td", null, formatearFechaHora(est.hora_inicio_unix))
          ),
          ce("tr", null,
            ce("td", { style: { padding: "0.2rem 0.75rem 0.2rem 0", color: "var(--color-text-muted)" } }, "Fin"),
            ce("td", null,
              est.estado === "ACTIVO"
                ? ce("span", { style: { color: "var(--color-success, green)" } }, "Activo")
                : formatearFechaHora(est.hora_fin_unix)
            )
          ),
          ce("tr", null,
            ce("td", { style: { padding: "0.2rem 0.75rem 0.2rem 0", color: "var(--color-text-muted)" } }, "Zona"),
            ce("td", null, est.subcuadra || "—")
          ),
          ce("tr", null,
            ce("td", { style: { padding: "0.2rem 0.75rem 0.2rem 0", color: "var(--color-text-muted)" } }, "Duración"),
            ce("td", null, est.duracion_horas + "h")
          ),
          ce("tr", null,
            ce("td", { style: { padding: "0.2rem 0.75rem 0.2rem 0", color: "var(--color-text-muted)" } }, "Costo"),
            ce("td", null, ce("strong", null, "$" + Number(est.costo).toFixed(2)))
          ),
          ce("tr", null,
            ce("td", { style: { padding: "0.2rem 0.75rem 0.2rem 0", color: "var(--color-text-muted)" } }, "Estado"),
            ce("td", null, est.estado)
          )
        )
      ),
      // Botón extender solo si está activo (lleva a la página Django de renovar — en 4A todavía no es inline)
      est.estado === "ACTIVO" && ce("div", { style: { marginTop: "0.75rem" } },
        ce("a", {
          className: "btn btn-outline",
          // urlRenovarBase viene del template como "/estacionamiento/0/renovar/"
          // Reemplazamos el 0 placeholder por el id real del estacionamiento
          href: urlRenovar.replace("/0/", "/" + est.id + "/"),
          style: { fontSize: "0.88rem" },
        }, "🔄 Extender")
      )
    )
  );
}

// ── PaginadorHistorial ────────────────────────────────────────────────────────
/**
 * Navegación de páginas: Anterior / "Página X de Y" / Siguiente.
 */
function PaginadorHistorial({ pagina, totalPaginas, onCambiarPagina }) {
  if (totalPaginas <= 1) return null;

  return ce("nav", {
    style: {
      display: "flex", justifyContent: "center", alignItems: "center",
      gap: "0.5rem", marginTop: "1rem", flexWrap: "wrap",
    }
  },
    pagina > 1 && ce("button", {
      type: "button",
      className: "btn btn-outline",
      style: { fontSize: "0.9rem" },
      onClick: () => onCambiarPagina(pagina - 1),
    }, "← Anterior"),
    ce("span", { style: { color: "var(--color-text-muted)", fontSize: "0.9rem", lineHeight: "2.2rem" } },
      "Página " + pagina + " de " + totalPaginas
    ),
    pagina < totalPaginas && ce("button", {
      type: "button",
      className: "btn btn-outline",
      style: { fontSize: "0.9rem" },
      onClick: () => onCambiarPagina(pagina + 1),
    }, "Siguiente →")
  );
}

// ── HistorialConductor ────────────────────────────────────────────────────────
/**
 * Componente raíz del historial.
 * Carga la primera página al montar, luego llama a la API al cambiar de página.
 */
function HistorialConductor({ urlHistorial, urlRenovarBase, patenteFiltro }) {
  const [datos,    setDatos]    = useState(null);
  const [pagina,   setPagina]   = useState(1);
  const [cargando, setCargando] = useState(true);
  const [error,    setError]    = useState(null);

  // Carga cada vez que cambia la página
  useEffect(() => {
    setCargando(true);
    setError(null);

    let url = urlHistorial + "?pagina=" + pagina;
    if (patenteFiltro) url += "&patente=" + encodeURIComponent(patenteFiltro);

    fetch(url)
      .then(r => {
        if (!r.ok) throw new Error("HTTP " + r.status);
        return r.json();
      })
      .then(data => {
        setDatos(data);
        setCargando(false);
      })
      .catch(e => {
        console.error("[HistorialConductor] error:", e);
        setError("No pudimos cargar el historial. Recargá la página.");
        setCargando(false);
      });
  }, [pagina]);

  // ── Estado: cargando ──────────────────────────────────────────────────────
  if (cargando) {
    return ce("div", { style: { textAlign: "center", padding: "2rem 0", color: "var(--color-text-muted)" } },
      "Cargando historial…"
    );
  }

  // ── Estado: error ─────────────────────────────────────────────────────────
  if (error) {
    return ce("div", { className: "alert alert-danger" }, error);
  }

  // ── Estado: sin registros ─────────────────────────────────────────────────
  if (!datos || datos.estacionamientos.length === 0) {
    return ce("p", {
      style: { textAlign: "center", padding: "2rem 0", color: "var(--color-text-muted)" }
    }, "No tenés estacionamientos registrados todavía.");
  }

  // ── Estado: lista con resultados ──────────────────────────────────────────
  return ce("div", null,
    // Banner de filtro activo
    patenteFiltro && ce("div", {
      className: "alert alert-warning",
      style: { marginBottom: "1rem", display: "flex", justifyContent: "space-between", alignItems: "center", gap: "0.5rem", flexWrap: "wrap" },
    },
      ce("span", null, "🔍 Filtrando por ", ce("strong", null, patenteFiltro)),
      ce("a", {
        href: urlHistorial.replace("/api/conductor/historial/", "/mis_estacionamientos/"),
        className: "btn btn-outline",
        style: { fontSize: "0.82rem", padding: "0.2rem 0.6rem" },
      }, "Ver todos")
    ),

    // Lista de tarjetas
    ce("div", { style: { display: "flex", flexDirection: "column", gap: "0.6rem" } },
      ...datos.estacionamientos.map(est =>
        ce(TarjetaEstacionamiento, {
          key: est.id,
          est,
          urlRenovar: urlRenovarBase,
        })
      )
    ),

    // Paginador
    ce(PaginadorHistorial, {
      pagina:         datos.pagina,
      totalPaginas:   datos.total_paginas,
      onCambiarPagina: (nuevaPag) => {
        setPagina(nuevaPag);
        // Scroll al inicio de la lista para que el usuario vea los nuevos registros
        window.scrollTo({ top: 0, behavior: "smooth" });
      },
    })
  );
}

// ── Mount ─────────────────────────────────────────────────────────────────────
/**
 * Busca el div #historial-react y monta el componente.
 * Si el div no existe (React deshabilitado o error de carga), el HTML Django
 * original sigue visible — el template mantiene ambos y oculta uno al montar.
 */
(function montarHistorialConductor() {
  const mountEl = document.getElementById("historial-react");
  if (!mountEl) return;

  const urlHistorial   = mountEl.dataset.urlHistorial;
  const urlRenovarBase = mountEl.dataset.urlRenovarBase; // ej: /estacionamiento/__ID__/renovar/
  const patenteFiltro  = mountEl.dataset.patenteFiltro || "";

  // Ocultar el fallback Django ahora que React va a montar
  const fallback = document.getElementById("historial-fallback-django");
  if (fallback) fallback.style.display = "none";

  const root = ReactDOM.createRoot(mountEl);
  root.render(
    ce(HistorialConductor, { urlHistorial, urlRenovarBase, patenteFiltro })
  );
})();
