# Auditoría UX/UI — Sistema de Estacionamiento
Fecha: 2026-07-24  
Templates revisados: `base.html`, `login.html`, `registro.html`, `inicio_usuarios.html`,
`estacionar_vehiculo.html`, `solicitar_verificacion.html`, `panel_inspectores.html`,
`verificar.html`, `registrar_infraccion.html`, `panel.html` (vendedores),
`registrar_estacionamiento.html`, `panel_admin.html`

---

## Resumen ejecutivo

El sistema tiene una base sólida para uso en campo: tipografías grandes, botones táctiles
cómodos, feedback sonoro + háptico en el verificador del inspector, y excelente progressive
disclosure en el formulario de exención. Los tres problemas de mayor fricción son puntuales y
tienen fix de pocas líneas cada uno. El resto son ajustes opcionales de bajo riesgo.

---

## Los 3 problemas de mayor fricción

### 1. Login: el correo se pierde si la contraseña es incorrecta

**Dónde:** `templates/usuarios/login.html` — línea 16.

**Qué pasa:** el `<input type="email">` no tiene atributo `value`. Cuando el login falla,
Django re-renderiza la página con el formulario vacío y el conductor tiene que escribir su correo
de nuevo. Todos los roles pasan por esta pantalla.

Además: los `<label>` no tienen atributo `for` y los `<input>` no tienen `id`, por lo que no
están asociados entre sí. Tocar el label no enfoca el input (accessibility básica).

**Fix aplicado:**
```html
<!-- label sin for → con for -->
<label for="id_correo">Correo</label>
<input type="email" id="id_correo" name="correo"
       value="{{ request.POST.correo|default:'' }}" required
       placeholder="tucorreo@ejemplo.com">

<label for="id_password">Contraseña</label>
<input type="password" id="id_password" name="password" required>
```

---

### 2. Sin feedback de carga al enviar formularios críticos

**Dónde:** todos los formularios del sistema — en especial `registrar_infraccion.html` y
`estacionar_vehiculo.html`, usados en campo con datos móviles.

**Qué pasa:** el usuario toca "Confirmar" y el botón no cambia. Si la conexión tarda 2-3
segundos (frecuente en 4G/3G en calle), la persona toca el botón de nuevo pensando que no
respondió. Riesgo de doble submit en acciones irreversibles (registrar infracción, cobrar).

**Fix aplicado en `base.html`:** un listener global que al hacer submit deshabilita el botón
con un texto "Enviando..." — solo si el botón no estaba ya disabled (no interfiere con el
botón del GPS pendiente en registrar_infraccion.html).

```javascript
// En base.html, al final del <script> existente
document.addEventListener("submit", function(e) {
  var btn = e.target.querySelector("[type='submit']:not([disabled])");
  if (!btn) return;
  var textoOriginal = btn.textContent;
  btn.disabled = true;
  btn.textContent = "Enviando…";
  // Re-habilitar tras 10 s por si el server tarda o hay error de red
  setTimeout(function() {
    btn.disabled = false;
    btn.textContent = textoOriginal;
  }, 10000);
});
```

---

### 3. El conductor no ve aviso de saldo insuficiente antes de intentar estacionar

**Dónde:** `templates/usuarios/estacionar_vehiculo.html` — botones de duración.

**Qué pasa:** el saldo se muestra en la parte superior de la pantalla (bien, y en rojo si
< $100), pero cuando el conductor elige una duración cuyo costo supera su saldo, el botón
"Confirmar estacionamiento" se habilita igual. El conductor toca "Confirmar", el servidor
rechaza con error, y recién ahí se entera. Un check en JS evita el viaje al servidor y muestra
el aviso en el momento en que elige la duración.

**Fix aplicado:** agregar `SALDO_CONDUCTOR` como constante JS y en el handler del botón de
duración, mostrar un warning inline y deshabilitar "Confirmar" si el costo supera el saldo.

---

## Mejoras opcionales (por pantalla)

### Login

- Botón "Ingresar con Google" solo tiene texto, sin ícono de Google. No rompe nada, pero el
  ícono da señal visual más rápida en mobile.
- No hay `placeholder` en el campo correo en la versión actual (ya agregado en el fix del
  problema 1).

### Registro (`registro.html`)

- El campo "Apellido" no tiene asterisco `*` ni texto "(opcional)", pero tampoco tiene
  atributo `required`. Ambiguo para el usuario. Consistencia: usar el patrón de
  `solicitar_verificacion.html` que marca opcionales explícitamente.
- El bloque de errores genérico (`form.errors`) aparece arriba del formulario sin señalar qué
  campo falló. El patrón de mostrar errores por debajo del campo correspondiente (ya presente
  en los campos de contraseña) debería extenderse a nombre y correo.

### Inspector — Panel (`panel_inspectores.html`)

- Solo muestra "Infracciones hoy". Si el inspector tiene un cierre de caja sin certificar,
  no lo sabe desde su panel (el panel de vendedor sí muestra esta advertencia).
  Mejora: agregar el bloque de cierres pendientes, igual al que ya existe en `panel.html`.

### Inspector — Verificar (`verificar.html`)

✅ Muy bien logrado: campo de patente en 3rem, historial clickeable de recientes, audio +
vibración háptica, resultado visual con colores claros y tipografía grande. No tocar.

### Inspector — Registrar infracción (`registrar_infraccion.html`)

✅ GPS chip con tres estados (esperando / ok / error), botón deshabilitado hasta GPS resuelto.
Buen diseño preventivo.

### Vendedor — Panel (`panel.html`)

- 4 tarjetas de stats con clase `grid-3`: el 4to card queda solo en su fila, visualmente
  descolgado. Cambiar a `grid-2` lo agrupa en 2×2, más balanceado.
- Sin cambios de lógica, solo de clase CSS.

### Conductor — Solicitar verificación (`solicitar_verificacion.html`)

✅ Progressive disclosure del checkbox de exención, ayuda contextual según tipo, "✅ Ya
adjunto" para documentos previos, validación de required solo en inputs visibles. Muy bien.

### Conductor — Inicio (`inicio_usuarios.html`)

✅ Timer JS del estacionamiento activo, warning de saldo < $100, banners de verificación.
Buen uso de estados secundarios.

### Admin — Panel (`panel_admin.html`)

✅ Sidebar sticky con badges de contadores en gestión, filas clickeables en tabla de
infracciones. Eficiente para uso en desktop.

### Global (`base.html`) — mensajes del sistema

Los mensajes de Django (`messages`) usan colores hardcodeados como inline styles
(`background:#d4edda`, etc.) en vez de las variables CSS del sistema (`--color-success-bg`,
`--color-primary-light`, etc.). Si un municipio tiene un color primario muy distinto del verde
por defecto, los mensajes de success pueden verse discordantes.
Mejora menor: migrar los colores de mensajes a clases en `global.css` que usen las variables.

---

## Qué está bien (no tocar)

- **Inspector verificar.html** — feedback multimodal (visual + audio + háptico) para trabajo
  en campo: excelente.
- **solicitar_verificacion.html** — progressive disclosure del checkbox + required dinámico por
  tipo de documento: el mejor formulario del sistema.
- **estacionar_vehiculo.html** — autoselección del vehículo único, cards visuales de patente,
  sección "Agregar vehículo" en `<details>` para no contaminar el flujo principal.
- **base.html** — hamburger con Escape, backdrop, aria-expanded: accesibilidad del menú bien
  cubierta.
- **Tipografía general** — `1.05rem` base, `font-size:1.3rem+` en patentes y montos críticos:
  adecuado para uso al sol con guantes o manos mojadas.
- **Colores de alerta** — verde/amarillo/rojo consistentes en todos los roles con el sistema
  de variables del municipio.

---

## Fixes aplicados en esta sesión

| Fix | Archivo | Impacto |
|-----|---------|---------|
| Email persiste en login fallido + labels con `for` | `login.html` | Todos los roles |
| Feedback "Enviando…" global en submit | `base.html` | Todos los formularios |
| Warning de saldo insuficiente en estacionar | `estacionar_vehiculo.html` | Conductores |
