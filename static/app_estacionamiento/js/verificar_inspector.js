// verificar_inspector.js
// Fase 5A: verificación de patentes inline para inspectores (sin recargar la página).
//
// El cascade GPS/subcuadra y el modal SIA siguen siendo JS vanilla en el template.
// Este componente maneja: input patente → fetch → resultado → sonidos → historial.
//
// Por qué no reactificamos todo el template:
//   El cascade calle→altura y el modal SIA son complejos y ya funcionan.
//   Reactificarlos en Fase 5A sería sobreingeniería. Fase 5B se encarga del printer.
//
// Integración con el template:
//   - obtenerSubcuadraId() lee el input oculto #subcuadra_sel que el cascade controla.
//   - abrirModalSia() es una función global definida en verificar.html.
//   - Los sonidos son <audio> definidos en el template (ids: "ok", "warn", "error").

(function () {
  "use strict";

  var ce         = React.createElement;
  var useState   = React.useState;
  var useEffect  = React.useEffect;
  var useRef     = React.useRef;

  // ─── BoxResultado ─────────────────────────────────────────────────────────
  // Renderiza el bloque de resultado con el mismo estilo que el template Django.

  function BoxResultado({ data }) {
    var estado = data.estado;  // valor del enum en minúsculas: "impago", "pagado", etc.
    var esMoto  = /^[0-9]{3}[A-Z]{3}$/.test(data.patente);

    var esOk               = estado === "pagado" || estado === "exento_total" || estado === "abono_activo";
    var esInfracReciente   = estado === "infraccion_reciente";
    // Danger: impago, no_registrado, exento_parcial fuera de su zona
    var esDanger           = !esOk && !esInfracReciente;

    var icono    = esOk ? "✅" : esInfracReciente ? "⏱️" : "🚨";
    var boxClass = "box-resultado " + (esOk ? "box-ok" : esInfracReciente ? "box-warn" : "box-danger");

    return ce("div", { className: boxClass },
      ce("div", { style: { fontSize: "2rem" } }, icono),
      ce("h2", { style: { margin: "0.3rem 0" } }, data.patente),
      ce("p", { style: { fontSize: "0.85rem", color: "var(--color-text-muted)", margin: "0.1rem 0" } },
        esMoto ? "🏍️ Moto" : "🚗 Auto"
      ),
      ce("h3", null, data.estado_label),

      // Tiempo restante para poder volver a infraccionar (solo INFRACCION_RECIENTE)
      esInfracReciente && data.minutos_hasta_siguiente
        ? ce("p", { style: { fontSize: "0.9rem", color: "var(--color-text-muted)" } },
            "Podés volver a infraccionar en aprox. ",
            ce("strong", null, String(data.minutos_hasta_siguiente) + " min"), "."
          )
        : null,

      // Botón SIA: permite que el inspector verifique la exención antes de infraccionar
      esDanger
        ? ce("button", {
            type: "button",
            className: "btn btn-outline",
            style: {
              marginBottom: "0.5rem", padding: "0.4rem 0.9rem", fontSize: "0.85rem",
              borderColor: "var(--color-text-muted)", color: "var(--color-text-muted)",
            },
            onClick: function () {
              // abrirModalSia() es una función global definida en verificar.html
              if (typeof abrirModalSia === "function") abrirModalSia(data.patente);
            },
          }, "♿ SIA")
        : null,

      // Botón INFRACCIONAR — solo si la lógica de negocio lo habilita
      data.necesita_infraccion && data.registrar_infraccion_url
        ? ce("a", {
            className: "btn btn-danger btn-big",
            href: data.registrar_infraccion_url,
          }, "🚨 INFRACCIONAR")
        : null
    );
  }

  // ─── VerificadorInspector ─────────────────────────────────────────────────

  function VerificadorInspector({ urlVerificar }) {
    var [patente,   setPatente]   = useState("");
    var [cargando,  setCargando]  = useState(false);
    var [resultado, setResultado] = useState(null);
    var [errorMsg,  setErrorMsg]  = useState(null);
    var [historial, setHistorial] = useState([]);
    var inputRef = useRef(null);

    // Enfocar el input al montar para que el inspector pueda empezar a tipear de inmediato
    useEffect(function () {
      if (inputRef.current) inputRef.current.focus();
    }, []);

    // Leer el token CSRF de la cookie (mismo patrón que los otros componentes React del sistema)
    function obtenerCsrf() {
      var cookie = document.cookie.split(";").find(function (c) {
        return c.trim().startsWith("csrftoken=");
      });
      return cookie ? cookie.trim().split("=")[1] : "";
    }

    // Obtener el id de la subcuadra seleccionada en el cascade calle→altura del template
    function obtenerSubcuadraId() {
      var el = document.getElementById("subcuadra_sel");
      return el ? (parseInt(el.value, 10) || null) : null;
    }

    // Reproducir el sonido correspondiente al estado del vehículo
    function reproducirSonido(data) {
      try {
        var estado = data.estado;
        if (
          estado === "impago" ||
          estado === "no_registrado" ||
          (estado === "exento_parcial" && !data.exento_en_subcuadra_actual)
        ) {
          document.getElementById("error").play();
          if (navigator.vibrate) navigator.vibrate([200, 100, 200]);
        } else if (estado === "infraccion_reciente") {
          document.getElementById("warn").play();
          if (navigator.vibrate) navigator.vibrate(100);
        } else {
          // pagado, exento_total, abono_activo, exento_parcial en su subcuadra
          document.getElementById("ok").play();
        }
      } catch (e) {
        // El audio puede fallar por política de autoplay del browser — no es bloqueante
      }
    }

    // Verificar una patente contra la API del inspector
    function verificar(patenteParam) {
      var p = (patenteParam !== undefined ? patenteParam : patente).trim();
      if (!p || cargando) return;

      setCargando(true);
      setResultado(null);
      setErrorMsg(null);

      fetch(urlVerificar, {
        method: "POST",
        headers: {
          "Content-Type": "application/json",
          "X-CSRFToken": obtenerCsrf(),
        },
        credentials: "same-origin",
        body: JSON.stringify({
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
          // Agregar al historial (máx 5, sin duplicados)
          setHistorial(function (prev) {
            var nuevo = [data.patente].concat(
              prev.filter(function (h) { return h !== data.patente; })
            );
            return nuevo.slice(0, 5);
          });
          reproducirSonido(data);
          // Limpiar el input y devolver el foco para la próxima verificación
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

      // Auto-submit al completar un formato de patente válido (igual que el template Django)
      //   AAA111  — autos anteriores al Mercosur
      //   AA111BB — autos Mercosur
      //   123ABC  — motos
      var esValida =
        /^[A-Z]{3}[0-9]{3}$/.test(val) ||
        /^[A-Z]{2}[0-9]{3}[A-Z]{2}$/.test(val) ||
        /^[0-9]{3}[A-Z]{3}$/.test(val);

      if (esValida) verificar(val);
    }

    function manejarKeydown(e) {
      if (e.key === "Enter") { e.preventDefault(); verificar(); }
    }

    return ce("div", null,
      // Input de patente (mismo estilo que el template Django)
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

      // Botón de verificación manual — aparece al escribir ≥3 caracteres
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

      // Indicador de carga
      cargando
        ? ce("p", {
            style: { textAlign: "center", color: "var(--color-text-muted)", marginTop: "0.5rem" }
          }, "⏳ Verificando…")
        : null,

      // Mensaje de error (horario, conexión, etc.)
      errorMsg
        ? ce("div", {
            style: {
              marginTop: "0.75rem", padding: "0.8rem", borderRadius: "8px",
              background: "#f8d7da", color: "#721c24", border: "1px solid #f5c6cb",
              fontSize: "0.9rem", textAlign: "center",
            },
          }, errorMsg)
        : null,

      // Resultado de la verificación
      resultado ? ce(BoxResultado, { data: resultado }) : null,

      // Historial de patentes verificadas en esta sesión (últimas 5)
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
  // Se monta en el div#verificar-inspector-react del template verificar.html.
  // El div hereda el id="contenedor-patente" del wrapper para que el cascade
  // JS (aplicarZonaLibreInspector) siga mostrando/ocultando el área correctamente.

  document.addEventListener("DOMContentLoaded", function () {
    var contenedor = document.getElementById("verificar-inspector-react");
    if (!contenedor) return;

    ReactDOM.render(
      ce(VerificadorInspector, { urlVerificar: contenedor.dataset.urlVerificar }),
      contenedor
    );
  });

})();
