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

// ── ModalRenovar ──────────────────────────────────────────────────────────────
/**
 * Modal inline para extender un estacionamiento activo sin salir del panel.
 *
 * Flujo:
 *   1. Se abre al hacer clic en "🔄 Extender"
 *   2. Llama a GET /api/conductor/estacionamiento/<id>/opciones-renovar/ para traer opciones y saldo
 *   3. El conductor selecciona una opción
 *   4. POST /api/conductor/estacionamiento/<id>/renovar/ con las horas elegidas
 *   5. Al confirmar: llama a onRenovado(nuevaHoraFinUnix) para actualizar el panel sin recargar
 *
 * Por qué inline y no una página separada:
 *   El conductor que extiende ya está viendo el panel con el timer contando.
 *   Salir a otra página rompe el contexto visual. El modal mantiene todo en la misma pantalla.
 */
function ModalRenovar({ estId, urlOpcionesBase, urlRenovarBase, onRenovado, onCerrar }) {
  const [fase,    setFase]    = useState("cargando"); // cargando | eligiendo | confirmando | error
  const [datos,   setDatos]   = useState(null);
  const [opcion,  setOpcion]  = useState(null); // la opción seleccionada { label, horas, costo }
  const [mensaje, setMensaje] = useState(null);

  // Arma la URL reemplazando el 0 placeholder por el id real
  function urlConId(base) {
    return base.replace("/0/", "/" + estId + "/");
  }

  // Carga las opciones al montar
  useEffect(() => {
    fetch(urlConId(urlOpcionesBase))
      .then(r => {
        if (!r.ok) throw new Error("HTTP " + r.status);
        return r.json();
      })
      .then(data => {
        setDatos(data);
        setFase(data.opciones.length === 0 ? "sin-opciones" : "eligiendo");
      })
      .catch(() => {
        setFase("error");
        setMensaje("No pudimos cargar las opciones. Intentá de nuevo.");
      });
  }, []);

  function confirmar() {
    if (!opcion) return;
    setFase("confirmando");

    fetch(urlConId(urlRenovarBase), {
      method: "POST",
      headers: {
        "Content-Type": "application/json",
        // Django requiere CSRF token en POST; lo leemos de la cookie
        "X-CSRFToken": (document.cookie.match(/csrftoken=([^;]+)/) || [])[1] || "",
      },
      body: JSON.stringify({ horas_extra: opcion.horas }),
    })
      .then(r => r.json())
      .then(data => {
        if (data.ok) {
          onRenovado(data.nueva_hora_fin_unix);
        } else {
          setFase("error");
          setMensaje(data.error || "Error al renovar.");
        }
      })
      .catch(() => {
        setFase("error");
        setMensaje("Error de red. Intentá de nuevo.");
      });
  }

  // ── Estilos del overlay ─────────────────────────────────────────────────
  const overlayStyle = {
    position: "fixed", inset: "0",
    background: "rgba(0,0,0,0.55)",
    display: "flex", alignItems: "flex-end", justifyContent: "center",
    zIndex: "1000",
  };
  const panelStyle = {
    background: "var(--color-surface)",
    borderRadius: "16px 16px 0 0",
    padding: "0 1.25rem 2.5rem",
    width: "100%", maxWidth: "480px",
    boxShadow: "0 -4px 32px rgba(0,0,0,0.2)",
  };

  return ce("div", { style: overlayStyle, onClick: onCerrar },
    ce("div", { style: panelStyle, onClick: e => e.stopPropagation() },

      // Barra de arrastre visual (solo decorativa, indica que es un bottom sheet)
      ce("div", { style: { display: "flex", justifyContent: "center", padding: "0.75rem 0 0.25rem" } },
        ce("div", { style: { width: "40px", height: "4px", borderRadius: "2px", background: "var(--color-border)" } })
      ),

      // Header del modal
      ce("div", {
        style: {
          display: "flex", justifyContent: "space-between", alignItems: "center",
          padding: "0.75rem 0 1rem",
          borderBottom: "1px solid var(--color-border)",
          marginBottom: "1.25rem",
        }
      },
        ce("span", { style: { fontSize: "1.1rem", fontWeight: 700 } }, "🔄 Extender estacionamiento"),
        ce("button", {
          type: "button",
          onClick: onCerrar,
          style: {
            background: "var(--color-surface-2, #f3f4f6)",
            border: "none", borderRadius: "50%",
            width: "32px", height: "32px",
            fontSize: "1.1rem", cursor: "pointer",
            color: "var(--color-text-muted)",
            display: "flex", alignItems: "center", justifyContent: "center",
          },
        }, "×")
      ),

      // ── Estado: cargando ────────────────────────────────────────────────
      fase === "cargando" && ce("p", {
        style: { color: "var(--color-text-muted)", textAlign: "center", padding: "1rem 0" }
      }, "Cargando opciones…"),

      // ── Estado: sin opciones ────────────────────────────────────────────
      fase === "sin-opciones" && ce("div", { className: "alert alert-warning" },
        "⏰ Tu estacionamiento ya cubre hasta el cierre del horario. No hace falta extenderlo."
      ),

      // ── Estado: error ───────────────────────────────────────────────────
      fase === "error" && ce("div", { className: "alert alert-danger" }, mensaje),

      // ── Estado: eligiendo ───────────────────────────────────────────────
      (fase === "eligiendo" || fase === "confirmando") && datos && ce("div", null,

        // Saldo disponible
        ce("div", {
          style: {
            display: "flex", justifyContent: "space-between",
            marginBottom: "1rem", padding: "0.75rem 1rem",
            background: "var(--color-surface-2)", borderRadius: "var(--radius-sm)",
          }
        },
          ce("span", { style: { color: "var(--color-text-muted)", fontSize: "0.9rem" } }, "Saldo disponible"),
          ce("strong", { style: { color: "var(--color-primary)" } }, "$" + Number(datos.saldo).toFixed(2))
        ),

        // Botones de opciones
        ce("div", { style: { display: "flex", flexWrap: "wrap", gap: "0.5rem", marginBottom: "1rem" } },
          ...datos.opciones.map(op =>
            ce("button", {
              key: op.horas,
              type: "button",
              className: "btn " + (opcion && opcion.horas === op.horas ? "btn-success" : "btn-outline"),
              disabled: datos.saldo < op.costo,
              onClick: () => setOpcion(op),
              style: { fontSize: "1rem", padding: "0.6rem 1rem", fontWeight: "600" },
              title: datos.saldo < op.costo ? "Saldo insuficiente" : "",
            }, op.label)
          )
        ),

        // Preview del costo seleccionado
        opcion && ce("div", {
          className: "alert alert-success",
          style: { marginBottom: "1rem" }
        },
          "+" + opcion.label + " · Costo: $" + Number(opcion.costo).toFixed(2)
        ),

        // Botón confirmar
        ce("button", {
          type: "button",
          className: "btn",
          style: { width: "100%", fontSize: "1rem", padding: "0.75rem" },
          disabled: !opcion || fase === "confirmando",
          onClick: confirmar,
        }, fase === "confirmando" ? "Procesando…" : "✅ Confirmar extensión")
      )
    )
  );
}


// ── CardUnEstacionamiento ─────────────────────────────────────────────────────
/**
 * Card para un solo estacionamiento activo (layout completo con patente, hora,
 * cuenta regresiva y botón Extender).
 *
 * onExtender: callback que abre el modal de renovar en el componente padre (PanelEstado).
 * Así el modal vive en el nivel raíz y no se apila dentro de un card anidado.
 */
function CardUnEstacionamiento({ est, urlEstacionar, onExtender }) {
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
      // Botón abre el modal inline en lugar de navegar a otra página
      ce("button", {
        type: "button",
        className: "btn btn-outline",
        onClick: () => onExtender(est.id),
      }, "🔄 Extender")
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
 * onExtender: callback que abre el modal de renovar (igual que en CardUnEstacionamiento).
 */
function ListaEstacionamientos({ estacionamientos, onExtender }) {
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
        ce("button", {
          type: "button",
          className: "btn btn-outline",
          onClick: () => onExtender(est.id),
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
function PanelEstado({ urlDashboard, urlEstacionamientosActivos, urlEstacionar, urlRecargar, urlOpcionesRenovarBase, urlRenovarBase }) {
  const [estado,          setEstado]          = useState(null); // null = todavía cargando
  const [error,           setError]           = useState(null);
  // idEstacionamientoModal: null = modal cerrado, número = id del estac. a extender
  const [idEstacionamientoModal, setIdEstacionamientoModal] = useState(null);

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
  // React.Fragment evita agregar un div wrapper sin clase que rompe el flujo visual.
  // El modal se renderiza por encima (fixed) y la card queda directamente en el DOM.
  if (activos.length > 0) {
    return ce(React.Fragment, null,
      // Modal de renovar (se renderiza por encima si idEstacionamientoModal está seteado)
      idEstacionamientoModal && ce(ModalRenovar, {
        estId:           idEstacionamientoModal,
        urlOpcionesBase: urlOpcionesRenovarBase,
        urlRenovarBase:  urlRenovarBase,
        onCerrar:        () => setIdEstacionamientoModal(null),
        // Al confirmar: actualiza la hora_fin del estacionamiento en el estado local
        // sin necesidad de recargar la página ni llamar al dashboard completo.
        onRenovado: (nuevaHoraFinUnix) => {
          setIdEstacionamientoModal(null);
          setEstado(prev => {
            if (!prev) return prev;
            return {
              ...prev,
              estacionamientos_activos: prev.estacionamientos_activos.map(e =>
                e.id === idEstacionamientoModal
                  ? { ...e, hora_fin_unix: nuevaHoraFinUnix }
                  : e
              ),
            };
          });
        },
      }),

      ce("div", { className: "card" },
        ce("h3", null, "🚗 Estado del vehículo"),
        ce("div", { className: "status-ok" },
          "🟢 " + (activos.length > 1
            ? activos.length + " vehículos activos"
            : "Estacionamiento activo")
        ),
        activos.length === 1
          ? ce(CardUnEstacionamiento, { est: activos[0], urlEstacionar, onExtender: setIdEstacionamientoModal })
          : ce(ListaEstacionamientos, { estacionamientos: activos, onExtender: setIdEstacionamientoModal })
      )
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
            // Muestra la duración mínima real del municipio, no "1 hora"
            "⚠️ Tu saldo no alcanza para ",
            estado.duracion_minima_min ? `${estado.duracion_minima_min} minutos` : "el mínimo",
            estado.costo_duracion_minima
              ? ` ($${Number(estado.costo_duracion_minima).toFixed(2)})`
              : "",
            ". Recargá antes de estacionar."
          ),
          ce("a", { className: "btn btn-primary", href: urlRecargar }, "💳 Recargar saldo")
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

  const urlDashboard               = mountEl.dataset.urlDashboard;
  const urlEstacionamientosActivos = mountEl.dataset.urlEstacionamientosActivos;
  const urlEstacionar              = mountEl.dataset.urlEstacionar;
  const urlRecargar                = mountEl.dataset.urlRecargar;
  const urlOpcionesRenovarBase     = mountEl.dataset.urlOpcionesRenovarBase;
  const urlRenovarBase             = mountEl.dataset.urlRenovarBase;

  const root = ReactDOM.createRoot(mountEl);
  root.render(
    ce(PanelEstado, {
      urlDashboard,
      urlEstacionamientosActivos,
      urlEstacionar,
      urlRecargar,
      urlOpcionesRenovarBase,
      urlRenovarBase,
    })
  );
})();
