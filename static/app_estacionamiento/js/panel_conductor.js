// panel_conductor.js — Fase 7
// Componente unificado para el panel de inicio del conductor.
//
// Reemplaza panel_estado_conductor.js + mis_vehiculos_conductor.js:
//   - Un solo fetch a /api/conductor/dashboard/
//   - Polling cada 30s solo para los timers (estacionamientos activos)
//   - SaldoCard: saldo con mostrar/ocultar (privacidad en mobile)
//   - PanelEstadoConductor: estado del vehículo (activo / sin estac. / fuera horario)
//   - AbonoBanner: abono mensual activo si existe
//   - MisVehiculos: acordeón colapsable (cerrado por defecto)
//
// Sin JSX, sin build step. Variables con var, funciones nombradas.
// Mismo patrón que verificar_inspector.js (sesión 33).

(function () {
  "use strict";

  var ce        = React.createElement;
  var useState  = React.useState;
  var useEffect = React.useEffect;

  // ─── Helpers ──────────────────────────────────────────────────────────────

  function pad(n) {
    return String(n).padStart(2, "0");
  }

  // Formatea milisegundos restantes como "MM:SS" o "HH:MM:SS"
  function formatearCuentaRegresiva(ms) {
    if (ms <= 0) return null; // indica vencido
    var totalSeg = Math.floor(ms / 1000);
    var horas    = Math.floor(totalSeg / 3600);
    var minutos  = Math.floor((totalSeg % 3600) / 60);
    var seg      = totalSeg % 60;
    if (horas > 0) return pad(horas) + ":" + pad(minutos) + ":" + pad(seg);
    return pad(minutos) + ":" + pad(seg);
  }

  // Formatea Unix timestamp (segundos) como "HH:MM" en hora local
  function formatearHora(unixSeg) {
    var d = new Date(unixSeg * 1000);
    return pad(d.getHours()) + ":" + pad(d.getMinutes());
  }

  // Formatea número como pesos: 2500 → "$2.500,00"
  function formatearPesos(monto) {
    return "$" + Number(monto).toLocaleString("es-AR", { minimumFractionDigits: 2, maximumFractionDigits: 2 });
  }

  // Lee el CSRF token de la cookie de Django
  function obtenerCsrf() {
    var cookie = document.cookie.split(";").find(function (c) {
      return c.trim().startsWith("csrftoken=");
    });
    return cookie ? cookie.trim().split("=")[1] : "";
  }

  // ─── ContadorRegresivo ────────────────────────────────────────────────────
  // Timer que se decrementa cada segundo. Verde → amarillo (< 5 min) → rojo (vencido).

  function ContadorRegresivo({ horaFinUnix }) {
    var [restanteMs, setRestanteMs] = useState(horaFinUnix * 1000 - Date.now());

    useEffect(function () {
      var id = setInterval(function () {
        setRestanteMs(horaFinUnix * 1000 - Date.now());
      }, 1000);
      return function () { clearInterval(id); };
    }, [horaFinUnix]);

    var texto      = formatearCuentaRegresiva(restanteMs);
    var vencido    = texto === null;
    var pocaTiempo = !vencido && restanteMs < 5 * 60 * 1000;

    var color = vencido    ? "var(--color-danger)"
              : pocaTiempo ? "var(--color-warning)"
              : "var(--color-primary)";

    return ce("span", { style: { color: color, fontWeight: 700, fontSize: "1.1rem" } },
      vencido ? "⏰ Tiempo vencido" : texto
    );
  }

  // ─── ModalRenovar ─────────────────────────────────────────────────────────
  // Bottom-sheet modal para extender un estacionamiento activo inline.
  // onRenovado(nuevaHoraFinUnix) actualiza el estado sin recargar la página.

  function ModalRenovar({ estId, urlOpcionesBase, urlRenovarBase, onRenovado, onCerrar }) {
    var [fase,    setFase]    = useState("cargando"); // cargando | eligiendo | sin-opciones | confirmando | error
    var [datos,   setDatos]   = useState(null);
    var [opcion,  setOpcion]  = useState(null); // { label, horas, costo }
    var [mensaje, setMensaje] = useState(null);

    // Reemplaza el placeholder /0/ por el id real del estacionamiento
    function urlConId(base) {
      return base.replace("/0/", "/" + estId + "/");
    }

    useEffect(function () {
      fetch(urlConId(urlOpcionesBase))
        .then(function (r) {
          if (!r.ok) throw new Error("HTTP " + r.status);
          return r.json();
        })
        .then(function (data) {
          setDatos(data);
          setFase(data.opciones.length === 0 ? "sin-opciones" : "eligiendo");
        })
        .catch(function () {
          setFase("error");
          setMensaje("No pudimos cargar las opciones. Intentá de nuevo.");
        });
    }, []);

    function confirmar() {
      if (!opcion) return;
      setFase("confirmando");
      fetch(urlConId(urlRenovarBase), {
        method: "POST",
        headers: { "Content-Type": "application/json", "X-CSRFToken": obtenerCsrf() },
        body: JSON.stringify({ horas_extra: opcion.horas }),
      })
        .then(function (r) { return r.json(); })
        .then(function (data) {
          if (data.ok) { onRenovado(data.nueva_hora_fin_unix); }
          else { setFase("error"); setMensaje(data.error || "Error al renovar."); }
        })
        .catch(function () { setFase("error"); setMensaje("Error de red. Intentá de nuevo."); });
    }

    return ce("div", {
      style: {
        position: "fixed", inset: "0", background: "rgba(0,0,0,0.55)",
        display: "flex", alignItems: "flex-end", justifyContent: "center", zIndex: "1000",
      },
      onClick: onCerrar,
    },
      ce("div", {
        style: {
          background: "var(--color-surface)", borderRadius: "16px 16px 0 0",
          padding: "0 1.25rem 2.5rem", width: "100%", maxWidth: "480px",
          boxShadow: "0 -4px 32px rgba(0,0,0,0.2)",
        },
        onClick: function (e) { e.stopPropagation(); },
      },
        // Barra de arrastre decorativa
        ce("div", { style: { display: "flex", justifyContent: "center", padding: "0.75rem 0 0.25rem" } },
          ce("div", { style: { width: "40px", height: "4px", borderRadius: "2px", background: "var(--color-border)" } })
        ),
        // Header
        ce("div", {
          style: {
            display: "flex", justifyContent: "space-between", alignItems: "center",
            padding: "0.75rem 0 1rem", borderBottom: "1px solid var(--color-border)", marginBottom: "1.25rem",
          }
        },
          ce("span", { style: { fontSize: "1.1rem", fontWeight: 700 } }, "🔄 Extender estacionamiento"),
          ce("button", {
            type: "button", onClick: onCerrar,
            style: {
              background: "var(--color-surface-2,#f3f4f6)", border: "none", borderRadius: "50%",
              width: "32px", height: "32px", fontSize: "1.1rem", cursor: "pointer",
              color: "var(--color-text-muted)", display: "flex", alignItems: "center", justifyContent: "center",
            },
          }, "×")
        ),

        fase === "cargando" && ce("p", {
          style: { color: "var(--color-text-muted)", textAlign: "center", padding: "1rem 0" }
        }, "Cargando opciones…"),

        fase === "sin-opciones" && ce("div", { className: "alert alert-warning" },
          "⏰ Tu estacionamiento ya cubre hasta el cierre del horario. No hace falta extenderlo."
        ),

        fase === "error" && ce("div", { className: "alert alert-danger" }, mensaje),

        (fase === "eligiendo" || fase === "confirmando") && datos && ce("div", null,
          // Saldo disponible
          ce("div", {
            style: {
              display: "flex", justifyContent: "space-between", marginBottom: "1rem",
              padding: "0.75rem 1rem", background: "var(--color-surface-2)", borderRadius: "var(--radius-sm)",
            }
          },
            ce("span", { style: { color: "var(--color-text-muted)", fontSize: "0.9rem" } }, "Saldo disponible"),
            ce("strong", { style: { color: "var(--color-primary)" } }, formatearPesos(datos.saldo))
          ),
          // Botones de opción
          ce("div", { style: { display: "flex", flexWrap: "wrap", gap: "0.5rem", marginBottom: "1rem" } },
            datos.opciones.map(function (op) {
              return ce("button", {
                key: op.horas, type: "button",
                className: "btn " + (opcion && opcion.horas === op.horas ? "btn-success" : "btn-outline"),
                disabled: datos.saldo < op.costo,
                onClick: function () { setOpcion(op); },
                style: { fontSize: "1rem", padding: "0.6rem 1rem", fontWeight: "600" },
                title: datos.saldo < op.costo ? "Saldo insuficiente" : "",
              }, op.label);
            })
          ),
          opcion && ce("div", { className: "alert alert-success", style: { marginBottom: "1rem" } },
            "+" + opcion.label + " · Costo: " + formatearPesos(opcion.costo)
          ),
          ce("button", {
            type: "button", className: "btn",
            style: { width: "100%", fontSize: "1rem", padding: "0.75rem" },
            disabled: !opcion || fase === "confirmando",
            onClick: confirmar,
          }, fase === "confirmando" ? "Procesando…" : "✅ Confirmar extensión")
        )
      )
    );
  }

  // ─── CardUnEstacionamiento ────────────────────────────────────────────────
  // Muestra un estacionamiento activo con patente, hora, timer y botón Extender.

  function CardUnEstacionamiento({ est, urlEstacionar, onExtender }) {
    var horaFinStr  = formatearHora(est.hora_fin_unix);
    var restanteMs  = est.hora_fin_unix * 1000 - Date.now();
    var pocaTiempo  = restanteMs > 0 && restanteMs < 5 * 60 * 1000;

    return ce("div", null,
      ce("div", {
        style: {
          display: "flex", alignItems: "center", justifyContent: "space-between",
          flexWrap: "wrap", gap: "0.5rem", marginTop: "0.5rem",
        }
      },
        ce("div", null,
          ce("p", { style: { fontSize: "1.5rem", fontWeight: 800, letterSpacing: "2px", margin: "0 0 0.15rem" } },
            est.patente
          ),
          ce("p", { style: { fontSize: "0.95rem", color: "var(--color-text-muted)", margin: 0 } },
            "hasta las ", ce("strong", null, horaFinStr), " — ",
            ce(ContadorRegresivo, { horaFinUnix: est.hora_fin_unix })
          )
        ),
        ce("button", {
          type: "button", className: "btn btn-outline",
          onClick: function () { onExtender(est.id); },
        }, "🔄 Extender")
      ),
      pocaTiempo && ce("div", {
        className: "alert alert-warning",
        style: { marginTop: "0.5rem", display: "flex", alignItems: "center", gap: "0.5rem" },
      }, ce("strong", null, "¡Quedan menos de 5 minutos! Extendé ahora.")),
      est.subcuadra && ce("p", {
        style: { fontSize: "0.82rem", color: "var(--color-text-muted)", margin: "0.6rem 0 0.75rem" }
      }, "📍 " + est.subcuadra),
      ce("a", { className: "btn", href: urlEstacionar }, "+ Estacionar otro vehículo")
    );
  }

  // ─── ListaEstacionamientos ─────────────────────────────────────────────────
  // Lista compacta cuando hay múltiples vehículos estacionados.

  function ListaEstacionamientos({ estacionamientos, onExtender }) {
    return ce("div", { style: { display: "flex", flexDirection: "column", gap: "0.4rem", marginTop: "0.5rem" } },
      estacionamientos.map(function (est) {
        return ce("div", {
          key: est.id,
          style: {
            display: "flex", alignItems: "center", justifyContent: "space-between",
            padding: "0.35rem 0", borderBottom: "1px solid var(--color-border)",
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
            type: "button", className: "btn btn-outline",
            onClick: function () { onExtender(est.id); },
            style: { fontSize: "0.78rem", padding: "0.2rem 0.5rem" },
          }, "🔄 Extender")
        );
      })
    );
  }

  // ─── SaldoCard ────────────────────────────────────────────────────────────
  // Saldo del conductor con botón para mostrar/ocultar (privacidad en mobile).
  // Por defecto visible. El estado se mantiene en memoria (no persiste entre recargas).

  function SaldoCard({ saldo, saldoBajo, urlRecargar }) {
    var [visible, setVisible] = useState(true);

    return ce("div", {
      className: "card",
      style: { marginBottom: "1rem" },
    },
      // Header: etiqueta + toggle
      ce("div", {
        style: { display: "flex", alignItems: "center", justifyContent: "space-between", marginBottom: "0.4rem" }
      },
        ce("span", { style: { fontSize: "0.88rem", color: "var(--color-text-muted)", fontWeight: 600 } },
          "💰 Tu saldo"
        ),
        ce("button", {
          type: "button",
          onClick: function () { setVisible(function (v) { return !v; }); },
          title: visible ? "Ocultar saldo" : "Mostrar saldo",
          style: {
            background: "none", border: "none", cursor: "pointer",
            fontSize: "1rem", color: "var(--color-text-muted)", padding: "0 0.2rem",
            lineHeight: 1,
          },
        }, visible ? "🙈" : "👁️")
      ),

      // Monto (visible u oculto)
      ce("div", { style: { fontSize: "2rem", fontWeight: 800, letterSpacing: "-0.5px", marginBottom: "0.3rem" } },
        visible ? formatearPesos(saldo) : "••••••"
      ),

      // Aviso saldo bajo
      saldoBajo && ce("p", {
        style: { margin: "0 0 0.5rem", fontSize: "0.85rem", color: "var(--color-danger, #c0392b)", fontWeight: 600 }
      }, "⚠️ Saldo bajo"),

      // Acciones
      ce("div", { style: { display: "flex", gap: "0.5rem", flexWrap: "wrap" } },
        ce("a", {
          href: urlRecargar, className: "btn btn-outline",
          style: { fontSize: "0.85rem", padding: "0.3rem 0.9rem" },
        }, "💳 Cargar saldo")
      )
    );
  }

  // ─── PanelEstadoConductor ─────────────────────────────────────────────────
  // Estado del vehículo — recibe los datos como props, no hace su propio fetch.
  // La lógica de datos (fetch + polling) vive en PanelConductor (componente raíz).

  function PanelEstadoConductor({ estado, urlEstacionar, urlRecargar, onExtender }) {
    var activos = estado.estacionamientos_activos || [];

    // Fuera de horario
    if (!estado.puede_estacionar) {
      return ce("div", { className: "card", style: { marginBottom: "1rem" } },
        ce("h3", null, "🚗 Estado del vehículo"),
        ce("div", { className: "alert alert-warning", style: { margin: 0 } },
          "⏰ " + estado.mensaje_horario
        )
      );
    }

    // Con estacionamientos activos
    if (activos.length > 0) {
      return ce("div", { className: "card", style: { marginBottom: "1rem" } },
        ce("h3", null, "🚗 Estado del vehículo"),
        ce("div", { className: "status-ok" },
          "🟢 " + (activos.length > 1
            ? activos.length + " vehículos activos"
            : "Estacionamiento activo")
        ),
        activos.length === 1
          ? ce(CardUnEstacionamiento, { est: activos[0], urlEstacionar: urlEstacionar, onExtender: onExtender })
          : ce(ListaEstacionamientos, { estacionamientos: activos, onExtender: onExtender })
      );
    }

    // Sin estacionamiento activo
    return ce("div", { className: "card", style: { marginBottom: "1rem" } },
      ce("h3", null, "🚗 Estado del vehículo"),
      ce("div", { className: "status-warn" }, "🟡 Sin estacionamiento"),
      estado.saldo_insuficiente
        ? ce("div", null,
            ce("div", {
              className: "alert alert-warning",
              style: { margin: "0.75rem 0 0.5rem", fontSize: "0.9rem" },
            },
              "⚠️ Tu saldo no alcanza para ",
              estado.duracion_minima_min ? estado.duracion_minima_min + " minutos" : "el mínimo",
              estado.costo_duracion_minima
                ? " (" + formatearPesos(estado.costo_duracion_minima) + ")"
                : "",
              ". Recargá antes de estacionar."
            ),
            ce("a", { className: "btn btn-primary", href: urlRecargar }, "💳 Recargar saldo")
          )
        : ce("a", { className: "btn", href: urlEstacionar }, "🛵 Estacionar 🚗")
    );
  }

  // ─── AbonoBanner ──────────────────────────────────────────────────────────
  // Sección compacta que muestra los abonos activos del mes.
  // No aparece si no hay abonos activos.

  function AbonoBanner({ abonos, urlPagarAbono }) {
    if (!abonos || abonos.length === 0) return null;

    return ce("div", { className: "card", style: { marginBottom: "1rem" } },
      ce("div", {
        style: { display: "flex", alignItems: "center", justifyContent: "space-between", marginBottom: "0.4rem" }
      },
        ce("h4", { style: { margin: 0, fontSize: "0.95rem" } }, "📅 Abono mensual"),
        ce("a", {
          href: urlPagarAbono, className: "btn btn-outline",
          style: { fontSize: "0.78rem", padding: "0.2rem 0.6rem" },
        }, "+ Pagar")
      ),
      ce("div", null,
        abonos.map(function (abono, i) {
          return ce("div", {
            key: i,
            style: { display: "flex", alignItems: "center", gap: "0.5rem", padding: "0.15rem 0", fontSize: "0.9rem" },
          },
            ce("span", null, "✅"),
            ce("strong", null, abono.patente),
            ce("span", { style: { color: "var(--color-text-muted)", fontSize: "0.85rem" } },
              "— acceso libre este mes"
            )
          );
        })
      )
    );
  }

  // ─── FilaVehiculo ─────────────────────────────────────────────────────────
  // Fila de la lista "Mis vehículos" con estado, patente y botones de acción.

  function FilaVehiculo({ vehiculo, urlHistorialBase, urlInfraccionesBase, esUltimo }) {
    var icono = vehiculo.tipo === "moto" ? "🛵" : "🚗";

    function badgeEstado() {
      if (vehiculo.tiene_estacionamiento_activo) return ce("span", { title: "Estacionado ahora" }, "🟢");
      if (vehiculo.tiene_abono_activo)           return ce("span", { title: "Abono activo" }, "🔵");
      return ce("span", { title: "Sin estacionamiento", style: { opacity: "0.35" } }, "⚪");
    }

    return ce("div", {
      style: {
        display: "flex", alignItems: "center", justifyContent: "space-between",
        flexWrap: "wrap", gap: "0.5rem", padding: "0.5rem 0",
        borderBottom: esUltimo ? "none" : "1px solid var(--color-border)",
      }
    },
      ce("div", { style: { display: "flex", alignItems: "center", gap: "0.5rem", flexWrap: "wrap" } },
        badgeEstado(),
        ce("strong", { style: { letterSpacing: "1px" } }, vehiculo.patente),
        ce("span", { style: { color: "var(--color-text-muted)", fontSize: "0.88rem" } },
          icono + " " + vehiculo.tipo_display
        ),
        vehiculo.infracciones_pendientes > 0 && ce("span", {
          style: { fontSize: "0.8rem", color: "var(--color-danger,#c0392b)", fontWeight: "700" },
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

  // ─── MisVehiculos ─────────────────────────────────────────────────────────
  // Acordeón: botón que muestra cuántos vehículos hay (y si hay infracciones)
  // y expande la lista al hacer click. Cerrado por defecto.

  function MisVehiculos({ vehiculos, urlHistorialBase, urlInfraccionesBase, urlAgregarVehiculo }) {
    var [abierto, setAbierto] = useState(false);

    if (!vehiculos || vehiculos.length === 0) return null;

    // Conteos para el encabezado del botón
    var conInfraccion = vehiculos.filter(function (v) { return v.infracciones_pendientes > 0; }).length;
    var conActivo     = vehiculos.filter(function (v) { return v.tiene_estacionamiento_activo; }).length;

    return ce("div", { className: "card", style: { marginBottom: "1rem" } },

      // ── Header: botón accordion ────────────────────────────────────────────
      ce("button", {
        type: "button",
        onClick: function () { setAbierto(function (a) { return !a; }); },
        style: {
          background: "none", border: "none", cursor: "pointer", font: "inherit",
          width: "100%", display: "flex", alignItems: "center", justifyContent: "space-between",
          padding: "0",
        },
        "aria-expanded": abierto,
      },
        ce("span", { style: { display: "flex", alignItems: "center", gap: "0.5rem" } },
          ce("span", { style: { fontSize: "1rem", fontWeight: 700 } }, "🚗 Mis vehículos"),
          // Badge cantidad
          ce("span", {
            style: {
              fontSize: "0.8rem", fontWeight: 400, color: "var(--color-text-muted)",
              background: "var(--color-bg-subtle,#f0f4ff)", borderRadius: "10px",
              padding: "0.05rem 0.45rem",
            }
          }, vehiculos.length),
          // Badge activos (solo si hay alguno activo)
          conActivo > 0 && ce("span", {
            style: {
              fontSize: "0.78rem", fontWeight: 600, color: "var(--color-primary)",
              background: "var(--color-bg-subtle,#f0f4ff)", borderRadius: "10px",
              padding: "0.05rem 0.45rem",
            },
            title: conActivo + " estacionado(s) ahora",
          }, "🟢 " + conActivo),
          // Badge infracciones (solo si hay)
          conInfraccion > 0 && ce("span", {
            style: {
              fontSize: "0.78rem", fontWeight: 700, color: "var(--color-danger,#c0392b)",
            },
            title: conInfraccion + " vehículo(s) con infracciones",
          }, "⚠️ " + conInfraccion)
        ),
        // Chevron
        ce("span", {
          style: {
            fontSize: "0.85rem", color: "var(--color-text-muted)",
            transition: "transform 0.2s",
            display: "inline-block",
            transform: abierto ? "rotate(180deg)" : "rotate(0deg)",
          }
        }, "▼")
      ),

      // ── Contenido: lista + botón agregar ──────────────────────────────────
      abierto && ce("div", { style: { marginTop: "0.75rem" } },
        ce("div", {
          style: { display: "flex", flexDirection: "column", gap: "0", maxHeight: "215px", overflowY: "auto" }
        },
          vehiculos.map(function (v, i) {
            return ce(FilaVehiculo, {
              key: v.id,
              vehiculo: v,
              urlHistorialBase: urlHistorialBase,
              urlInfraccionesBase: urlInfraccionesBase,
              esUltimo: i === vehiculos.length - 1,
            });
          })
        ),
        ce("div", { style: { marginTop: "0.6rem" } },
          ce("a", {
            href: urlAgregarVehiculo, className: "btn btn-outline",
            style: { fontSize: "0.82rem" },
          }, "+ Agregar vehículo")
        )
      )
    );
  }

  // ─── PanelConductor ───────────────────────────────────────────────────────
  // Componente raíz.
  // Hace UN solo fetch a /api/conductor/dashboard/ y distribuye los datos
  // a SaldoCard, PanelEstadoConductor, AbonoBanner y MisVehiculos.
  // El polling de 30s solo actualiza los estacionamientos activos (para el timer).
  // El modal de renovar se gestiona acá para que quede en el nivel raíz del DOM.

  function PanelConductor(props) {
    var urlDashboard             = props.urlDashboard;
    var urlEstacionamientosActivos = props.urlEstacionamientosActivos;
    var urlEstacionar            = props.urlEstacionar;
    var urlRecargar              = props.urlRecargar;
    var urlOpcionesRenovarBase   = props.urlOpcionesRenovarBase;
    var urlRenovarBase           = props.urlRenovarBase;
    var urlHistorialBase         = props.urlHistorialBase;
    var urlInfraccionesBase      = props.urlInfraccionesBase;
    var urlAgregarVehiculo       = props.urlAgregarVehiculo;
    var urlPagarAbono            = props.urlPagarAbono;

    var [estado,                  setEstado]                  = useState(null);
    var [error,                   setError]                   = useState(null);
    var [idEstacionamientoModal,  setIdEstacionamientoModal]  = useState(null);

    // Fetch inicial — carga todo el estado del conductor
    useEffect(function () {
      fetch(urlDashboard)
        .then(function (r) {
          if (!r.ok) throw new Error("HTTP " + r.status);
          return r.json();
        })
        .then(function (data) { setEstado(data); })
        .catch(function (e) {
          console.error("[PanelConductor] error cargando dashboard:", e);
          setError("No pudimos cargar el panel. Recargá la página.");
        });
    }, []);

    // Polling cada 30s: solo actualiza estacionamientos activos (mantiene los timers frescos)
    // Por qué solo activos y no el dashboard completo: el dashboard incluye vehículos,
    // abonos y cálculos de saldo — demasiado pesado para cada 30 segundos.
    useEffect(function () {
      if (!estado) return;
      var id = setInterval(function () {
        fetch(urlEstacionamientosActivos)
          .then(function (r) { return r.json(); })
          .then(function (data) {
            setEstado(function (prev) {
              if (!prev) return prev;
              return Object.assign({}, prev, { estacionamientos_activos: data.estacionamientos });
            });
          })
          .catch(function () {}); // fallo silencioso en polling
      }, 30000);
      return function () { clearInterval(id); };
    }, [!!estado]); // solo cuando cambia de null → algo

    // ── Render: error de red ───────────────────────────────────────────────
    if (error) {
      return ce("div", { className: "card" },
        ce("div", { className: "alert alert-danger", style: { margin: 0 } }, error)
      );
    }

    // ── Render: cargando ───────────────────────────────────────────────────
    if (!estado) {
      return ce("div", { className: "card" },
        ce("p", { style: { color: "var(--color-text-muted)", margin: 0 } }, "Cargando…")
      );
    }

    var saldoBajo = Number(estado.saldo) < 100;

    // ── Render: panel completo ─────────────────────────────────────────────
    return ce(React.Fragment, null,

      // Modal de renovar (fixed overlay — fuera del flujo normal del DOM)
      idEstacionamientoModal !== null && ce(ModalRenovar, {
        estId:           idEstacionamientoModal,
        urlOpcionesBase: urlOpcionesRenovarBase,
        urlRenovarBase:  urlRenovarBase,
        onCerrar: function () { setIdEstacionamientoModal(null); },
        onRenovado: function (nuevaHoraFinUnix) {
          setIdEstacionamientoModal(null);
          setEstado(function (prev) {
            if (!prev) return prev;
            return Object.assign({}, prev, {
              estacionamientos_activos: prev.estacionamientos_activos.map(function (e) {
                return e.id === idEstacionamientoModal
                  ? Object.assign({}, e, { hora_fin_unix: nuevaHoraFinUnix })
                  : e;
              }),
            });
          });
        },
      }),

      // 1. Saldo con toggle ocultar/mostrar
      ce(SaldoCard, {
        saldo:      estado.saldo,
        saldoBajo:  saldoBajo,
        urlRecargar: urlRecargar,
      }),

      // 2. Estado del vehículo (activo / sin est. / fuera horario)
      ce(PanelEstadoConductor, {
        estado:       estado,
        urlEstacionar: urlEstacionar,
        urlRecargar:   urlRecargar,
        onExtender:    setIdEstacionamientoModal,
      }),

      // 3. Abono mensual (solo si hay)
      ce(AbonoBanner, {
        abonos:      estado.abonos_activos || [],
        urlPagarAbono: urlPagarAbono,
      }),

      // 4. Mis vehículos (acordeón, cerrado por defecto)
      ce(MisVehiculos, {
        vehiculos:          estado.vehiculos || [],
        urlHistorialBase:   urlHistorialBase,
        urlInfraccionesBase: urlInfraccionesBase,
        urlAgregarVehiculo:  urlAgregarVehiculo,
      })
    );
  }

  // ─── Mount ────────────────────────────────────────────────────────────────
  // Lee todas las URLs del data-* del elemento raíz.
  // Así Django reverse() calcula las URLs y el JS no conoce los patrones de ruta.

  var contenedor = document.getElementById("panel-conductor-react");
  if (!contenedor) return;

  var d = contenedor.dataset;
  ReactDOM.render(
    ce(PanelConductor, {
      urlDashboard:              d.urlDashboard,
      urlEstacionamientosActivos: d.urlEstacionamientosActivos,
      urlEstacionar:             d.urlEstacionar,
      urlRecargar:               d.urlRecargar,
      urlOpcionesRenovarBase:    d.urlOpcionesRenovarBase,
      urlRenovarBase:            d.urlRenovarBase,
      urlHistorialBase:          d.urlHistorial,
      urlInfraccionesBase:       d.urlInfracciones,
      urlAgregarVehiculo:        d.urlAgregarVehiculo,
      urlPagarAbono:             d.urlPagarAbono,
    }),
    contenedor
  );
  // Marca el contenedor para que el script inline del template sepa que React montó OK.
  // Si este atributo no aparece, el script muestra el fallback Django después de 3 segundos.
  contenedor.dataset.reactMontado = "1";

})();
