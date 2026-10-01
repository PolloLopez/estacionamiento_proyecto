// verificar_inspector.js
// Fase 5A + 5B: verificación + infracción + impresión inline para inspectores.
//
// Sin redirect entre verificar → infraccionar → imprimir.
// La sesión BLE de la impresora térmica sobrevive todo el flujo porque
// Chrome pierde getDevices() al navegar entre páginas (bug conocido),
// y este componente evita esa navegación.
//
// Fases del componente (estado "fase"):
//   "verificar"   → input de patente + resultado (Fase 5A)
//   "formulario"  → foto + subcuadra + GPS + botón grabar acta (Fase 5B)
//   "ticket"      → confirmación + impresión BLE (Fase 5B)
//
// Integración con el template verificar.html:
//   - obtenerSubcuadraId() lee #subcuadra_sel (controlado por el cascade JS vanilla)
//   - abrirModalSia() función global definida en verificar.html
//   - SUBCUADRAS_INS array global definido en verificar.html (para el selector de subcuadra en formulario)
//   - Los sonidos son <audio> definidos en el template (ids: "ok", "warn", "error")
//   - Las funciones BLE son globales de impresora_bluetooth.js (cargado en verificar.html)

(function () {
  "use strict";

  var ce        = React.createElement;
  var useState  = React.useState;
  var useEffect = React.useEffect;
  var useRef    = React.useRef;

  // ─── Helpers comunes ──────────────────────────────────────────────────────

  function obtenerCsrf() {
    var cookie = document.cookie.split(";").find(function (c) {
      return c.trim().startsWith("csrftoken=");
    });
    return cookie ? cookie.trim().split("=")[1] : "";
  }

  function obtenerSubcuadraId() {
    var el = document.getElementById("subcuadra_sel");
    return el ? (parseInt(el.value, 10) || null) : null;
  }

  function reproducirSonido(tipo) {
    try { document.getElementById(tipo).play(); } catch (e) {}
  }

  // ─── BoxResultado ─────────────────────────────────────────────────────────
  // Renderiza el bloque de resultado después de verificar una patente.

  function BoxResultado({ data, onInfraccionar }) {
    var estado = data.estado;
    var esMoto = /^[0-9]{3}[A-Z]{3}$/.test(data.patente);

    var esOk             = estado === "pagado" || estado === "exento_total" || estado === "abono_activo";
    var esInfracReciente = estado === "infraccion_reciente";
    var esDanger         = !esOk && !esInfracReciente;

    var icono    = esOk ? "✅" : esInfracReciente ? "⏱️" : "🚨";
    var boxClass = "box-resultado " + (esOk ? "box-ok" : esInfracReciente ? "box-warn" : "box-danger");

    return ce("div", { className: boxClass },
      ce("div", { style: { fontSize: "2rem" } }, icono),
      ce("h2", { style: { margin: "0.3rem 0" } }, data.patente),
      ce("p", { style: { fontSize: "0.85rem", color: "var(--color-text-muted)", margin: "0.1rem 0" } },
        esMoto ? "🏍️ Moto" : "🚗 Auto"
      ),
      ce("h3", null, data.estado_label),

      esInfracReciente && data.minutos_hasta_siguiente
        ? ce("p", { style: { fontSize: "0.9rem", color: "var(--color-text-muted)" } },
            "Podés volver a infraccionar en aprox. ",
            ce("strong", null, String(data.minutos_hasta_siguiente) + " min"), "."
          )
        : null,

      // Botón SIA: verifica exención antes de infraccionar
      esDanger
        ? ce("button", {
            type: "button",
            className: "btn btn-outline",
            style: {
              marginBottom: "0.5rem", padding: "0.4rem 0.9rem", fontSize: "0.85rem",
              borderColor: "var(--color-text-muted)", color: "var(--color-text-muted)",
            },
            onClick: function () {
              if (typeof abrirModalSia === "function") abrirModalSia(data.patente);
            },
          }, "♿ SIA")
        : null,

      // Botón INFRACCIONAR → no navega, abre formulario inline (Fase 5B)
      data.necesita_infraccion
        ? ce("button", {
            type:      "button",
            className: "btn btn-danger btn-big",
            onClick:   onInfraccionar,
          }, "🚨 INFRACCIONAR")
        : null
    );
  }

  // ─── GpsChip ──────────────────────────────────────────────────────────────
  // Chip de estado GPS reutilizable.

  function GpsChip({ lat, lon, acc, gpsEstado }) {
    if (gpsEstado === "desactivado") return null;

    var textoChip, chipClass;
    if (gpsEstado === "esperando") {
      textoChip = "⏳ Obteniendo ubicación…";
      chipClass = "gps-chip esperando";
    } else if (gpsEstado === "ok") {
      textoChip = "📍 " + lat + ", " + lon + " ±" + acc + "m";
      chipClass = "gps-chip";
    } else {
      textoChip = "⚠️ Sin ubicación — foto sin marca GPS";
      chipClass = "gps-chip error";
    }

    return ce("span", { className: chipClass, style: { display: "inline-block", marginBottom: "0.5rem" } },
      textoChip
    );
  }

  // ─── FormularioInfraccion ─────────────────────────────────────────────────
  // Paso 2: foto + subcuadra + GPS → POST API → datos_acta

  function FormularioInfraccion({ patente, urlRegistrar, geolocActiva, onCancelar, onExito }) {
    var [foto,      setFoto]      = useState(null);    // File
    var [fotoUrl,   setFotoUrl]   = useState(null);    // preview URL
    var [enviando,  setEnviando]  = useState(false);
    var [error,     setError]     = useState(null);
    var [gpsLat,    setGpsLat]    = useState(null);
    var [gpsLon,    setGpsLon]    = useState(null);
    var [gpsAcc,    setGpsAcc]    = useState(null);
    var [gpsEstado, setGpsEstado] = useState(geolocActiva ? "esperando" : "desactivado");
    var fotoInputRef = useRef(null);

    // Solicitar GPS al montar (si el superadmin lo habilitó para este municipio)
    useEffect(function () {
      if (!geolocActiva || !navigator.geolocation) {
        if (geolocActiva) setGpsEstado("error");
        return;
      }
      navigator.geolocation.getCurrentPosition(
        function (pos) {
          setGpsLat(pos.coords.latitude.toFixed(5));
          setGpsLon(pos.coords.longitude.toFixed(5));
          setGpsAcc(Math.round(pos.coords.accuracy));
          setGpsEstado("ok");
        },
        function () { setGpsEstado("error"); },
        { enableHighAccuracy: true, timeout: 10000, maximumAge: 0 }
      );
    }, []);

    function manejarFoto(e) {
      var archivo = e.target.files && e.target.files[0];
      if (!archivo) return;
      setFoto(archivo);
      setFotoUrl(URL.createObjectURL(archivo));
    }

    function retomar() {
      // Limpiar foto y volver a abrir la cámara
      setFoto(null);
      setFotoUrl(null);
      setTimeout(function () {
        if (fotoInputRef.current) fotoInputRef.current.click();
      }, 50);
    }

    function enviar() {
      var subcuadraId = obtenerSubcuadraId();
      if (!subcuadraId) {
        setError("Seleccioná la subcuadra (calle y altura) antes de infraccionar.");
        return;
      }
      if (!foto) {
        setError("Tomá una foto del vehículo antes de infraccionar.");
        return;
      }

      setEnviando(true);
      setError(null);

      var fd = new FormData();
      fd.append("patente",      patente);
      fd.append("subcuadra_id", String(subcuadraId));
      fd.append("foto",         foto);
      if (gpsEstado === "ok") {
        fd.append("gps_lat", gpsLat);
        fd.append("gps_lon", gpsLon);
        fd.append("gps_acc", String(gpsAcc));
      }

      // Nota: NO pongas Content-Type en los headers cuando usás FormData.
      // El browser lo hace automáticamente con el boundary correcto.
      fetch(urlRegistrar, {
        method:      "POST",
        headers:     { "X-CSRFToken": obtenerCsrf() },
        credentials: "same-origin",
        body:        fd,
      })
        .then(function (r) { return r.json(); })
        .then(function (data) {
          setEnviando(false);
          if (!data.ok) {
            setError(data.error || "No se pudo registrar el acta.");
            return;
          }
          onExito(data.datos_acta);
        })
        .catch(function () {
          setEnviando(false);
          setError("Error de conexión. Verificá la red.");
        });
    }

    return ce("div", { style: { marginTop: "0.5rem" } },

      // Encabezado: patente grande (no editable) + botón cancelar
      ce("div", { style: { display: "flex", alignItems: "center", justifyContent: "space-between", marginBottom: "0.75rem" } },
        ce("h2", { style: { margin: 0, letterSpacing: "3px" } }, "🚨 " + patente),
        ce("button", {
          type:    "button",
          onClick: onCancelar,
          style: {
            background: "none", border: "1px solid var(--color-border)",
            borderRadius: "6px", padding: "0.3rem 0.7rem",
            fontSize: "0.85rem", cursor: "pointer", color: "var(--color-text-muted)",
          },
        }, "✕ Cancelar")
      ),

      // GPS chip
      ce(GpsChip, { lat: gpsLat, lon: gpsLon, acc: gpsAcc, gpsEstado: gpsEstado }),

      // Foto: input oculto + botón custom
      ce("input", {
        ref:      fotoInputRef,
        type:     "file",
        accept:   "image/*",
        capture:  "environment",
        style:    { display: "none" },
        onChange: manejarFoto,
      }),

      !fotoUrl
        ? ce("button", {
            type:    "button",
            onClick: function () { if (fotoInputRef.current) fotoInputRef.current.click(); },
            style: {
              width: "100%", padding: "0.9rem", marginBottom: "0.75rem",
              fontSize: "1rem", fontWeight: "700", cursor: "pointer",
              border: "2px dashed var(--color-border)", borderRadius: "10px",
              background: "var(--color-surface)", color: "var(--color-text)",
            },
          }, "📷 Tomar foto")
        : ce("div", { style: { marginBottom: "0.75rem", textAlign: "center" } },
            ce("img", {
              src:   fotoUrl,
              alt:   "Vista previa",
              style: { maxWidth: "100%", maxHeight: "200px", borderRadius: "8px",
                       border: "2px solid var(--color-border)" },
            }),
            ce("div", { style: { marginTop: "0.4rem" } },
              ce("button", {
                type:    "button",
                onClick: retomar,
                style: {
                  fontSize: "0.85rem", padding: "0.3rem 0.8rem", cursor: "pointer",
                  background: "none", border: "1px solid var(--color-border)",
                  borderRadius: "6px", color: "var(--color-text-muted)",
                },
              }, "🔄 Retomar foto")
            )
          ),

      // Error
      error
        ? ce("div", {
            style: {
              marginBottom: "0.75rem", padding: "0.75rem", borderRadius: "8px",
              background: "#f8d7da", color: "#721c24", border: "1px solid #f5c6cb",
              fontSize: "0.9rem", textAlign: "center",
            },
          }, error)
        : null,

      // Botón grabar
      ce("button", {
        type:     "button",
        onClick:  enviar,
        disabled: enviando,
        className: "btn btn-danger btn-grabar",
        style: { width: "100%", opacity: enviando ? "0.7" : "1" },
      }, enviando ? "⏳ Grabando acta…" : "🚨 Grabar acta de infracción")
    );
  }

  // ─── ModalTicket ──────────────────────────────────────────────────────────
  // Paso 3: confirmación + impresión BLE inline.
  // Usa los globales de impresora_bluetooth.js:
  //   generarTicketInfraccion(d)  → Uint8Array ESC/POS
  //   reconectarImpresora()       → conexion | null  (silencioso, sin diálogo)
  //   reconectarSilencioso()      → conexion | null  (watchAdvertisements)
  //   conectarImpresora()         → conexion          (abre diálogo BLE — requiere gesto)
  //   enviarImpresion(carac, bytes)
  //   obtenerInfoImpresora()      → { alias, name } | null
  //   nombreMostrar(device)       → string

  function ModalTicket({ datosActa, onNuevaVerificacion }) {
    var [estadoImpresion, setEstadoImpresion] = useState("");
    var [textoBoton,      setTextoBoton]      = useState("");
    var [botonVisible,    setBotonVisible]    = useState(false);
    var [botonDesabled,   setBotonDisabled]   = useState(false);

    // Refs para la lógica async (evita closures sobre state stale)
    var bytesRef      = useRef(null);        // Uint8Array del ticket
    var copia1EnvRef  = useRef(false);       // si ya se envió la copia 1
    var onClickRef    = useRef(null);        // handler actual del botón de reintento

    useEffect(function () {
      intentarAutoImprimir();
    }, []);

    // ── intentarAutoImprimir ────────────────────────────────────────────────
    // Igual que en ticket_infraccion.html pero usando setters de estado React.
    // getDevices() es silencioso (no requiere gesto del usuario).
    // Si encuentra el dispositivo → llama a ejecutarImpresion() automáticamente.
    // Si no → muestra botón para que el inspector lo inicie con un click (gesto válido).
    async function intentarAutoImprimir() {
      if (!navigator.bluetooth) {
        setEstadoImpresion("⚠️ Impresión BLE no disponible. Usá Chrome en Android.");
        setTextoBoton("📱 Necesitás Chrome en Android");
        setBotonVisible(true);
        setBotonDisabled(true);
        return;
      }

      var dispositivoGuardado = null;
      if (typeof navigator.bluetooth.getDevices === "function") {
        try {
          var devs = await navigator.bluetooth.getDevices();
          if (devs.length) dispositivoGuardado = devs[0];
        } catch (e) {
          console.warn("[BLE] getDevices falló en auto-load:", e.message);
        }
      }

      if (dispositivoGuardado) {
        // Chrome tiene la impresora en su lista de permisos → reconexión silenciosa
        var nombre = (typeof nombreMostrar === "function")
          ? nombreMostrar(dispositivoGuardado) : "";
        setEstadoImpresion("⏳ Buscando " + (nombre || "impresora") + "…");
        ejecutarImpresion();
      } else {
        // getDevices() vacío (bug Chrome post-navegación) → necesitamos gesto del usuario
        var infoGuardada = (typeof obtenerInfoImpresora === "function") ? obtenerInfoImpresora() : null;
        var nombreLabel = infoGuardada ? (infoGuardada.alias || infoGuardada.name || "") : "";
        setEstadoImpresion("🖨 Tocá para imprimir el acta");
        setTextoBoton(nombreLabel ? ("🖨 Conectar " + nombreLabel) : "🖨 Imprimir acta");
        setBotonVisible(true);
        setBotonDisabled(false);
        onClickRef.current = ejecutarImpresion;
      }
    }

    // ── ejecutarImpresion ───────────────────────────────────────────────────
    // Misma lógica que imprimirActa() en ticket_infraccion.html.
    // Imprime 2 copias con reconexión fresca entre ellas.
    async function ejecutarImpresion() {
      setBotonDisabled(true);
      setBotonVisible(false);
      setEstadoImpresion("");
      copia1EnvRef.current = false;

      // 1. Reconexión silenciosa
      var conexion = null;
      try {
        setEstadoImpresion("⏳ Buscando impresora…");
        conexion = await reconectarImpresora();
      } catch (e) {
        console.warn("[BLE] reconectar falló:", e.message);
      }

      // 2. Si la reconexión silenciosa falló → diálogo (requiere gesto del usuario)
      if (!conexion) {
        try {
          var infoGuardada = (typeof obtenerInfoImpresora === "function") ? obtenerInfoImpresora() : null;
          var nombreConocido = infoGuardada ? (infoGuardada.alias || infoGuardada.name || "") : "";
          setEstadoImpresion(nombreConocido
            ? "📡 Seleccioná \"" + nombreConocido + "\" en el diálogo…"
            : "📡 Seleccioná la impresora en el diálogo…");
          conexion = await conectarImpresora();
        } catch (e) {
          setEstadoImpresion("❌ " + (e.message || "No se pudo conectar a la impresora."));
          setTextoBoton("🔄 Reintentar impresión");
          setBotonVisible(true);
          setBotonDisabled(false);
          onClickRef.current = ejecutarImpresion;
          return;
        }
      }

      // 3. Generar bytes del ticket (una sola vez para ambas copias)
      var bytes;
      try {
        bytes = generarTicketInfraccion(datosActa);
        bytesRef.current = bytes;
      } catch (e) {
        setEstadoImpresion("❌ Error al generar el ticket: " + e.message);
        setTextoBoton("🔄 Reintentar");
        setBotonVisible(true);
        setBotonDisabled(false);
        onClickRef.current = ejecutarImpresion;
        return;
      }

      // 4. Enviar copia 1 + pausa + copia 2
      try {
        setEstadoImpresion("⏳ Imprimiendo copia 1 de 2…");
        await enviarImpresion(conexion.caracteristica, bytes);
        copia1EnvRef.current = true;

        // Desconectar después de copia 1 para que la impresora avance el papel
        try { conexion.device.gatt.disconnect(); } catch (_) {}

        // Pausa entre copias: configurable en segundos (0 = confirmación manual)
        var pausaSegundos = datosActa.segundos_pausa_copias || 0;
        if (pausaSegundos > 0) {
          for (var seg = pausaSegundos; seg > 0; seg--) {
            setEstadoImpresion("⏳ Esperando " + seg + "s para copia 2…");
            await new Promise(function (r) { setTimeout(r, 1000); });
          }
        } else {
          // Confirmación manual: el inspector decide cuándo imprimir la copia 2
          setEstadoImpresion("✋ Retirá la copia 1 y tocá para imprimir la copia 2.");
          setTextoBoton("🖨 Imprimir copia 2");
          setBotonVisible(true);
          setBotonDisabled(false);
          await new Promise(function (resolver) {
            onClickRef.current = function () {
              setBotonDisabled(true);
              resolver();
            };
          });
          onClickRef.current = ejecutarImpresion;  // restaurar para catch posterior
        }

        // Reconexión fresca antes de copia 2 (800ms de pausa para evitar disconnect race)
        setEstadoImpresion("⏳ Reconectando para copia 2…");
        await new Promise(function (r) { setTimeout(r, 800); });
        var reconCopia2 = await reconectarSilencioso();
        if (!reconCopia2) {
          throw new Error("Impresora no encontrada para la copia 2. Usá el botón de reintento.");
        }
        conexion = reconCopia2;

        setEstadoImpresion("⏳ Imprimiendo copia 2 de 2…");
        await enviarImpresion(conexion.caracteristica, bytes);
        conexion.device.gatt.disconnect();
        setEstadoImpresion("✅ 2 copias enviadas a la impresora.");
        setBotonVisible(false);

      } catch (e) {
        console.warn("[BLE] envío falló:", e.message);

        if (copia1EnvRef.current) {
          // Copia 1 llegó; solo falló la copia 2 → ofrecer reintentar solo la 2
          setEstadoImpresion("✅ Copia 1 enviada. ❌ Copia 2 no se pudo enviar.");
          setTextoBoton("🔄 Reintentar copia 2");
          setBotonVisible(true);
          setBotonDisabled(false);
          onClickRef.current = async function () {
            setBotonDisabled(true);
            setEstadoImpresion("⏳ Buscando impresora…");
            try {
              var cx = await reconectarImpresora();
              if (!cx) {
                setEstadoImpresion("📡 Seleccioná la impresora en el diálogo…");
                cx = await conectarImpresora();
              }
              setEstadoImpresion("⏳ Enviando copia 2…");
              await enviarImpresion(cx.caracteristica, bytesRef.current);
              cx.device.gatt.disconnect();
              setEstadoImpresion("✅ Copia 2 enviada.");
              setBotonVisible(false);
            } catch (eR) {
              setEstadoImpresion("❌ Copia 2 falló: " + (eR.message || "Error desconocido"));
              setBotonDisabled(false);
            }
          };
        } else {
          // Error total: ni la copia 1 se envió
          setEstadoImpresion("❌ Error al enviar: " + e.message);
          setTextoBoton("🔄 Reintentar impresión");
          setBotonVisible(true);
          setBotonDisabled(false);
          onClickRef.current = ejecutarImpresion;
        }
      }
    }

    return ce("div", { style: { marginTop: "0.5rem" } },

      // Confirmación: acta guardada en el sistema (siempre visible)
      ce("div", {
        style: {
          background: "#d4edda", border: "1px solid #c3e6cb",
          borderRadius: "10px", padding: "1rem", textAlign: "center",
          marginBottom: "1rem",
        },
      },
        ce("div", { style: { fontSize: "2rem" } }, "✅"),
        ce("h3", { style: { margin: "0.3rem 0" } }, "Acta N° " + datosActa.acta + " registrada"),
        ce("p", { style: { margin: "0.1rem 0", fontSize: "0.9rem", fontWeight: "700", letterSpacing: "2px" } },
          datosActa.patente
        ),
        ce("p", { style: { margin: "0.1rem 0", fontSize: "0.85rem", color: "#155724" } },
          datosActa.subcuadra + " — $" + datosActa.monto
        )
      ),

      // Estado de la impresión
      estadoImpresion
        ? ce("p", {
            style: { textAlign: "center", fontWeight: "600", margin: "0 0 0.75rem", color: "#333" }
          }, estadoImpresion)
        : null,

      // Botón de acción de impresión (reintento, copia 2, conectar, etc.)
      botonVisible
        ? ce("button", {
            type:     "button",
            disabled: botonDesabled,
            onClick:  function () { if (onClickRef.current) onClickRef.current(); },
            className: "btn btn-outline",
            style: {
              width: "100%", marginBottom: "0.75rem",
              opacity: botonDesabled ? "0.7" : "1",
            },
          }, textoBoton)
        : null,

      // Botón para volver a verificar otra patente
      ce("button", {
        type:      "button",
        onClick:   onNuevaVerificacion,
        className: "btn",
        style: {
          width: "100%", background: "var(--color-primary)", color: "white",
          border: "none", borderRadius: "8px", padding: "0.8rem",
          fontSize: "1rem", fontWeight: "700", cursor: "pointer",
        },
      }, "🔍 Nueva verificación")
    );
  }

  // ─── VerificadorInspector ─────────────────────────────────────────────────
  // Componente raíz. Gestiona la "fase" del flujo del inspector.

  function VerificadorInspector({ urlVerificar, urlRegistrar, geolocActiva }) {
    var [fase,      setFase]      = useState("verificar");
    var [patente,   setPatente]   = useState("");
    var [cargando,  setCargando]  = useState(false);
    var [resultado, setResultado] = useState(null);
    var [errorMsg,  setErrorMsg]  = useState(null);
    var [historial, setHistorial] = useState([]);
    var [datosActa, setDatosActa] = useState(null);  // para ModalTicket
    var inputRef = useRef(null);

    // Enfocar el input al montar
    useEffect(function () {
      if (inputRef.current) inputRef.current.focus();
    }, []);

    // ── Verificar patente (Fase 5A) ─────────────────────────────────────────

    function verificar(patenteParam) {
      var p = (patenteParam !== undefined ? patenteParam : patente).trim();
      if (!p || cargando) return;

      setCargando(true);
      setResultado(null);
      setErrorMsg(null);

      fetch(urlVerificar, {
        method:      "POST",
        headers: {
          "Content-Type": "application/json",
          "X-CSRFToken":  obtenerCsrf(),
        },
        credentials: "same-origin",
        body:        JSON.stringify({
          patente:      p,
          subcuadra_id: obtenerSubcuadraId(),
        }),
      })
        .then(function (r) { return r.json(); })
        .then(function (data) {
          setCargando(false);
          if (!data.ok) {
            setErrorMsg(data.error || "No se pudo verificar.");
            return;
          }
          setResultado(data);
          // Historial: máx 5, sin duplicados
          setHistorial(function (prev) {
            return [data.patente].concat(
              prev.filter(function (h) { return h !== data.patente; })
            ).slice(0, 5);
          });
          // Sonidos + vibración según estado
          var estado = data.estado;
          if (estado === "impago" || estado === "no_registrado" ||
              (estado === "exento_parcial" && !data.exento_en_subcuadra_actual)) {
            reproducirSonido("error");
            if (navigator.vibrate) navigator.vibrate([200, 100, 200]);
          } else if (estado === "infraccion_reciente") {
            reproducirSonido("warn");
            if (navigator.vibrate) navigator.vibrate(100);
          } else {
            reproducirSonido("ok");
          }
          setPatente("");
          setTimeout(function () {
            if (inputRef.current) inputRef.current.focus();
          }, 200);
        })
        .catch(function () {
          setCargando(false);
          setErrorMsg("Error de conexión. Verificá la red.");
        });
    }

    function manejarInput(e) {
      var val = e.target.value.toUpperCase().replace(/[^A-Z0-9]/g, "");
      setPatente(val);
      var esValida =
        /^[A-Z]{3}[0-9]{3}$/.test(val) ||
        /^[A-Z]{2}[0-9]{3}[A-Z]{2}$/.test(val) ||
        /^[0-9]{3}[A-Z]{3}$/.test(val);
      if (esValida) verificar(val);
    }

    function manejarKeydown(e) {
      if (e.key === "Enter") { e.preventDefault(); verificar(); }
    }

    // ── Callbacks de fase ───────────────────────────────────────────────────

    function iniciarFormulario() {
      setFase("formulario");
    }

    function cancelarFormulario() {
      setFase("verificar");
      setTimeout(function () {
        if (inputRef.current) inputRef.current.focus();
      }, 100);
    }

    function recibirTicket(datos) {
      setDatosActa(datos);
      setFase("ticket");
    }

    function nuevaVerificacion() {
      setFase("verificar");
      setResultado(null);
      setPatente("");
      setDatosActa(null);
      setTimeout(function () {
        if (inputRef.current) inputRef.current.focus();
      }, 100);
    }

    // ── Render ──────────────────────────────────────────────────────────────

    // FASE: ticket (impresión inline, sin redirect)
    if (fase === "ticket" && datosActa) {
      return ce(ModalTicket, {
        datosActa:          datosActa,
        onNuevaVerificacion: nuevaVerificacion,
      });
    }

    // FASE: formulario (foto + subcuadra + GPS)
    if (fase === "formulario" && resultado) {
      return ce(FormularioInfraccion, {
        patente:      resultado.patente,
        urlRegistrar: urlRegistrar,
        geolocActiva: geolocActiva,
        onCancelar:   cancelarFormulario,
        onExito:      recibirTicket,
      });
    }

    // FASE: verificar (input + resultado + historial)
    return ce("div", null,
      ce("input", {
        ref:          inputRef,
        value:        patente,
        onChange:     manejarInput,
        onKeyDown:    manejarKeydown,
        className:    "input-patente",
        placeholder:  "AAA111 / AA111BB / 123ABC",
        autoComplete: "off",
        disabled:     cargando,
      }),

      !cargando && patente.length >= 3
        ? ce("button", {
            type:  "button",
            style: {
              width: "100%", marginTop: "0.5rem", padding: "0.7rem",
              fontSize: "1rem", background: "var(--color-primary)", color: "white",
              border: "none", borderRadius: "8px", cursor: "pointer", fontWeight: "600",
            },
            onClick: function () { verificar(); },
          }, "🔍 Verificar")
        : null,

      cargando
        ? ce("p", {
            style: { textAlign: "center", color: "var(--color-text-muted)", marginTop: "0.5rem" }
          }, "⏳ Verificando…")
        : null,

      errorMsg
        ? ce("div", {
            style: {
              marginTop: "0.75rem", padding: "0.8rem", borderRadius: "8px",
              background: "#f8d7da", color: "#721c24", border: "1px solid #f5c6cb",
              fontSize: "0.9rem", textAlign: "center",
            },
          }, errorMsg)
        : null,

      resultado
        ? ce(BoxResultado, { data: resultado, onInfraccionar: iniciarFormulario })
        : null,

      historial.length > 0
        ? ce("div", { style: { marginTop: "1.2rem", textAlign: "left" } },
            ce("p", {
              style: { fontSize: "0.8rem", color: "var(--color-text-muted)", marginBottom: "0.4rem" }
            }, "Recientes:"),
            historial.map(function (p) {
              return ce("button", {
                key:     p,
                onClick: function () { verificar(p); },
                style: {
                  margin: "2px", padding: "4px 10px", fontSize: "0.9rem",
                  letterSpacing: "2px", background: "var(--color-surface)",
                  border: "1px solid var(--color-border)", borderRadius: "6px",
                  cursor: "pointer", fontWeight: "700",
                },
              }, p);
            })
          )
        : null
    );
  }

  // ─── Mount ────────────────────────────────────────────────────────────────
  document.addEventListener("DOMContentLoaded", function () {
    var contenedor = document.getElementById("verificar-inspector-react");
    if (!contenedor) return;

    ReactDOM.render(
      ce(VerificadorInspector, {
        urlVerificar: contenedor.dataset.urlVerificar,
        urlRegistrar: contenedor.dataset.urlRegistrar,
        // "true" / "false" como string desde data-* del template
        geolocActiva: contenedor.dataset.geoloc === "true",
      }),
      contenedor
    );
  });

})();
