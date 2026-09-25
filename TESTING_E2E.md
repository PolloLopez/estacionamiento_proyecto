# Testing E2E — Flujo completo de punta a punta
> Sistema de Estacionamiento Medido — Railway: https://estacionamiento.up.railway.app
> Última actualización: 2026-09-24 (sesión 18)

Seguí este archivo en orden. Cada fase depende de la anterior.
Anotá tus observaciones en los espacios `___` — eso es el insumo para la siguiente sesión de mejoras.

> Para referencia detallada de cada flujo: ver `GUIA_TESTING_ROLES.md`.

---

## Configuración de browsers

Abrí **4 ventanas** (o pestañas de incógnito separadas) para no mezclar sesiones:

| Ventana | Rol | URL de inicio |
|---------|-----|---------------|
| A | Superadmin | `/usuarios/superadmin/` |
| B | Admin + Tesorero | `/usuarios/admin-inicio/` |
| C | Inspector + Vendedor | `/usuarios/inspectores/` |
| D | Conductor + Pago público | `/usuarios/` |

---

## FASE 1 — SUPERADMIN: Configurar el municipio `[~10 min]`

> **Ventana A** · Login: superadmin · Ir a `/usuarios/superadmin/`

### 1.1 — Editar municipio y activar flags

1. Ir a "Municipios" → editar el municipio de prueba.
2. Verificar que están activos:
   - [ ] `puede_gestionar_subcuadras` = ✅ activado
   - [ ] `mapa_infracciones_activo` = ✅ activado
   - [ ] `modulo_informes_activo` = según preferencia
3. Verificar tarifas cargadas (precio hora, monto infracción).
4. Guardar → verificar que no hay error 500.

**Qué anotar:**
- Algo confuso en la pantalla de edición: `___`
- Campos faltantes o mal ordenados: `___`

### 1.2 — Verificar panel superadmin

- [ ] El municipio aparece en la lista con estado correcto
- [ ] "Gestionar sugerencias" accesible y sin errores
- [ ] No hay errores visibles en consola (F12)

---

## FASE 2 — ADMIN: Panel, sidebar y herramientas `[~15 min]`

> **Ventana B** · Login: admin@ejemplo.com / Admin.2026

### 2.1 — Panel principal y sidebar 🆕 *sesión 15*

1. Entrar al panel → verificar que el sidebar muestra correctamente:
   - [ ] "📍 Subcuadras" visible (flag activado en Fase 1)
   - [ ] "📊 Cobertura" visible
   - [ ] "🗺️ Mapa de calor" visible
2. Hacer scroll hasta el final del panel.
3. Verificar **footer tutorial**:
   - [ ] Aparece "📖 ¿Cómo usar el panel?" colapsable al pie
   - [ ] Al expandir: muestra los pasos correctos del admin
   - [ ] Aparece "💡 ¿Tenés alguna sugerencia? Enviala acá →"
   - [ ] El link de sugerencias lleva a la página correcta

**Qué anotar:**
- Items del tutorial que no son claros: `___`
- Algo que falta en el tutorial del admin: `___`

### 2.2 — Dashboard 🆕 *sesión 15*

1. Ir a `/usuarios/admin-dashboard/`.
2. Verificar que la sección de cobros dice "**💰 Cobros por vendedores**" (no "por usuario").
   - [ ] Columna dice "Vendedor" (no "Usuario")
3. Verificar que hay una sección "**📋 Infracciones por día**":
   - [ ] Si hay infracciones en el período: muestra tabla con fecha y cantidad
   - [ ] Si no hay: muestra "Sin infracciones en el período"
4. Cambiar el filtro de fechas → verificar que las dos secciones se actualizan.

**Qué anotar:**
- Datos que faltan en el dashboard: `___`
- Algo confuso en el período de fechas: `___`

### 2.3 — Gestionar tarifas y duración mínima 🆕 *sesión 18*

1. Ir a `/usuarios/admin-tarifas/`.
2. Verificar que aparece la sección "Duración mínima de compra":
   - [ ] Muestra el valor actual en minutos (ej: "30 min")
   - [ ] Hay un `<select>` con opciones de 30, 60, 90, ... hasta 480 min
3. Cambiar la duración mínima a **60 min** → guardar.
4. En **Ventana D** (conductor): ir a "🅿️ Estacionar" → verificar que la primera opción de duración es **1 hora** (ya no aparece "30 min").
   - [ ] Primera opción = 1 hora
   - [ ] Opción "30 min" desaparece
5. Volver a `/usuarios/admin-tarifas/` → restaurar a 30 min → verificar que "30 min" vuelve a aparecer para el conductor.
   - [ ] Comportamiento consistente en ambas direcciones

**Qué anotar:**
- La opción de duración mínima fue fácil de encontrar: `[ ] Sí / [ ] No — ___`

### 2.4 — Gestionar vendedores: nombre del negocio 🆕 *sesión 18*

1. Ir a `/usuarios/admin-gestionar-vendedores/`.
2. En el formulario de crear vendedor: verificar que aparece el campo **"Nombre del negocio / punto de venta"**.
   - [ ] El campo existe y tiene placeholder descriptivo
3. Crear (o editar) un vendedor: cargar `nombre_negocio` = "Kiosco Prueba".
4. Verificar que la tabla de vendedores muestra el nombre del negocio como columna principal.
   - [ ] "Kiosco Prueba" visible en la tabla

### 2.6 — Horario activo (crítico para la Fase 3)

> ⚠️ Si el horario no está activo para hoy, el inspector no puede operar. Verificar ahora.

1. Ir a `/usuarios/admin-horarios/` → verificar que hay un horario activo para el día de hoy.
2. Si no hay: crear uno (ej. 08:00–20:00 para hoy).
3. **Anotar el horario activo:** de `___` a `___` hs.
4. El testing de inspector (Fase 3) debe hacerse dentro de ese rango.
   - [ ] Horario confirmado para hoy

### 2.7 — Auditoría de staff `/admin-staff/` 🆕 *sesión 15*

1. Ir a `/usuarios/admin-staff/`.
2. Verificar que se ven **dos tabs**: "💰 Vendedores" y "👮 Inspectores".
   - [ ] Tab por defecto: Vendedores
   - [ ] Cambiar a "Inspectores": la URL cambia a `?tab=inspectores` sin recargar
   - [ ] Recargar la página con `?tab=inspectores`: queda en ese tab
3. Con listas largas: hacer scroll dentro de la tabla.
   - [ ] Los encabezados de columna siguen visibles al hacer scroll (sticky)

**Qué anotar:**
- Algo que confunde en los tabs: `___`

### 2.8 — Módulo desactivado (acceso denegado con estilo) 🆕 *sesión 15*

1. En **Ventana A** (superadmin): desactivar `puede_gestionar_subcuadras` para el municipio.
2. En **Ventana B** (admin): refrescar y verificar que "📍 Subcuadras" **ya no aparece** en el sidebar.
3. Intentar ir a `/usuarios/admin-subcuadras/` directamente.
   - [ ] Aparece página de "🔒 Módulo no habilitado" con estilo (no un 403 en blanco)
   - [ ] Hay un botón "← Volver al panel"
   - [ ] El botón funciona
4. En **Ventana A**: volver a activar el flag.
5. En **Ventana B**: refrescar → "📍 Subcuadras" vuelve a aparecer.
   - [ ] Flujo activar/desactivar funciona correctamente

**Qué anotar:**
- El mensaje de la página bloqueada es claro: `[ ] Sí / [ ] No — ___`

### 2.9 — Seguridad: admin no puede administrar a otro admin 🆕 *sesión 15*

1. Ir a `/usuarios/admin-staff-municipio/` (gestionar staff).
2. Si hay otro admin en la lista: intentar hacer clic en "Editar" o "Resetear contraseña".
   - [ ] El sistema rechaza con un mensaje de error (no permite la acción)
   - [ ] El mensaje es claro (no un 500)
3. Verificar que sí puede editar a un **inspector** o **vendedor** del municipio.
   - [ ] Editar inspector: funciona sin error

**Qué anotar:**
- El mensaje de error al intentar editar a otro admin: `___`

---

## FASE 3 — INSPECTOR: Verificar y multar `[~15 min]`

> **Ventana C** · Login: inspector@ejemplo.com / 12345
> ⚠️ **Hacé esta fase dentro del horario activo** confirmado en el paso 2.3.

### 3.1 — Panel del inspector

1. Entrar a `/usuarios/inspectores/`.
2. Hacer scroll hasta el final.
3. Verificar **footer tutorial**:
   - [ ] "📖 ¿Cómo usar el panel?" al pie, colapsable
   - [ ] Al expandir: muestra los pasos del inspector
   - [ ] "💡 Enviala acá →" link de sugerencias funciona

### 3.2 — Verificar un auto con pago activo

1. Ir a `/usuarios/inspectores/verificar/`.
2. Verificar que el formulario está visible (horario activo ✅).
3. Ingresar la patente `AA123BB` (o la patente que estacionaste en la Fase 2 / una que tengas activa).
   - [ ] El placeholder dice "AAA111" (auto por defecto)
   - [ ] Al completar el patrón: el form se envía solo (auto-submit)
   - [ ] Resultado: caja verde ✅ "Pago activo" o "Abono activo"
   - [ ] Sonido de OK (si hay sonido activado)

### 3.3 — Verificar un auto sin pago → labrar infracción

1. Buscar o tener lista una patente **sin estacionamiento activo** y **sin infracciones pendientes**.
   - Patente de prueba sin pago: `___`
2. Ingresar la patente.
   - [ ] Resultado: caja roja ❌ "Impago" o "No registrado"
   - [ ] Sonido de error + vibración (celular)
3. Completar el acta de infracción:
   - Seleccionar subcuadra: `___`
   - Motivo: `___`
   - Foto: (opcional, testear si sube correctamente)
4. Confirmar la infracción.
   - [ ] El sistema muestra confirmación
   - [ ] La infracción aparece en "Mis infracciones del día"

**Anotar:**
- ¿El flujo de labrar infracción fue claro? `[ ] Sí / [ ] No — ___`
- ¿La foto subió correctamente? `[ ] Sí / [ ] No / [ ] No la probé`

### 3.4 — Verificar una moto 🆕 *sesión 15 (documentado)*

> Formato moto: `123ABC` (3 dígitos + 3 letras). El auto-submit funciona solo si está seleccionado el radio "🏍 Moto" antes de tipear.

1. **Seleccionar radio "🏍 Moto"** (antes de escribir la patente).
   - [ ] El placeholder cambia a "123ABC"
   - [ ] El campo se limpia al cambiar de tipo
2. Tipear `123` (sin las letras).
   - [ ] El botón "🔍 Verificar" aparece debajo del input
3. Tipear las letras `ABC` (completando `123ABC`).
   - [ ] El form se envía automáticamente (auto-submit)
   - [ ] Si no se envió: usar el botón "🔍 Verificar" manualmente — también funciona
4. Cambiar de vuelta a "🚗 Auto" → verificar que el campo se limpia.
   - [ ] Campo vacío al cambiar de tipo

**Qué anotar:**
- ¿El auto-submit de moto funcionó sin botón manual? `[ ] Sí / [ ] No`
- ¿Tuviste que usar el botón manual? `[ ] Sí / [ ] No`

---

## FASE 4 — CONDUCTOR: Estacionar y pagar `[~15 min]`

> **Ventana D** · Login: conductor@ejemplo.com / Cond.12

### 4.1 — Panel del conductor

1. Entrar a `/usuarios/`.
2. Verificar saldo disponible → anotar: `$___`
3. Verificar que aparecen los vehículos vinculados.
   - [ ] Ícono correcto por estado: 🟢 activo / ⚠️ con infracción / 🏷️ exento

### 4.2 — Estacionar (con GPS o manual)

1. Hacer clic en "🅿️ Estacionar".
2. Intentar con GPS: "Detectar mi cuadra".
   - [ ] El spinner aparece mientras detecta
   - [ ] Resultado: muestra nombre de subcuadra (o error de GPS claro)
3. Si GPS falla o no querés usarlo: selección manual (calle → altura).
   - [ ] Al seleccionar una subcuadra **libre**: aparece banner verde, sin formulario de pago
   - [ ] Al seleccionar una subcuadra **pagada**: aparece formulario de duración y precio
4. Seleccionar 1 hora → verificar el precio calculado.
5. Completar el estacionamiento → verificar que el saldo bajó exactamente el precio.
   - Saldo antes: `$___` · Precio mostrado: `$___` · Saldo después: `$___`
   - [ ] Saldo después = Saldo antes − Precio

**Qué anotar:**
- GPS funcionó sin problemas: `[ ] Sí / [ ] No — ___`
- Algo confuso en el flujo de estacionar: `___`

### 4.3 — Ver la infracción labrada por el inspector (Fase 3)

1. Ir a `/usuarios/mis-infracciones/`.
2. Verificar que aparece la infracción labrada en Fase 3.3.
   - [ ] Muestra monto, fecha y estado "pendiente de pago"
   - [ ] Foto visible si se subió una
3. Intentar estacionar el mismo vehículo infraccionado:
   - [ ] El sistema avisa de la infracción pendiente
   - Si está dentro del período de gracia: la infracción se anula automáticamente
   - Si está fuera del período: queda pendiente y el conductor puede estacionar pero con aviso

**Qué anotar:**
- El aviso de infracción pendiente fue claro: `[ ] Sí / [ ] No — ___`

### 4.4 — Pago público `/pagar/` sin login 🆕 *sesión 18*

> El flujo cambió: ahora hay **un solo campo** de patente con un paso de confirmación antes de buscar.

1. Abrir `/usuarios/pagar/` (sin login o en pestaña de incógnito).
2. Tipear menos de 5 caracteres (ej: `AA1`).
   - [ ] El botón "Buscar →" permanece deshabilitado
3. Tipear `AA123BB` (≥ 5 caracteres).
   - [ ] El botón "Buscar →" se habilita
4. Hacer clic en "Buscar →" (NO envía aún).
   - [ ] El campo de patente desaparece
   - [ ] Aparece un bloque verde con la patente en grande: "¿Es correcta la patente?"
   - [ ] Dos botones: "✅ Sí, buscar" y "✏️ Corregir"
5. Hacer clic en "✏️ Corregir".
   - [ ] Vuelve al campo de patente con foco
   - [ ] La patente ingresada sigue cargada para corregirla
6. Corregir a `AA123BC` → "Buscar →" → "✅ Sí, buscar".
   - [ ] Envía el formulario con la patente correcta
   - [ ] Muestra deuda o estado del vehículo

**Qué anotar:**
- El flujo de un campo + confirmación fue más cómodo que antes: `[ ] Sí / [ ] No — ___`
- Algo que confunde en /pagar/: `___`

---

## FASE 5 — VENDEDOR: Cobros en efectivo y cierre de caja `[~15 min]`

> **Ventana C** · Cerrar sesión de inspector → Login: kiosco@ejemplo.com / 12345

### 5.1 — Panel del vendedor

1. Entrar a `/usuarios/vendedores/`.
2. Hacer scroll hasta el final.
3. Verificar **footer tutorial**:
   - [ ] "📖 ¿Cómo usar el panel?" al pie, colapsable
   - [ ] Pasos del tutorial correctos para el vendedor
   - [ ] "💡 Enviala acá →" funciona

### 5.2 — Cargar saldo a un conductor 🆕 *sesión 18*

1. En el panel del vendedor: verificar que existe el botón **"💰 Cargar saldo"**.
   - [ ] Botón visible en el panel
2. Hacer clic → lleva a `/usuarios/vendedores/cargar-saldo/`.
3. Buscar al conductor por **correo**: ingresar el correo del conductor de prueba.
   - [ ] Aparece el nombre y saldo actual del conductor
4. Ingresar monto: `$500` → "✅ Cargar saldo".
   - [ ] Aparece pantalla de comprobante con:
     - Nombre del conductor
     - Monto cargado ($500)
     - Saldo nuevo = saldo anterior + $500
     - "Registrado por": muestra el nombre del negocio del vendedor (si tiene `nombre_negocio` cargado) o su correo
     - Fecha y hora
5. En **Ventana D** (conductor): verificar que el saldo aumentó $500.
   - [ ] Saldo del conductor actualizado correctamente
6. Volver a `/usuarios/vendedores/cargar-saldo/` → buscar por **patente**.
   - [ ] También encuentra al conductor correctamente

**Qué anotar:**
- La búsqueda por correo funcionó: `[ ] Sí / [ ] No — ___`
- La búsqueda por patente funcionó: `[ ] Sí / [ ] No — ___`
- El comprobante mostró el nombre del negocio: `[ ] Sí / [ ] No (solo correo)`

### 5.3 — Registrar estacionamiento en efectivo

1. Hacer clic en "🚗 Registrar estacionamiento".
2. Ingresar patente: `___` (puede ser cualquier patente).
3. Seleccionar zona y duración.
4. Confirmar el cobro.
   - [ ] El movimiento aparece en "Mi caja" del día
   - [ ] El monto es correcto

### 5.4 — Cobrar una infracción con acta reciente → verificar notificación 🆕 *sesión 18*

> Testea el caso donde el conductor paga dentro del período de gracia de una infracción reciente.

**Caso A — pago dentro de la gracia (acta se cancela):**
1. Asegurarse de que el conductor tiene una infracción **reciente** (dentro del período de tolerancia).
2. En Ventana C (vendedor): "⚠️ Cobrar infracción" → ingresar la patente.
3. El sistema cobra el estacionamiento y **cancela el acta automáticamente**.
4. Verificar el ticket de cobro:
   - [ ] Aparece banner naranja/amarillo visible
   - [ ] Ícono ⚠️ grande
   - [ ] Texto "AVISÁ AL CONDUCTOR" en mayúsculas
   - [ ] Subtexto: "↩️ Acta #X cancelada por pago en período permitido"
5. En **Ventana D** (conductor): verificar que la infracción figura como "anulada".
   - [ ] Estado = anulada

**Caso B — pago fuera de la gracia:**
1. Cobrar una infracción **antigua** (fuera del período de tolerancia).
   - [ ] El sistema cobra pero **no cancela** el acta
   - [ ] No aparece el banner naranja
   - [ ] La infracción sigue en estado "pendiente"

**Qué anotar:**
- El banner naranja fue notorio: `[ ] Sí / [ ] No — ___`
- El vendedor entendió que tenía que avisar: `[ ] Sí / [ ] No`

### 5.5 — Ver resumen y cerrar caja

1. Ir a "🧾 Mi caja".
   - [ ] Se ven los movimientos del día con sus montos
   - [ ] El total acumulado es correcto
2. Ir a "📊 Ver resumen" → verificar el desglose.
3. Cerrar la caja.
   - [ ] Aparece confirmación de cierre
   - [ ] El cierre queda en estado "pendiente de certificar"

**Qué anotar:**
- Algo confuso en el cierre de caja: `___`
- Montos incorrectos o faltantes: `___`

---

## FASE 6 — ADMIN: Certificar cierres y crear rendición `[~15 min]`

> **Ventana B** · Ya logueado como admin

### 6.1 — Certificar el cierre del vendedor

1. Ir a `/usuarios/admin-rendiciones/` → tab "① Cierres pendientes".
2. Verificar que aparece el cierre del vendedor (Fase 5.4).
   - [ ] Muestra nombre del vendedor, fecha y monto
3. Hacer clic en "Certificar".
   - [ ] El cierre pasa al tab "② Rendir a tesorería"

### 6.2 — Cerrar caja propia del admin (si aplica)

1. Si el admin también realizó cobros: ir a "Mi caja" y cerrarla.
2. Verificar que el propio cierre del admin **no muestra** el botón "Certificar" (no puede auto-certificarse).
   - [ ] Sin botón "Certificar" en el propio cierre

### 6.3 — Crear rendición a tesorería

1. En el tab "② Rendir a tesorería": seleccionar los cierres a incluir.
2. Crear la rendición.
   - [ ] La rendición aparece en el tab "③ Tesorería"
   - [ ] Las comisiones del vendedor se generaron automáticamente (ver en "💵 Comisiones")
3. Verificar que el monto de comisión del vendedor es correcto:
   - Total cobrado por vendedor: `$___`
   - Porcentaje de comisión: `___`%
   - Comisión esperada: `$___`
   - Comisión generada por el sistema: `$___`
   - [ ] Coinciden

**Qué anotar:**
- Algo confuso en el flujo de rendición: `___`
- Números que no cuadran: `___`

---

## FASE 7 — TESORERO: Validar rendición y depositar comisiones `[~10 min]`

> **Ventana B** · Cerrar sesión de admin → Login: tesoreria@ejemplo.com / Teso.2026

### 7.1 — Panel del tesorero

1. Entrar al panel de tesorero.
2. Verificar las tarjetas de resumen al tope:
   - [ ] "Rendiciones pendientes" muestra la que creó el admin
   - [ ] "Comisiones a depositar" muestra el monto correcto
3. Hacer scroll hasta el final.
4. Verificar **footer tutorial**:
   - [ ] "📖 ¿Cómo usar el panel?" al pie, colapsable
   - [ ] Pasos correctos del tesorero
   - [ ] "💡 Enviala acá →" funciona

### 7.2 — Intentar observar sin notas (validación)

1. Ir a la rendición pendiente → hacer clic en "⚠️ Observar".
2. Dejar el campo de notas vacío y confirmar.
   - [ ] El sistema lo bloquea (el campo se resalta en rojo, no deja enviar)
3. Agregar una nota: "prueba de observación".
   - [ ] Ahora sí permite enviar
   - [ ] La rendición vuelve al admin con estado "observada"
4. Como admin (Ventana B): verificar que la rendición aparece como "observada".
5. Volver como tesorero: re-validar la rendición con "✅ Recibida".
   - [ ] La rendición pasa a "recibida"

### 7.3 — Depositar comisión del vendedor

1. Ir a "💵 Comisiones de vendedores".
2. Verificar que aparece la comisión del vendedor (Fase 6.3).
3. Hacer clic en "💸 Marcar depositada" → completar con comprobante (número de transferencia): `___`
   - [ ] La comisión pasa a estado "depositada"

**Qué anotar:**
- El flujo de validar rendición fue claro: `[ ] Sí / [ ] No — ___`

---

## FASE 8 — VENDEDOR: Confirmar recibo de comisión `[~5 min]`

> **Ventana C** · Login nuevamente como vendedor

### 8.1 — Notificación y confirmación

1. Entrar al panel del vendedor.
   - [ ] Aparece una alerta azul "Tenés comisiones depositadas pendientes de confirmación"
2. Ir a "💼 Mis comisiones".
3. Verificar que aparece la comisión con estado "depositada".
4. Hacer clic en "✅ Confirmar recibo".
   - [ ] La comisión pasa a "certificada"
   - [ ] Desaparece la alerta azul del panel

**Qué anotar:**
- La alerta fue clara y prominente: `[ ] Sí / [ ] No — ___`

---

## FASE 9 — IMPORTAR EXENCIONES (admin) `[~10 min]`

> **Ventana B** · Admin logueado

### 9.1 — Importar Excel de vecinos exentos 🆕 *sesión 15*

> El formato real del Excel tiene **6 columnas** (no 7): Patente · Nombre y Apellido · Dirección · Teléfono · Fecha renovación · Vencimiento.
> **Sin** columna "Condición" — el tipo (global/parcial) lo elegís en el formulario.

1. Ir a `/usuarios/admin-exenciones/` → "Importar vecinos".
2. En el formulario: verificar que aparece el selector de tipo:
   - [ ] Radio "📍 Parcial" (exento en subcuadras específicas)
   - [ ] Radio "🌐 Global" (exento en todo el municipio)
3. Seleccionar **Parcial** (el más común).
4. Subir un Excel con el formato correcto (6 columnas).
5. Verificar que la importación reconoce patentes, nombres y fechas.
   - [ ] Sin errores de formato
   - [ ] Las exenciones aparecen en la lista con vencimiento correcto
6. Intentar con **Global**: seleccionar ese radio y subir el mismo archivo.
   - [ ] Las exenciones se crean como globales

**Qué anotar:**
- Mensaje de error si hay algún problema con el Excel: `___`
- Formato que confundió: `___`

---

## FASE 10 — CASOS BORDE `[~10 min]`

### 10.1 — Inspector fuera del horario activo

1. En **Ventana A** (superadmin o admin): editar el horario para que el cierre sea en 1 minuto.
2. Esperar que el horario venza.
3. En **Ventana C** (inspector): ir a `/usuarios/inspectores/verificar/`.
   - [ ] El formulario no aparece (pantalla de "fuera de horario")
   - [ ] El botón "🔍 Verificar" no existe (era el síntoma reportado en sesión 15)
   - [ ] El placeholder no cambia al seleccionar "Moto" (JS no corre sin el form)
4. Restaurar el horario a la configuración original.

### 10.2 — Saldo insuficiente

1. En **Ventana D** (conductor): verificar el saldo actual.
2. Intentar estacionar por más tiempo del que alcanza el saldo.
   - [ ] El sistema muestra error claro (no se registra el estacionamiento)
   - [ ] El mensaje indica el saldo disponible

### 10.3 — Acceso cruzado entre roles

1. Con la sesión del inspector activa: intentar ir a `/usuarios/admin-inicio/`.
   - [ ] Redirige al panel del inspector (no muestra pantalla de admin)
2. Con la sesión del conductor: intentar ir a `/usuarios/inspectores/`.
   - [ ] Redirige al panel del conductor

### 10.4 — Dark mode

1. Activar modo oscuro en el sistema operativo o en el navegador.
2. Revisar rápidamente: panel admin, inspector y conductor.
   - [ ] No hay textos ilegibles (texto oscuro sobre fondo oscuro)
   - [ ] No hay fondos raros (blanco hardcodeado que rompe el dark mode)
   - [ ] Los badges y alertas se ven correctamente

**Qué anotar:**
- Paneles con problemas visuales en dark mode: `___`

### 10.5 — Mobile (si tenés el celular disponible)

1. Abrir el sistema en el celular (Chrome Android o Safari iOS).
2. Revisar: panel conductor, panel inspector (verificar patente).
   - [ ] Los botones son tocables sin hacer zoom (no muy pequeños)
   - [ ] El input de patente se puede tipear cómodamente
   - [ ] El resultado de verificación se ve completo en pantalla

**Qué anotar:**
- Algo que no se ve bien en mobile: `___`

---

## CHECKLIST FINAL: ¿qué verificar después del testeo?

Cuando terminés las 10 fases, revisá esto antes de reportar:

- [ ] **Ningún error 500** en toda la sesión (revisar logs Railway o Sentry)
- [ ] **Montos de comisión** coinciden en todos los pasos (Fases 5→6→7→8)
- [ ] **Inspector**: las infracciones labradas aparecen en "Mis infracciones del día"
- [ ] **Admin**: el dashboard muestra las infracciones del día (Fase 2.2)
- [ ] **Footer tutorial**: verificado en los 4 roles (admin, inspector, vendedor, tesorero)
- [ ] **Sidebar flags**: activar y desactivar funcionó correctamente (Fase 2.5)
- [ ] **Tabs de auditoría de staff**: sticky headers y URL con tab funcionan (Fase 2.4)
- [ ] **Confirmación de patente en /pagar/**: bloquea con patentes distintas (Fase 4.4)
- [ ] **Importar exenciones**: 6 columnas reconocidas, selector global/parcial funciona (Fase 9)
- [ ] **Cargar saldo (vendedor)**: comprobante muestra `nombre_negocio` + correo entre paréntesis (Fase 5.2) 🆕 *sesión 18*
- [ ] **nombre_negocio en admin**: campo visible en crear/editar vendedor, y en la tabla de gestión (Fase 2.x)  🆕 *sesión 18*
- [ ] **Banner acta cancelada**: banner naranja ⚠️ visible y con texto claro al cobrar infracción dentro de gracia (Fase 5.4) 🆕 *sesión 18*
- [ ] **Ticket de infracción**: impresión térmica con texto más grande (doble alto) funcionó (Fase 3.x) 🆕 *sesión 18*

---

## Observaciones generales

> Completar después del testeo completo.

**¿Qué flujo fue más confuso?**
`___`

**¿Qué mensaje de error fue difícil de entender?**
`___`

**¿Qué pantalla mejorarías?**
`___`

**¿Encontraste algún bug?** (describir: qué hiciste, qué esperabas, qué pasó)
```
Bug 1: ___
Bug 2: ___
Bug 3: ___
```

**¿Algo que no estaba en esta guía y querés que quede documentado?**
`___`

---

*Para la próxima sesión: traé las observaciones de arriba → las convertimos en tareas.*
