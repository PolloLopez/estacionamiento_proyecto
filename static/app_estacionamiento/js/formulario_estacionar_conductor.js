/**
 * FormularioEstacionar — componente React para la pantalla de estacionar.
 *
 * Reemplaza el formulario Django de estacionar_vehiculo.html con una versión
 * que carga datos frescos por API y envía el POST a /api/conductor/estacionar/
 * sin recargar la página.
 *
 * Estrategia de migración:
 *   - El formulario Django queda en el DOM (id="formulario-estacionar-fallback")
 *   - Al montar correctamente, se oculta el fallback Django
 *   - Si la API falla al cargar, el fallback Django toma el control
 *
 * GPS y subcuadra:
 *   - GPS usa navigator.geolocation + endpoint /conductor/subcuadra-cercana/
 *   - Subcuadra cascade (calle → altura) se maneja en React con useState
 *   - Las coords GPS capturadas silenciosamente se mandan junto al POST
 */

"use strict";

var ce = React.createElement;
const { useState, useEffect, useRef } = React;

// ── Helpers GPS ───────────────────────────────────────────────────────────────

/**
 * Llama al endpoint de subcuadra cercana con las coords del navegador.
 * onResultado recibe el objeto {id, nombre, tipo_zona, entre} o null si falla.
 */
function detectarSubcuadraCercana(urlCercana, onResultado) {
  if (!navigator.geolocation) {
    onResultado(null);
    return;
  }
  navigator.geolocation.getCurrentPosition(
    function(pos) {
      var lat = pos.coords.latitude;
      var lon = pos.coords.longitude;
      fetch(urlCercana + "?lat=" + lat + "&lon=" + lon)
        .then(function(r) { return r.json(); })
        .then(function(data) { onResultado(data.id ? data : null); })
        .catch(function() { onResultado(null); });
    },
    function() { onResultado(null); },
    { timeout: 8000 }
  );
}

/**
 * Captura coords GPS en silencio para enviarlas en el POST de estacionar.
 * Si el usuario niega el permiso simplemente no se guardan.
 */
function capturarCoordsGps(callback) {
  if (!navigator.geolocation) return;
  navigator.geolocation.getCurrentPosition(
    function(pos) {
      callback(
        pos.coords.latitude.toFixed(6),
        pos.coords.longitude.toFixed(6)
      );
    },
    function() { /* permiso denegado: silencioso */ },
    { enableHighAccuracy: true, timeout: 10000, maximumAge: 60000 }
  );
}

function obtenerCsrf() {
  var match = document.cookie.match(/csrftoken=([^;]+)/);
  return match ? match[1] : "";
}

// ── TarjetaVehiculo ───────────────────────────────────────────────────────────

/**
 * onPedirEliminar(vehiculo): el padre muestra el modal de confirmación y hace el fetch.
 * La tarjeta no maneja directamente ni el confirm ni el fetch — responsabilidad única.
 */
function TarjetaVehiculo({ vehiculo, seleccionado, onSeleccionar, onPedirEliminar }) {
  var icono = vehiculo.tipo === "moto" ? "🛵" : "🚗";
  var estiloTarjeta = {
    flex: "1", minWidth: "130px", maxWidth: "180px",
    border: seleccionado ? "3px solid var(--color-primary)" : "3px solid var(--color-border)",
    background: seleccionado ? "var(--color-primary-light)" : "var(--color-surface)",
    borderRadius: "14px", padding: "1rem 0.9rem", textAlign: "center",
    cursor: "pointer", transition: "border-color 0.15s, background 0.15s",
    position: "relative",
  };

  function eliminar(e) {
    e.stopPropagation();
    e.preventDefault();
    onPedirEliminar(vehiculo);
  }

  return ce("div", { style: estiloTarjeta, onClick: function() { onSeleccionar(vehiculo); } },
    ce("div", { style: { fontSize: "1.5rem", fontWeight: "800", letterSpacing: "2px", wordBreak: "break-all", lineHeight: "1.1" } },
      vehiculo.patente
    ),
    ce("div", { style: { fontSize: "0.82rem", color: "var(--color-text-muted)", marginTop: "0.35rem" } },
      icono + " " + vehiculo.tipo_display
    ),
    vehiculo.tiene_abono && ce("div", {
      style: { fontSize: "0.72rem", color: "var(--color-warning)", marginTop: "0.25rem", fontWeight: "700" }
    }, "🗓️ Abono activo"),
    !vehiculo.tiene_abono && vehiculo.exento && ce("div", {
      style: { fontSize: "0.72rem", color: "var(--color-primary)", marginTop: "0.25rem", fontWeight: "700" }
    }, "✅ Exento"),
    // Botón eliminar (✕ arriba a la derecha)
    ce("button", {
      type: "button",
      onClick: eliminar,
      title: "Quitar vehículo",
      style: {
        position: "absolute", top: "5px", right: "5px",
        background: "none", border: "none", cursor: "pointer",
        fontSize: "0.85rem", color: "var(--color-text-muted)",
        padding: "2px 5px", borderRadius: "4px",
      },
    }, "✕")
  );
}

// ── ModalConfirmarEliminar ────────────────────────────────────────────────────
//
// Overlay de confirmación propio — reemplaza el confirm() nativo del browser,
// que tiene estilo de sistema operativo y no puede personalizarse.
// Se monta sobre toda la pantalla con fondo semitransparente.
// Click fuera del card → cancela (mismo comportamiento que un dialog nativo).

function ModalConfirmarEliminar({ vehiculo, onConfirmar, onCancelar }) {
  return ce("div", {
    // Overlay: cubre toda la pantalla
    style: {
      position: "fixed", inset: "0",
      background: "rgba(0,0,0,0.48)",
      zIndex: "1000",
      display: "flex", alignItems: "center", justifyContent: "center",
      padding: "1rem",
    },
    onClick: onCancelar,
  },
    ce("div", {
      // Card centrado: click interno no propaga al overlay
      style: {
        background: "var(--color-surface)",
        borderRadius: "16px",
        padding: "1.75rem 1.5rem 1.5rem",
        maxWidth: "340px", width: "100%",
        boxShadow: "0 8px 32px rgba(0,0,0,0.22)",
        textAlign: "center",
      },
      onClick: function(e) { e.stopPropagation(); },
    },
      ce("div", { style: { fontSize: "2.2rem", marginBottom: "0.5rem" } }, "🗑️"),
      ce("h4", { style: { margin: "0 0 0.4rem", fontSize: "1.1rem" } },
        "¿Eliminar vehículo?"
      ),
      ce("p", { style: { color: "var(--color-text-muted)", fontSize: "0.95rem", margin: "0 0 1.4rem" } },
        "Vas a quitar ",
        ce("strong", { style: { letterSpacing: "1.5px", color: "var(--color-text)" } }, vehiculo.patente),
        " de tu cuenta."
      ),
      ce("div", { style: { display: "flex", gap: "0.6rem" } },
        ce("button", {
          type: "button",
          className: "btn btn-outline",
          style: { flex: "1", fontSize: "0.95rem" },
          onClick: onCancelar,
        }, "Cancelar"),
        ce("button", {
          type: "button",
          className: "btn",
          style: {
            flex: "1", fontSize: "0.95rem",
            background: "var(--color-danger, #c0392b)",
            borderColor: "var(--color-danger, #c0392b)",
            color: "#fff",
          },
          onClick: onConfirmar,
        }, "Sí, eliminar")
      )
    )
  );
}

// ── SeccionSubcuadra ──────────────────────────────────────────────────────────
//
// Selector de cuadra con dos capas:
//   1. Input de calle (autocomplete con datalist) — GPS lo pre-llena
//   2. Botonera de cuadras filtradas por esa calle — GPS resalta la detectada
//
// Reemplaza el <select> anterior que resultaba incómodo en mobile.

function SeccionSubcuadra({
  subcuadras, gpsEstado, subcuadraId,
  calleManual, onSubcuadraChange, onCalleChange,
}) {
  // Calles únicas para el datalist
  var callesUnicas = [];
  var callesVistas = {};
  subcuadras.forEach(function(s) {
    if (!callesVistas[s.calle]) {
      callesVistas[s.calle] = true;
      callesUnicas.push(s.calle);
    }
  });
  callesUnicas.sort();

  // Si hay pocas subcuadras (≤ 12), mostrar todas cuando no hay filtro de calle;
  // si hay muchas, esperar a que el usuario filtre para no saturar la pantalla.
  var mostrarTodas = subcuadras.length <= 12;
  var subcuadrasMostradas = calleManual
    ? subcuadras.filter(function(s) {
        return s.calle.toLowerCase().includes(calleManual.toLowerCase());
      })
    : (mostrarTodas ? subcuadras : []);

  // Chip de estado GPS: reemplaza el texto plano — inline junto al título para
  // que el conductor vea el estado sin necesidad de buscar un párrafo aparte.
  var chipGps = null;
  if (gpsEstado === "detectando") {
    chipGps = ce("span", { style: {
      display: "inline-flex", alignItems: "center", gap: "0.3rem",
      fontSize: "0.76rem", padding: "0.2rem 0.65rem", borderRadius: "20px",
      background: "#e8f4fd", color: "#0077cc", border: "1px solid #b8daff",
      fontWeight: "600", letterSpacing: "0",
    }}, "📡 Detectando…");
  } else if (gpsEstado === "detectado") {
    chipGps = ce("span", { style: {
      display: "inline-flex", alignItems: "center", gap: "0.3rem",
      fontSize: "0.76rem", padding: "0.2rem 0.65rem", borderRadius: "20px",
      background: "#d4edda", color: "#155724", border: "1px solid #c3e6cb",
      fontWeight: "600",
    }}, "📡 GPS activo");
  } else if (gpsEstado === "fallo") {
    chipGps = ce("span", { style: {
      display: "inline-flex", alignItems: "center", gap: "0.3rem",
      fontSize: "0.76rem", padding: "0.2rem 0.65rem", borderRadius: "20px",
      background: "#fff3cd", color: "#856404", border: "1px solid #ffc107",
      fontWeight: "600",
    }}, "⚠️ Sin GPS");
  }

  return ce("div", { style: { marginBottom: "1.2rem" } },
    // Título + chip de estado GPS en la misma línea
    ce("div", { style: { display: "flex", alignItems: "center", gap: "0.65rem", marginBottom: "0.75rem", flexWrap: "wrap" } },
      ce("h3", { style: { margin: "0" } }, "📍 ¿Dónde estás?"),
      chipGps,
    ),

    // Input de calle — siempre visible, pre-llenado por GPS cuando detecta
    ce("div", { style: { display: "flex", gap: "0.5rem", alignItems: "center", marginBottom: "0.6rem" } },
      ce("input", {
        list: "list-calles-react",
        placeholder: "Calle…",
        value: calleManual,
        onChange: function(e) { onCalleChange(e.target.value); },
        autoComplete: "off",
        style: {
          flex: "1", padding: "0.5rem 0.65rem", borderRadius: "6px",
          border: "1px solid var(--color-border)", fontSize: "1rem",
          background: "var(--color-surface)",
        },
      }),
      ce("datalist", { id: "list-calles-react" },
        callesUnicas.map(function(c) { return ce("option", { key: c, value: c }); })
      ),
      // Botón para limpiar el filtro de calle
      calleManual && ce("button", {
        type: "button",
        onClick: function() { onCalleChange(""); },
        title: "Limpiar calle",
        style: {
          padding: "0.45rem 0.7rem", borderRadius: "6px",
          border: "1px solid var(--color-border)", background: "var(--color-surface)",
          cursor: "pointer", fontSize: "0.95rem", color: "var(--color-text-muted)", flexShrink: "0",
        },
      }, "✕")
    ),

    // Botonera de cuadras (filtradas por calle o todas si son pocas)
    subcuadrasMostradas.length > 0
      ? ce("div", { style: { display: "flex", flexWrap: "wrap", gap: "0.4rem" } },
          subcuadrasMostradas.map(function(s) {
            var activa = s.id === subcuadraId;
            // Si hay calle filtrada, mostrar solo la altura/entre para no repetir la calle
            var nombreBtn = calleManual
              ? (s.altura + (s.entre ? " — " + s.entre : ""))
              : (s.calle + " " + s.altura);
            return ce("button", {
              key: s.id, type: "button",
              onClick: function() { onSubcuadraChange(s.id, s); },
              style: {
                padding: "0.4rem 0.75rem", borderRadius: "6px", fontSize: "0.88rem",
                border: activa ? "2px solid var(--color-primary)" : "1px solid var(--color-border)",
                background: activa ? "var(--color-primary-light)" : "var(--color-surface)",
                color: activa ? "var(--color-primary)" : "var(--color-text)",
                cursor: "pointer", fontWeight: activa ? "700" : "400",
                transition: "border-color 0.12s, background 0.12s",
              },
            }, nombreBtn);
          })
        )
      : ce("p", {
          style: { fontSize: "0.84rem", color: "var(--color-text-muted)", fontStyle: "italic", margin: "0.3rem 0" }
        }, calleManual ? "Sin cuadras para esa calle." : "Escribí la calle para ver las cuadras disponibles.")
  );
}

// ── BotoneraDuracion ──────────────────────────────────────────────────────────

function BotoneraDuracion({ opciones, seleccionada, onSeleccionar }) {
  if (!opciones || opciones.length === 0) {
    return ce("div", { className: "alert alert-warning" },
      "⏰ El horario de cobro finalizó. No hace falta que registres estacionamiento."
    );
  }
  return ce("div", { className: "duraciones" },
    opciones.map(function(op) {
      var activa = seleccionada && seleccionada.horas === op.horas;
      return ce("button", {
        key: op.horas,
        type: "button",
        className: "btn btn-outline duracion-btn" + (activa ? " duracion-activa" : ""),
        onClick: function() { onSeleccionar(op); },
        style: { flex: "1", minWidth: "80px", fontSize: "1.1rem", padding: "0.75rem 0", fontWeight: "700" },
      }, op.label);
    })
  );
}

// ── FormularioEstacionar ──────────────────────────────────────────────────────

function FormularioEstacionar({
  urlDatos, urlEstacionar, urlAgregarVehiculo, urlEliminarBase, urlCargaSaldo,
  patentePresel, onMontadoConExito,
}) {
  var [datos, setDatos]             = useState(null);
  var [errorCarga, setErrorCarga]   = useState(false);

  // Selección de vehículo y duración
  var [vehiculoSel, setVehiculoSel] = useState(null);
  var [duracionSel, setDuracionSel] = useState(null);

  // Estado GPS y subcuadra
  var [gpsEstado, setGpsEstado]         = useState("inactivo"); // inactivo|detectando|detectado|fallo
  var [gpsYaCorrio, setGpsYaCorrio]     = useState(false);
  var [subcuadraId, setSubcuadraId]     = useState(null);
  var [subcuadraNombre, setSubcuadraNombre] = useState("");
  var [subcuadraTipo, setSubcuadraTipo] = useState("paga");     // "libre" o "paga"
  var [calleManual, setCalleManual]     = useState("");
  var [alturaManual, setAlturaManual]   = useState("");

  // Coords GPS silenciosas para el POST
  var [gpsLat, setGpsLat] = useState("");
  var [gpsLon, setGpsLon] = useState("");

  // Estado de envío
  var [enviando, setEnviando]   = useState(false);
  var [errorForm, setErrorForm] = useState(null);

  // Mostrar/ocultar form inline de agregar vehículo
  var [mostrarAgregar, setMostrarAgregar] = useState(false);

  // Vehículo pendiente de eliminar: cuando no es null, se muestra el modal de confirmación
  var [vehiculoAEliminar, setVehiculoAEliminar] = useState(null);

  // ── Fetch inicial de datos ───────────────────────────────────────────────
  useEffect(function() {
    fetch(urlDatos)
      .then(function(r) {
        if (!r.ok) throw new Error("HTTP " + r.status);
        return r.json();
      })
      .then(function(d) {
        setDatos(d);
        // Ocultar fallback Django — React toma el control
        onMontadoConExito();
        // Capturar coords GPS en background si el municipio lo tiene habilitado
        if (d.geoloc_activa) {
          capturarCoordsGps(function(lat, lon) {
            setGpsLat(lat);
            setGpsLon(lon);
          });
        }
        // Pre-seleccionar vehículo desde ?patente=XXX o si solo hay uno
        if (d.vehiculos && d.vehiculos.length > 0) {
          var vPre = patentePresel
            ? d.vehiculos.find(function(v) { return v.patente === patentePresel; })
            : null;
          var vAuto = vPre || (d.vehiculos.length === 1 ? d.vehiculos[0] : null);
          if (vAuto) seleccionarVehiculo(vAuto, d);
        }
      })
      .catch(function() {
        // Error de red: dejar el fallback Django visible
        setErrorCarga(true);
      });
  }, []);

  // ── Seleccionar vehículo ─────────────────────────────────────────────────
  // datosActuales: el objeto data que llega del fetch (antes de que setDatos termine).
  // En clicks posteriores se usa el estado `datos` ya disponible.
  function seleccionarVehiculo(v, datosActuales) {
    var d = datosActuales || datos;
    setVehiculoSel(v);
    setDuracionSel(null);
    setErrorForm(null);

    if (v.tiene_abono) return; // abono activo: no arrancar GPS ni mostrar duración

    // Arrancar GPS solo la primera vez (mismo comportamiento que el template JS)
    if (!gpsYaCorrio && d && d.subcuadras && d.subcuadras.length > 0) {
      setGpsYaCorrio(true);
      setGpsEstado("detectando");
      detectarSubcuadraCercana(d.url_subcuadra_cercana, function(resultado) {
        if (resultado && resultado.id) {
          setSubcuadraId(resultado.id);
          setSubcuadraNombre(resultado.nombre + (resultado.entre ? " — " + resultado.entre : ""));
          setSubcuadraTipo(resultado.tipo_zona || "paga");
          setGpsEstado("detectado");
          // Pre-llenar el input de calle para que la botonera muestre solo esa calle
          var subCercana = d.subcuadras && d.subcuadras.find(function(s) { return s.id === resultado.id; });
          if (subCercana) setCalleManual(subCercana.calle);
        } else {
          setGpsEstado("fallo");
        }
      });
    }

    // Auto-seleccionar primera duración disponible
    if (d) {
      var opciones = v.tipo === "moto" ? d.opciones_duracion_moto : d.opciones_duracion_auto;
      if (opciones && opciones.length > 0) {
        setDuracionSel(opciones[0]);
      }
    }
  }

  // ── Cambios de subcuadra ─────────────────────────────────────────────────

  function onSubcuadraChange(id, subcuadra) {
    setSubcuadraId(id);
    if (subcuadra) {
      setSubcuadraTipo(subcuadra.tipo_zona || "paga");
      // Incluir entre_calles en el nombre para mostrar en el banner de zona libre
      setSubcuadraNombre(
        subcuadra.calle + " " + subcuadra.altura +
        (subcuadra.entre ? " — " + subcuadra.entre : "")
      );
    } else {
      setSubcuadraTipo("paga");
    }
    // Limpiar duración si cambió a zona libre (no se usa duración en ese caso)
    if (subcuadra && subcuadra.tipo_zona === "libre") {
      setDuracionSel(null);
    }
  }

  function onCalleChange(calle) {
    setCalleManual(calle);
    setAlturaManual("");
    setSubcuadraId(null);
    setSubcuadraTipo("paga");
  }

  // ── Eliminar vehículo ────────────────────────────────────────────────────
  function eliminarVehiculo(vehiculoId) {
    // Actualizar el estado local sin recargar la página
    setDatos(function(d) {
      if (!d) return d;
      return Object.assign({}, d, {
        vehiculos: d.vehiculos.filter(function(v) { return v.id !== vehiculoId; })
      });
    });
    // Deseleccionar si era el vehículo activo
    setVehiculoSel(function(sel) {
      return (sel && sel.id === vehiculoId) ? null : sel;
    });
  }

  // ── Confirmar eliminación de vehículo ───────────────────────────────────
  //
  // El fetch vive acá (no en TarjetaVehiculo) porque necesita actualizar el
  // estado del padre y mostrar el error de form si falla.
  function confirmarEliminarVehiculo() {
    if (!vehiculoAEliminar) return;
    var url = urlEliminarBase.replace("/0/", "/" + vehiculoAEliminar.id + "/");
    fetch(url, {
      method: "POST",
      headers: { "X-CSRFToken": obtenerCsrf() },
      credentials: "same-origin",
      redirect: "follow",
    }).then(function() {
      eliminarVehiculo(vehiculoAEliminar.id);
      setVehiculoAEliminar(null);
    }).catch(function() {
      setVehiculoAEliminar(null);
      setErrorForm("No se pudo eliminar el vehículo. Intentá de nuevo.");
    });
  }

  // ── Confirmar estacionamiento ────────────────────────────────────────────
  //
  // "sinServicio" (zonaLibre o dia_libre_hoy) → NO se registra.
  //   El botón de confirmar no se muestra en esos casos; este guard es protección extra.
  function confirmar() {
    if (!vehiculoSel) { setErrorForm("Seleccioná un vehículo."); return; }
    if (zonaLibre || (datos && datos.dia_libre_hoy)) return; // guard: no debe llegar acá
    if (!duracionSel) { setErrorForm("Seleccioná una duración."); return; }

    setEnviando(true);
    setErrorForm(null);

    var body = {
      vehiculo_id:       vehiculoSel.id,
      horas:             duracionSel.horas,
      subcuadra_id:      subcuadraId || null,
      conductor_gps_lat: gpsLat || null,
      conductor_gps_lon: gpsLon || null,
    };

    fetch(urlEstacionar, {
      method:  "POST",
      headers: { "Content-Type": "application/json", "X-CSRFToken": obtenerCsrf() },
      body:    JSON.stringify(body),
    })
      .then(function(r) { return r.json(); })
      .then(function(data) {
        if (data.ok) {
          // Redirigir a inicio_usuarios (donde panel_estado verá el estacionamiento nuevo)
          window.location.href = data.redirect_url;
        } else {
          setErrorForm(data.error || "Error al estacionar.");
          setEnviando(false);
        }
      })
      .catch(function() {
        setErrorForm("Error de red. Intentá de nuevo.");
        setEnviando(false);
      });
  }

  // ── Render ───────────────────────────────────────────────────────────────

  // Si el fetch falló, devolvemos null (el fallback Django sigue visible)
  if (errorCarga) return null;
  // Mientras carga, mostrar spinner mínimo (el fallback Django está oculto si ya montó)
  if (!datos) return ce("div", {
    style: { textAlign: "center", padding: "2rem", color: "var(--color-text-muted)" }
  }, "⏳ Cargando...");

  var zonaLibre   = subcuadraTipo === "libre";
  // sinServicio: ningún caso requiere registro (zona libre permanente o día sin inspectores).
  // En ambos casos NO se crea Estacionamiento — el conductor puede circular libremente.
  // Diferencia: dia_libre_hoy aplica a todo el municipio; zonaLibre aplica a una cuadra puntual.
  var sinServicio = zonaLibre || datos.dia_libre_hoy;

  var saldo             = datos.saldo;
  var costoActual       = duracionSel ? duracionSel.costo : 0;
  // Saldo insuficiente solo cuando hay cobro real
  var saldoInsuficiente = !sinServicio && costoActual > saldo;

  var vehiculosRecientes = datos.vehiculos.filter(function(v) { return v.es_reciente; });
  var vehiculosOtros     = datos.vehiculos.filter(function(v) { return !v.es_reciente; });
  var opcionesActuales   = vehiculoSel
    ? (vehiculoSel.tipo === "moto" ? datos.opciones_duracion_moto : datos.opciones_duracion_auto)
    : [];

  // Duración y confirmación solo cuando hay servicio activo
  var mostrarSeccionSubcuadra = vehiculoSel && !vehiculoSel.tiene_abono && datos.subcuadras.length > 0;
  var mostrarSeccionDuracion  = vehiculoSel && !vehiculoSel.tiene_abono && !sinServicio;

  var textoBtnConfirmar = enviando
    ? "⏳ Confirmando..."
    : !vehiculoSel
      ? "✅ Confirmar estacionamiento"
      : duracionSel
        ? "✅ Estacionar " + vehiculoSel.patente + " · " + duracionSel.label + " · $" + Number(duracionSel.costo).toLocaleString("es-AR")
        : "✅ Confirmar estacionamiento";

  return ce("div", null,

    // ── Modal eliminar vehículo ───────────────────────────────────────────
    // Se renderiza sobre todo lo demás cuando el conductor toca ✕ en una tarjeta.
    vehiculoAEliminar && ce(ModalConfirmarEliminar, {
      vehiculo: vehiculoAEliminar,
      onConfirmar: confirmarEliminarVehiculo,
      onCancelar: function() { setVehiculoAEliminar(null); },
    }),

    // ── Saldo disponible ──────────────────────────────────────────────────
    ce("div", {
      style: { display: "flex", justifyContent: "space-between", alignItems: "center", background: "var(--color-surface)", border: "1px solid var(--color-border)", borderRadius: "10px", padding: "0.75rem 1.1rem", marginBottom: "1.2rem" }
    },
      ce("span", { style: { fontSize: "0.9rem", color: "var(--color-text-muted)" } }, "Saldo disponible"),
      ce("span", { style: { fontSize: "1.5rem", fontWeight: "800", color: saldo < 100 ? "var(--color-danger)" : "var(--color-primary)" } },
        "$" + saldo.toFixed(2)
      )
    ),

    // ── Alertas de horario ────────────────────────────────────────────────
    datos.dia_libre_hoy && ce("div", { className: "alert alert-success" },
      "🟢 ", ce("strong", null, "Hoy es día libre."), " No hay inspectores en la vía pública. No necesitás registrar tu estacionamiento."
    ),
    datos.fuera_de_horario && ce("div", { className: "alert alert-warning" },
      "⏰ ", ce("strong", null, "Fuera de horario."), " " + (datos.mensaje_horario || "")
    ),

    // ── Wrapper (opacidad si fuera de horario) ────────────────────────────
    ce("div", {
      style: datos.fuera_de_horario
        ? { pointerEvents: "none", opacity: "0.45", filter: "grayscale(50%)" }
        : {}
    },

      // ── Header vehículos ────────────────────────────────────────────────
      ce("div", { className: "page-header", style: { marginBottom: "0.75rem" } },
        ce("h3", { style: { margin: "0" } }, "🚗🛵 ¿Con qué vehículo?"),
        ce("button", {
          type: "button",
          className: "btn btn-outline",
          onClick: function() { setMostrarAgregar(!mostrarAgregar); },
          style: { fontSize: "0.85rem", padding: "0.4rem 0.85rem" },
        }, mostrarAgregar ? "✕ Cerrar" : "➕ Agregar")
      ),

      // ── Form inline agregar vehículo ────────────────────────────────────
      mostrarAgregar && ce("div", {
        style: { marginBottom: "1.2rem", background: "var(--color-surface-2)", borderRadius: "10px", padding: "0.9rem 1rem" }
      },
        ce("form", {
          method: "post",
          action: urlAgregarVehiculo,
          style: { display: "flex", gap: "0.6rem", alignItems: "flex-end", flexWrap: "wrap" },
        },
          ce("input", { type: "hidden", name: "csrfmiddlewaretoken", value: obtenerCsrf() }),
          ce("div", { style: { flex: "1", minWidth: "140px" } },
            ce("label", { style: { fontSize: "0.82rem", fontWeight: "600", display: "block", marginBottom: "0.2rem" } }, "Patente"),
            ce("input", {
              name: "patente", placeholder: "ABC123", required: true,
              style: { textTransform: "uppercase", letterSpacing: "2px", fontWeight: "700", fontSize: "1.05rem", width: "100%" },
              onInput: function(e) { e.target.value = e.target.value.replace(/[^A-Za-z0-9]/g, "").toUpperCase(); },
            })
          ),
          ce("div", { style: { minWidth: "110px" } },
            ce("label", { style: { fontSize: "0.82rem", fontWeight: "600", display: "block", marginBottom: "0.2rem" } }, "Tipo"),
            ce("select", { name: "tipo", style: { padding: "0.45rem 0.6rem", borderRadius: "6px", border: "1px solid var(--color-border)", background: "var(--color-surface)", fontSize: "0.95rem", width: "100%" } },
              ce("option", { value: "auto" }, "🚗 Auto"),
              ce("option", { value: "moto" }, "🛵 Moto")
            )
          ),
          ce("button", { type: "submit", className: "btn", style: { fontSize: "0.9rem", padding: "0.5rem 1rem" } }, "Agregar")
        )
      ),

      // ── Tarjetas recientes ──────────────────────────────────────────────
      vehiculosRecientes.length > 0 && ce(React.Fragment, null,
        ce("p", { style: { fontSize: "0.8rem", color: "var(--color-text-muted)", margin: "0 0 0.5rem" } }, "Últimos usados"),
        ce("div", {
          id: "tarjetas-vehiculos",
          style: { display: "flex", flexWrap: "wrap", gap: "0.75rem", marginBottom: vehiculosOtros.length > 0 ? "0.4rem" : "1.4rem" }
        },
          vehiculosRecientes.map(function(v) {
            return ce(TarjetaVehiculo, {
              key: v.id, vehiculo: v,
              seleccionado: vehiculoSel && vehiculoSel.id === v.id,
              onSeleccionar: function(sel) { seleccionarVehiculo(sel); },
              onPedirEliminar: function(veh) { setVehiculoAEliminar(veh); },
            });
          })
        )
      ),

      // ── Otros vehículos (colapsados) ────────────────────────────────────
      vehiculosOtros.length > 0 && ce("details", { style: { marginBottom: "1rem" } },
        ce("summary", {
          style: { fontSize: "0.8rem", color: "var(--color-text-muted)", cursor: "pointer", margin: "0.4rem 0", listStyle: "none", userSelect: "none", display: "flex", alignItems: "center", gap: "0.3rem" }
        }, "▸ Otros vehículos"),
        ce("div", { style: { display: "flex", flexWrap: "wrap", gap: "0.75rem", marginTop: "0.5rem" } },
          vehiculosOtros.map(function(v) {
            return ce(TarjetaVehiculo, {
              key: v.id, vehiculo: v,
              seleccionado: vehiculoSel && vehiculoSel.id === v.id,
              onSeleccionar: function(sel) { seleccionarVehiculo(sel); },
              onPedirEliminar: function(veh) { setVehiculoAEliminar(veh); },
            });
          })
        )
      ),

      datos.vehiculos.length === 0 && ce("p", {
        className: "text-muted", style: { marginBottom: "1rem" }
      }, "Todavía no tenés vehículos. Usá el botón ➕ Agregar para empezar."),

      // ── Aviso abono activo ──────────────────────────────────────────────
      vehiculoSel && vehiculoSel.tiene_abono && ce("div", { className: "alert alert-warning" },
        "🗓️ ", ce("strong", null, "Abono mensual activo."), " No debes registrar estacionamiento."
      ),

      // ── Subcuadra (GPS + cascade manual) ────────────────────────────────
      mostrarSeccionSubcuadra && ce(SeccionSubcuadra, {
        subcuadras: datos.subcuadras,
        gpsEstado, subcuadraId,
        calleManual, onSubcuadraChange, onCalleChange,
      }),

      // ── Banner zona libre ─────────────────────────────────────────────────
      // En zona libre NO se crea un Estacionamiento: el conductor puede estacionar
      // sin registrarse. Se muestra la subcuadra detectada/seleccionada claramente
      // para que el conductor pueda verificar que el GPS acertó.
      zonaLibre && vehiculoSel && !vehiculoSel.tiene_abono && ce("div", {
        style: {
          background: "#d4edda", border: "1px solid #c3e6cb", borderRadius: "10px",
          padding: "1rem 1.2rem", marginTop: "0.5rem",
        }
      },
        ce("p", { style: { fontWeight: "700", fontSize: "1.05rem", margin: "0 0 0.3rem", color: "#155724" } },
          "🟢 Zona de estacionamiento libre"
        ),
        subcuadraNombre
          ? ce("p", { style: { margin: "0 0 0.4rem", fontSize: "0.95rem", color: "#155724" } },
              "📍 ", ce("strong", null, subcuadraNombre)
            )
          : ce("p", { style: { margin: "0 0 0.4rem", fontSize: "0.9rem", color: "#155724", fontStyle: "italic" } },
              "Seleccioná la cuadra en el mapa de arriba para confirmar tu ubicación."
            ),
        ce("p", { style: { margin: "0", fontSize: "0.9rem", color: "#155724" } },
          "No necesitás registrar tu vehículo. Podés estacionar sin costo ni trámite."
        )
      ),

      // ── Duración ─────────────────────────────────────────────────────────
      mostrarSeccionDuracion && ce("div", null,
        ce("h3", { style: { marginBottom: "0.75rem" } }, "⏱ ¿Cuánto tiempo?"),
        datos.descuento_pct > 0 && ce("div", { className: "alert alert-success", style: { marginBottom: "0.75rem" } },
          "🏷️ ", ce("strong", null, Math.round(datos.descuento_pct) + "% de descuento"),
          " por ser conductor verificado. Los precios ya incluyen tu descuento."
        ),
        ce(BotoneraDuracion, { opciones: opcionesActuales, seleccionada: duracionSel, onSeleccionar: setDuracionSel })
      ),

      // ── Confirmar ────────────────────────────────────────────────────────
      // No se muestra si no hay servicio (zonaLibre o dia_libre_hoy).
      // El banner correspondiente ya explica que no hace falta registrar.
      vehiculoSel && !vehiculoSel.tiene_abono && !sinServicio && ce("div", null,
        saldoInsuficiente && ce("div", { className: "alert alert-danger", style: { fontWeight: "600" } },
          "⚠️ Saldo insuficiente para esta duración. ",
          ce("a", { href: urlCargaSaldo, style: { color: "var(--color-danger)", textDecoration: "underline" } },
            "Cargá saldo acá."
          )
        ),

        errorForm && ce("div", { className: "alert alert-danger" }, errorForm),

        ce("button", {
          type: "button",
          className: "btn btn-big",
          style: { background: "#28a745", borderColor: "#28a745", marginTop: "0.5rem" },
          disabled: enviando || saldoInsuficiente || !duracionSel,
          onClick: confirmar,
        }, textoBtnConfirmar)
      )
    ) // fin wrapper fuera-de-horario
  );
}

// ── Mount ─────────────────────────────────────────────────────────────────────

(function montarFormularioEstacionar() {
  var el = document.getElementById("formulario-estacionar-react");
  if (!el) return;

  var urlDatos          = el.dataset.urlDatos;
  var urlEstacionar     = el.dataset.urlEstacionar;
  var urlAgregarVehiculo = el.dataset.urlAgregarVehiculo;
  var urlEliminarBase   = el.dataset.urlEliminarBase;
  var urlCargaSaldo     = el.dataset.urlCargaSaldo;
  var patentePresel     = (new URLSearchParams(window.location.search)).get("patente") || "";

  function onMontadoConExito() {
    var fallback = document.getElementById("formulario-estacionar-fallback");
    if (fallback) fallback.style.display = "none";
  }

  var root = ReactDOM.createRoot(el);
  root.render(ce(FormularioEstacionar, {
    urlDatos, urlEstacionar, urlAgregarVehiculo, urlEliminarBase, urlCargaSaldo,
    patentePresel, onMontadoConExito,
  }));
}());
