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

const ce = React.createElement;
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

function TarjetaVehiculo({ vehiculo, seleccionado, onSeleccionar, urlEliminarBase }) {
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
    if (!confirm("¿Eliminar " + vehiculo.patente + " de tu cuenta?")) return;
    var url = urlEliminarBase.replace("/0/", "/" + vehiculo.id + "/");
    var form = document.createElement("form");
    form.method = "POST";
    form.action = url;
    var csrf = document.createElement("input");
    csrf.type = "hidden";
    csrf.name = "csrfmiddlewaretoken";
    csrf.value = obtenerCsrf();
    form.appendChild(csrf);
    document.body.appendChild(form);
    form.submit();
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

// ── SeccionSubcuadra ──────────────────────────────────────────────────────────

function SeccionSubcuadra({
  subcuadras, selectorManualActivo,
  gpsEstado, subcuadraId, subcuadraNombre,
  calleManual, alturaManual,
  onSubcuadraChange, onCalleChange, onAlturaChange,
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

  var subcuadrasFiltradas = calleManual
    ? subcuadras.filter(function(s) { return s.calle === calleManual; })
    : [];

  var labelTexto = "📡 Detectando tu cuadra…";
  if (gpsEstado === "detectado") labelTexto = "📍 " + subcuadraNombre;
  if (gpsEstado === "fallo")     labelTexto = "No pudimos detectar tu ubicación — seleccioná manualmente:";

  var mostrarManual = selectorManualActivo && gpsEstado === "fallo";

  return ce("div", { style: { marginBottom: "1.2rem" } },
    ce("h3", { style: { marginBottom: "0.4rem" } }, "📍 ¿Dónde estás?"),
    ce("p", {
      style: { fontSize: "0.82rem", color: "var(--color-text-muted)", margin: "0 0 0.4rem", display: "flex", alignItems: "center", gap: "0.4rem" }
    }, labelTexto),

    // Selector principal de subcuadra
    ce("select", {
      value: subcuadraId || "",
      onChange: function(e) {
        var id = Number(e.target.value) || null;
        var sub = id ? subcuadras.find(function(s) { return s.id === id; }) : null;
        onSubcuadraChange(id, sub);
      },
      style: { width: "100%", padding: "0.55rem 0.75rem", borderRadius: "8px", border: "1px solid var(--color-border)", fontSize: "1rem", background: "var(--color-surface)" },
    },
      ce("option", { value: "" }, "— Sin informar zona —"),
      subcuadras.map(function(s) {
        var label = s.calle + " " + s.altura + (s.entre ? " — " + s.entre : "");
        return ce("option", { key: s.id, value: s.id }, label);
      })
    ),

    // Selector manual (calle + altura) si GPS falló y está habilitado por superadmin
    mostrarManual && ce("div", {
      style: { marginTop: "0.6rem", background: "var(--color-surface-2)", borderRadius: "8px", padding: "0.65rem 0.85rem" }
    },
      ce("div", { style: { display: "flex", gap: "0.5rem", flexWrap: "wrap" } },
        ce("input", {
          list: "list-calles-react",
          placeholder: "Calle…",
          value: calleManual,
          onChange: function(e) { onCalleChange(e.target.value); },
          autoComplete: "off",
          style: { flex: "2", minWidth: "130px", padding: "0.5rem 0.65rem", borderRadius: "6px", border: "1px solid var(--color-border)", fontSize: "1rem", background: "var(--color-surface)" },
        }),
        ce("datalist", { id: "list-calles-react" },
          callesUnicas.map(function(c) { return ce("option", { key: c, value: c }); })
        ),
        ce("input", {
          list: "list-alturas-react",
          placeholder: "Altura",
          value: alturaManual,
          disabled: !calleManual,
          onChange: function(e) { onAlturaChange(e.target.value, subcuadrasFiltradas); },
          inputMode: "numeric",
          autoComplete: "off",
          style: { flex: "1", minWidth: "80px", padding: "0.5rem 0.65rem", borderRadius: "6px", border: "1px solid var(--color-border)", fontSize: "1rem", background: "var(--color-surface)" },
        }),
        ce("datalist", { id: "list-alturas-react" },
          subcuadrasFiltradas.map(function(s) {
            var label = s.entre ? (s.altura ? s.altura + " — " + s.entre : s.entre) : String(s.altura);
            return ce("option", { key: s.id, value: label });
          })
        )
      )
    )
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
      setSubcuadraNombre(subcuadra.calle + " " + subcuadra.altura);
    } else {
      setSubcuadraTipo("paga");
    }
    // Al cambiar subcuadra manualmente, limpiar la duración seleccionada
    // solo si cambió a zona libre (para que el botón confirmar se actualice)
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

  function onAlturaChange(texto, subcuadrasFiltradas) {
    setAlturaManual(texto);
    if (!texto || !subcuadrasFiltradas.length) return;
    var alturaNum = parseInt(texto, 10);
    // Buscar coincidencia exacta primero, luego altura numérica, luego más cercana
    var sub = subcuadrasFiltradas.find(function(s) {
      var label = s.entre ? (s.altura ? s.altura + " — " + s.entre : s.entre) : String(s.altura);
      return label === texto;
    });
    if (!sub) sub = subcuadrasFiltradas.find(function(s) { return !isNaN(alturaNum) && s.altura === alturaNum; });
    if (!sub && !isNaN(alturaNum) && subcuadrasFiltradas.length > 0) {
      sub = subcuadrasFiltradas.reduce(function(prev, curr) {
        return Math.abs(curr.altura - alturaNum) < Math.abs(prev.altura - alturaNum) ? curr : prev;
      });
    }
    if (sub) {
      setSubcuadraId(sub.id);
      setSubcuadraTipo(sub.tipo_zona || "paga");
    }
  }

  // ── Confirmar estacionamiento ────────────────────────────────────────────
  function confirmar() {
    if (!vehiculoSel) { setErrorForm("Seleccioná un vehículo."); return; }
    var esLibreTotal = zonaLibre || (datos && datos.dia_libre_hoy);
    if (!esLibreTotal && !duracionSel) { setErrorForm("Seleccioná una duración."); return; }

    setEnviando(true);
    setErrorForm(null);

    var body = {
      vehiculo_id:       vehiculoSel.id,
      horas:             esLibreTotal ? 1 : duracionSel.horas,
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

  var zonaLibre         = subcuadraTipo === "libre";
  var esLibreTotal      = zonaLibre || datos.dia_libre_hoy;
  var saldo             = datos.saldo;
  var costoActual       = duracionSel ? duracionSel.costo : 0;
  var saldoInsuficiente = !esLibreTotal && costoActual > saldo;

  var vehiculosRecientes = datos.vehiculos.filter(function(v) { return v.es_reciente; });
  var vehiculosOtros     = datos.vehiculos.filter(function(v) { return !v.es_reciente; });
  var opcionesActuales   = vehiculoSel
    ? (vehiculoSel.tipo === "moto" ? datos.opciones_duracion_moto : datos.opciones_duracion_auto)
    : [];

  var mostrarSeccionSubcuadra = vehiculoSel && !vehiculoSel.tiene_abono && datos.subcuadras.length > 0;
  var mostrarSeccionDuracion  = vehiculoSel && !vehiculoSel.tiene_abono && !zonaLibre;

  var textoBtnConfirmar = enviando
    ? "⏳ Confirmando..."
    : (duracionSel && !esLibreTotal
        ? "✅ " + vehiculoSel.patente + " — $" + duracionSel.costo.toFixed(2)
        : "✅ Confirmar estacionamiento");

  return ce("div", null,

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
      "🟢 ", ce("strong", null, "Hoy no hay cobro."), " Podés registrar el estacionamiento sin costo ($0)."
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
              urlEliminarBase: urlEliminarBase,
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
              urlEliminarBase: urlEliminarBase,
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
        subcuadras:           datos.subcuadras,
        selectorManualActivo: datos.selector_manual_activo,
        gpsEstado, subcuadraId, subcuadraNombre,
        calleManual, alturaManual,
        onSubcuadraChange, onCalleChange, onAlturaChange,
      }),

      // ── Banner zona libre ────────────────────────────────────────────────
      zonaLibre && vehiculoSel && !vehiculoSel.tiene_abono && ce("div", { className: "alert alert-success" },
        "🟢 ", ce("strong", null, "Zona de estacionamiento libre."), " No hay cobro en esta área."
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

      // ── Resumen + Confirmar ───────────────────────────────────────────────
      vehiculoSel && !vehiculoSel.tiene_abono && ce("div", null,
        ce("div", {
          className: "resumen",
          style: { display: "flex", justifyContent: "space-between", alignItems: "center" }
        },
          ce("span", { style: { fontSize: "1rem", color: "var(--color-text-muted)" } },
            ce("strong", null, vehiculoSel.patente),
            " · ",
            ce("span", null, esLibreTotal ? "Sin costo" : (duracionSel ? duracionSel.label : "—"))
          ),
          ce("span", { style: { fontSize: "1.4rem", fontWeight: "800", color: "var(--color-primary)" } },
            esLibreTotal ? "$0.00" : (duracionSel ? "$" + duracionSel.costo.toFixed(2) : "—")
          )
        ),

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
          disabled: enviando || saldoInsuficiente || (!esLibreTotal && !duracionSel),
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
