/**
 * PanelEstado — componente React para el panel de inicio del conductor.
 *
 * Reemplaza el bloque "Estado del vehículo" de inicio_usuarios.html.
 * Sin JSX, sin build step: usa React.createElement directamente.
 * Esto permite entender cómo funciona React por debajo antes de agregar
 * JSX con Vite en fases posteriores.
 *
 * Flujo:
 *   mount → fetch /api/conductor/dashboard/ (estado completo)
 *         → render según puede_estacionar / estacionamientos_activos
 *         → polling cada 30s a /api/conductor/estacionamientos/activos/ (solo timers)
 */

"use strict";

// Alias corto para React.createElement — habitual en código sin JSX
const ce = React.createElement;
const { useState, useEffect } = React;

// ── Helpers ──────────────────────────────────────────────────────────────────

function pad(n) {
  return String(n).padStart(2, "0");
}

/** Formatea milisegundos restantes en "MM:SS" o "HH:MM:SS" */
function formatearCuentaRegresiva(ms) {
  if (ms <= 0) return null; // indica vencido
  const totalSeg = Math.floor(ms / 1000);
  const horas    = Math.floor(totalSeg / 3600);
  const minutos  = Math.floor((totalSeg % 3600) / 60);
  const seg      = totalSeg % 60;
  if (horas > 0) return `${pad(horas)}:${pad(minutos)}:${pad(seg)}`;
  return `${pad(minutos)}:${pad(seg)}`;
}

/** Formatea un Unix timestamp (segundos) como "HH:MM" en hora local */
function formatearHora(unixSeg) {
  const d = new Date(unixSeg * 1000);
  return pad(d.getHours()) + ":" + pad(d.getMinutes());
}

// ── ContadorRegresivo ─────────────────────────────────────────────────────────
/**
 * Muestra MM:SS con colores (verde → amarillo al quedar < 5 min → rojo al vencer).
 * Se auto-actualiza cada segundo con setInterval.
 * Recibe hora_fin_unix (segundos) desde la API — no calcula nada con duraciones.
 */
function ContadorRegresivo({ horaFinUnix }) {
  const [restanteMs, setRestanteMs] = useState(horaFinUnix * 1000 - Date.now());

  useEffect(() => {
    const id = setInterval(() => {
      setRestanteMs(horaFinUnix * 1000 - Date.now());
    }, 1000);
    // cleanup: cancela el interval cuando el componente se desmonta o cambia horaFinUnix
    return () => clearInterval(id);
  }, [horaFinUnix]);

  const texto    = formatearCuentaRegresiva(restanteMs);
  const vencido  = texto === null;
  const pocaTiempo = !vencido && restanteMs < 5 * 60 * 1000; // menos de 5 min

  const color = vencido     ? "var(--color-danger)"
              : pocaTiempo  ? "var(--color-warning)"
              : "var(--color-primary)";

  return ce("span", { style: { color, fontWeight: 700, fontSize: "1.1rem" } },
    vencido ? "⏰ Tiempo vencido" : texto
  );
}

// ── CardUnEstacionamiento ─────────────────────────────────────────────────────
/**
 * Card para un solo estacionamiento activo (layout completo con patente, hora,
 * cuenta regresiva y botón Extender).
 */
function CardUnEstacionamiento({ est, urlEstacionar }) {
  const horaFinStr = formatearHora(est.hora_fin_unix);
  const restanteMs = est.hora_fin_unix * 1000 - Date.now();
  const pocaTiempo = restanteMs > 0 && restanteMs < 5 * 60 * 1000;

  return ce("div", null,
    // Fila: patente + botón Extender
    ce("div", {
      style: {
        display: "flex", alignItems: "center",
        justifyContent: "space-between", flexWrap: "wrap",
        gap: "0.5rem", marginTop: "0.5rem",
      }
    },
      ce("div", null,
        ce("p", { style: { fontSize: "1.5rem", fontWeight: 800, letterSpacing: "2px", margin: "0 0 0.15rem" } },
          est.patente
        ),
        ce("p", { style: { fontSize: "0.95rem", color: "var(--color-text-muted)", margin: 0 } },
          "hasta las ",
          ce("strong", null, horaFinStr),
          " — ",
          ce(ContadorRegresivo, { horaFinUnix: est.hora_fin_unix })
        )
      ),
      ce("a", { className: "btn btn-outline", href: est.url_renovar }, "🔄 Extender")
    ),

    // Aviso si queda poco tiempo (< 5 min)
    pocaTiempo && ce("div", {
      className: "alert alert-warning",
      style: { marginTop: "0.5rem", display: "flex", alignItems: "center", gap: "0.5rem" },
    }, ce("strong", null, "¡Quedan menos de 5 minutos! Extendé ahora.")),

    // Subcuadra
    est.subcuadra && ce("p", {
      style: { fontSize: "0.82rem", color: "var(--color-text-muted)", margin: "0.6rem 0 0.75rem" }
    }, "📍 " + est.subcuadra),

    // Botón para estacionar otro vehículo
    ce("div", { style: { display: "flex", gap: "0.5rem", flexWrap: "wrap", alignItems: "center" } },
      ce("a", { className: "btn", href: urlEstacionar }, "+ Estacionar otro vehículo")
    )
  );
}

// ── ListaEstacionamientos ─────────────────────────────────────────────────────
/**
 * Lista compacta para cuando hay múltiples vehículos estacionados al mismo tiempo.
 */
function ListaEstacionamientos({ estacionamientos }) {
  return ce("div", { style: { display: "flex", flexDirection: "column", gap: "0.4rem", marginTop: "0.5rem" } },
    ...estacionamientos.map(est =>
      ce("div", {
        key: est.id,
        style: {
          display: "flex", alignItems: "center",
          justifyContent: "space-between",
          padding: "0.35rem 0",
          borderBottom: "1px solid var(--color-border)",
          flexWrap: "wrap", gap: "0.4rem",
        }
      },
        ce("div", null,
          ce("strong", { style: { letterSpacing: "1px" } }, est.patente),
          ce("span", { style: { fontSize: "1rem", fontWeight: 700, marginLeft: "0.5rem" } },
            "hasta " + formatearHora(est.hora_fin_unix)
          ),
          ce("span", { style: { marginLeft: "0.5rem" } },
            ce(ContadorRegresivo, { horaFinUnix: est.hora_fin_unix })
          )
        ),
        ce("a", {
          className: "btn btn-outline",
          href: est.url_renovar,
          style: { fontSize: "0.78rem", padding: "0.2rem 0.5rem" },
        }, "🔄 Extender")
      )
    )
  );
}

// ── PanelEstado ───────────────────────────────────────────────────────────────
/**
 * Componente raíz. Gestiona:
 *   - Carga inicial: GET /api/conductor/dashboard/
 *   - Polling cada 30s: GET /api/conductor/estacionamientos/activos/
 *   - Estados: cargando / error / fuera de horario / con estac. activos / sin estac.
 */
function PanelEstado({ urlDashboard, urlEstacionamientosActivos, urlEstacionar, urlRecargar }) {
  const [estado, setEstado] = useState(null); // null = todavía cargando
  const [error,  setError]  = useState(null);

  // Carga inicial: estado completo del conductor
  useEffect(() => {
    fetch(urlDashboard)
      .then(r => {
        if (!r.ok) throw new Error(`HTTP ${r.status}`);
        return r.json();
      })
      .then(data => setEstado(data))
      .catch(e => {
        console.error("[PanelEstado] error cargando dashboard:", e);
        setError("No pudimos cargar el estado. Recargá la página.");
      });
  }, []);

  // Polling: actualiza solo los estacionamientos activos (el resto no cambia seguido)
  useEffect(() => {
    if (!estado) return; // esperar a que cargue la primera vez
    const id = setInterval(() => {
      fetch(urlEstacionamientosActivos)
        .then(r => r.json())
        .then(data => {
          setEstado(prev => prev
            ? { ...prev, estacionamientos_activos: data.estacionamientos }
            : prev
          );
        })
        .catch(() => {}); // error de red en polling: silencioso, el usuario no necesita saberlo
    }, 30_000); // cada 30 segundos
    return () => clearInterval(id);
  }, [!!estado]); // solo se activa cuando estado cambia de null → algo

  // ── Render: cargando ─────────────────────────────────────────────────────
  if (error) {
    return ce("div", { className: "card" },
      ce("h3", null, "🚗 Estado del vehículo"),
      ce("div", { className: "alert alert-danger", style: { margin: 0 } }, error)
    );
  }

  if (!estado) {
    return ce("div", { className: "card" },
      ce("h3", null, "🚗 Estado del vehículo"),
      ce("p", { style: { color: "var(--color-text-muted)", margin: 0 } }, "Cargando…")
    );
  }

  // ── Render: fuera de horario ─────────────────────────────────────────────
  if (!estado.puede_estacionar) {
    return ce("div", { className: "card" },
      ce("h3", null, "🚗 Estado del vehículo"),
      ce("div", { className: "alert alert-warning", style: { margin: 0 } },
        "⏰ " + estado.mensaje_horario
      )
    );
  }

  const activos = estado.estacionamientos_activos || [];

  // ── Render: con estacionamientos activos ────────────────────────────────
  if (activos.length > 0) {
    return ce("div", { className: "card" },
      ce("h3", null, "🚗 Estado del vehículo"),
      ce("div", { className: "status-ok" },
        "🟢 " + (activos.length > 1
          ? `${activos.length} vehículos activos`
          : "Estacionamiento activo")
      ),
      activos.length === 1
        ? ce(CardUnEstacionamiento, { est: activos[0], urlEstacionar })
        : ce(ListaEstacionamientos, { estacionamientos: activos })
    );
  }

  // ── Render: sin estacionamiento activo ──────────────────────────────────
  return ce("div", { className: "card" },
    ce("h3", null, "🚗 Estado del vehículo"),
    ce("div", { className: "status-warn" }, "🟡 Sin estacionamiento activo"),

    estado.saldo_insuficiente
      ? ce("div", null,
          ce("div", {
            className: "alert alert-warning",
            style: { margin: "0.75rem 0 0.5rem", fontSize: "0.9rem" },
          },
            "⚠️ Tu saldo no alcanza para 1 hora",
            estado.costo_hora_min
              ? ` ($${Number(estado.costo_hora_min).toFixed(2)})`
              : "",
            ". Recargá antes de estacionar."
          ),
          ce("div", { style: { display: "flex", gap: "0.5rem", flexWrap: "wrap", marginTop: "0.4rem" } },
            ce("a", { className: "btn btn-primary", href: urlRecargar }, "💳 Recargar saldo"),
            ce("a", { className: "btn btn-outline", href: urlEstacionar, style: { fontSize: "0.85rem" } },
              "Estacionar igual"
            )
          )
        )
      : ce("a", { className: "btn", href: urlEstacionar }, "🛵 Estacionar 🚗")
  );
}

// ── Mount ─────────────────────────────────────────────────────────────────────
/**
 * Punto de entrada: busca el div #panel-estado-react y monta el componente.
 * Las URLs se pasan como data-* para no hardcodearlas en el JS
 * (Django reverse() garantiza que siempre sean correctas).
 */
(function montarPanelEstado() {
  const mountEl = document.getElementById("panel-estado-react");
  if (!mountEl) return;

  const urlDashboard              = mountEl.dataset.urlDashboard;
  const urlEstacionamientosActivos = mountEl.dataset.urlEstacionamientosActivos;
  const urlEstacionar             = mountEl.dataset.urlEstacionar;
  const urlRecargar               = mountEl.dataset.urlRecargar;

  const root = ReactDOM.createRoot(mountEl);
  root.render(
    ce(PanelEstado, { urlDashboard, urlEstacionamientosActivos, urlEstacionar, urlRecargar })
  );
})();
