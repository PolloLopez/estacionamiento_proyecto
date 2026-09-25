# Smoke test V1.0.1 — Presentación municipal
> Railway: https://estacionamiento.up.railway.app  
> Última actualización: 2026-09-25 (sesión 19)

Recorrido rápido de los 5 flujos críticos. Duración estimada: 20 min.  
Hacelo todo en una sola sesión con el mismo usuario de prueba.

---

## Preparación (2 min)

Antes de arrancar, abrí **3 ventanas/tabs separados** (incógnito funciona bien):

| Ventana | Rol | URL |
|---------|-----|-----|
| A | Admin | `/usuarios/admin-inicio/` |
| B | Inspector | `/usuarios/inspectores/` |
| C | Conductor | `/usuarios/` |

**Usuarios de prueba** (Railway):
- Admin: `admin@ejemplo.com` / `Admin.2026`
- Inspector: el que tengas cargado
- Conductor: el que tengas cargado

**Verificar antes de empezar:**
- [ ] Hay un horario activo para hoy (Admin → `/usuarios/admin-horarios/`). Si no hay, crealo (ej. 08:00–22:00).
- [ ] El conductor tiene saldo suficiente (mínimo $500 en su billetera del municipio). Si no, acreditale en el flujo 2.

---

## Flujo 1 — Verificar vehículo (inspector) `[3 min]`


> Ventana B — Inspector

1. Ir a "Verificar vehículo" (`/usuarios/verificar/`).
2. Ingresar la patente del conductor de prueba.
3. Esperar resultado.

**Qué verificar:**
- [ ] Aparece el resultado (OK / IMPAGO / EXENTO) sin error 500.
- [ ] Si el vehículo está al día: aparece ✅ con datos del estacionamiento activo o "Sin estacionamiento activo".
- [ ] La subcuadra y la altura se ven correctamente (si el inspector tiene subcuadras asignadas).

**Qué anotar:**
- Algo confuso en la pantalla: `_Todo verde!  ✅__`

---

## Flujo 2 — Acreditar saldo (vendedor o admin) `[3 min]`

> Ventana A — Admin, o usar un vendedor si tenés uno cargado

1. Admin → "Gestionar conductores" → buscá el conductor de prueba.
2. En el detalle, usá el formulario de recarga de saldo (si está disponible en el panel admin).
   - Alternativa: que el propio conductor recargue con MercadoPago (`/usuarios/recargar/`).
3. Verificar que el saldo se acreditó.

**Qué verificar:**
- [ ] El saldo nuevo aparece en la billetera del conductor.
- [ ] Si lo hizo el conductor: el botón de MercadoPago funciona (aunque sea en sandbox).

**Qué anotar:**
- ¿El flujo fue intuitivo para el conductor? `_/vendedores/cargar-saldo/ falta imprimir comprobante__`
---

## Flujo 3 — Estacionar (conductor) `[5 min]`

> Ventana C — Conductor

1. Ir a "🅿️ Estacionar" (`/usuarios/estacionar/`).
2. Seleccionar el vehículo (de los recientes o del desplegable de "Otros vehículos").
3. Seleccionar la ubicación:
   - Probar el botón **GPS** (azul) para detectar automáticamente.
   - O seleccionar calle/altura manualmente — verificar que la altura muestra la referencia "entre calles".
4. Elegir duración: **30 min** (primera opción).
   - [ ] El botón de duración seleccionada se ve en **azul sólido** (distinto al botón GPS).
5. Confirmar con el botón verde "✅ Confirmar estacionamiento".

**Qué verificar:**
- [ ] El botón GPS es azul contorneado; la duración seleccionada es azul sólido; Confirmar es verde. Los tres son visualmente distintos.
- [ ] La altura en el selector muestra número + entre calles (ej. "500 — Entre Av. San Martín y Belgrano").
- [ ] Después de confirmar: redirige al inicio y muestra el timer activo.
- [ ] En el inicio: aparece "📍 [subcuadra] · **hasta HH:MM**" con el botón 🔄 Renovar al lado.
- [ ] "Otros vehículos vinculados" está colapsado por defecto (se expande con clic).

**Qué anotar:**
- ¿El conductor entendió qué botón tocar primero? `_Todo verde!  ✅
 mejorar notificacion. # ── Notificacion de infraccion detectada al estacionar ──__`
---

## Flujo 4 — Generar infracción (inspector) `[4 min]`

> Ventana B — Inspector

1. Esperar que el estacionamiento del flujo 3 venza (o crear uno con poco tiempo).
   - Alternativa rápida: verificar un vehículo **diferente** que esté sin estacionamiento activo.
2. En "Verificar vehículo", ingresar la patente del vehículo impago.
3. Si aparece 🚨 IMPAGO → hacer clic en "Infraccionar".
4. Completar el formulario: subcuadra + altura + foto (opcional).
5. Confirmar la infracción.

**Qué verificar:**
- [ ] El botón de infraccionar solo aparece cuando corresponde (IMPAGO, fuera de tolerancia).
- [ ] El acta se genera correctamente con patente y timestamp.
- [ ] El conductor (Ventana C) ve la infracción en "Mis infracciones".

**Qué anotar:**
- ¿El formulario de infracción fue rápido de completar en el celular? `__el formulario Rapido. Sigue roto el flujo de vincular impresora para cada impresion _`

---

## Flujo 5 — Pagar infracción (conductor) `[3 min]`

> Ventana C — Conductor

1. Ir a "Mis infracciones" (`/usuarios/mis-infracciones/`).
2. Ver la infracción del flujo 4 (estado: Pendiente).
3. Hacer clic en "Pagar" → confirmar el pago con saldo.

**Qué verificar:**
- [ ] La infracción aparece con estado "Pendiente" y el monto correcto.
- [ ] Después de pagar: el estado cambia a "Pagada".
- [ ] El saldo del conductor se redujo correctamente.

**Qué anotar:**
- ¿El flujo de pago fue claro? `__{% block title %}Agregar vehículo{% endblock %} Agregar - sin diseño_`
---

## Flujo 6 — Renovar / cancelar estacionamiento `[3 min]`

> Ventana C — Conductor (con un estacionamiento activo nuevo)

**6a. Renovar:**
1. Con el estacionamiento activo en el inicio, hacer clic en 🔄 Renovar (al lado de "hasta HH:MM").
2. Elegir 30 min adicionales.
3. Confirmar.

- [ ] Las opciones de renovar incluyen fracciones de 30 min (30 min, 1 h, 1:30 h...).
- [ ] El nuevo horario de vencimiento se actualiza en el timer del inicio.

**6b. Cancelar:**
1. Ir a "Mis estacionamientos" → ver el activo.
2. Si hay botón de cancelar: usarlo.
   - (Si no hay opción de cancelar desde el conductor: anotar para el admin.)

- [ ] El estacionamiento puede cancelarse (o queda claro que no se puede y por qué).
- [ mejorar estilo: 
<button type="submit" class="btn btn-danger" style="font-size:0.78rem; padding:0.2rem 0.5rem;"
 onclick="return confirm('¿Finalizar {{ est.vehiculo.patente }}?\nEl costo ya fue descontado al inicio.')">⛔</button>
renovar_estacionamiento.html
if (saldo >= costo) {
        previewDiv.style.background = "var(--color-success-bg)";
        previewDiv.style.color = "var(--color-success)";
        previewDiv.innerHTML = "+" + label + " · Costo: $<strong>" + costo.toFixed(2) +
          "</strong> · Nuevo vencimiento: <strong>" + finStr + "</strong>";
 onclick="return confirm('¿Finalizar {{ est.vehiculo.patente }}?\nEl costo ya fue descontado al inicio.')">⛔</button>
        btnConfirmar.disabled = false;
        
        no calcula bien el nuevo final de estacionamiento cuando suma fracciones de 30 mintos, en horas enteras --- ]

## ¿Qué hacer si algo falla?

| Síntoma | Dónde mirar |
|---------|-------------|
| Error 500 | `python manage.py shell` + reproducir / logs en Railway |
| Saldo no se debita | `debitar_saldo_conductor()` en `use_cases/estacionar_vehiculo.py` |
| Timer no muestra "hasta HH:MM" | JS en `inicio_usuarios.html` — función que calcula `horaVencStr` |
| Botones todos iguales | `.duracion-activa` en `estacionar_vehiculo.html` |
| Inspector no puede infraccionar | Verificar horario activo para hoy en admin |
| Renovar no muestra 30 min | `views_usuarios.py::renovar_estacionamiento` — `duracion_minima_min` |

---

## Resultado esperado

Si los 6 flujos pasan sin error 500 y con el comportamiento descrito: **V1.0.1 lista para presentar**.

Anotá todo lo raro en los `___` de cada paso — eso es el insumo de la próxima sesión.
