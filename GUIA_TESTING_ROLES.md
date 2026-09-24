# Guía de testing completo por rol
> Sistema de Estacionamiento Medido — Railway: https://estacionamiento.up.railway.app
> Última actualización: 2026-09-22

Esta guía cubre cada rol con: flujos a testear paso a paso, qué verificar en cada pantalla, y un cuestionario de experiencia de usuario (UX) para registrar observaciones durante la prueba.

**Antes de empezar:** tener al menos un municipio configurado con tarifa, horario activo y subcuadras cargadas.

---

## Credenciales del ambiente Railway (demo)

> ⚠️ Estas son las credenciales del ambiente de prueba en Railway. No son datos de producción real.

| Rol | Email | Contraseña |
|-----|-------|-----------|
| Admin municipal | admin@ejemplo.com | Admin.2026 |
| Tesorero | tesoreria@ejemplo.com | Teso.2026 |
| Vendedor / Kiosco | kiosco@ejemplo.com | 12345 |
| Inspector | inspector@ejemplo.com | 12345 |
| Conductor | conductor@ejemplo.com | Cond.12 |

Tener una patente de prueba lista (ej: `AA123BB`) que NO tenga infracciones pendientes.

---

## ROL 1: Conductor

**URL de entrada:** `/usuarios/` (redirige desde login)

### Flujos a testear

#### F1.1 — Registrar estacionamiento con saldo
1. Ir a `/usuarios/` → ver panel con saldo actual y vehículos vinculados.
2. Clic en "Estacionar".
3. Hacer clic en el botón "Detectar mi cuadra" → esperar el spinner de detección.
4. Verificar que muestre el nombre de la subcuadra detectada.
5. Si la subcuadra es libre → verificar que aparece el **banner verde** "Zona de estacionamiento libre" y que el formulario de pago queda oculto.
6. Si la subcuadra es pagada → seleccionar duración → ver precio calculado.
7. Completar el estacionamiento. Verificar que el saldo disminuyó.
8. Volver al panel → verificar que aparece el estacionamiento activo con temporizador.

**Qué verificar:**
- [ ] GPS detecta subcuadra correctamente (o muestra error si no hay permiso de ubicación)
- [ ] Zona libre: el formulario de pago se oculta y aparece el botón "Confirmar ubicación"
- [ ] Zona libre: al confirmar, aparece mensaje "Podés estacionar sin pagar" (sin llamar al backend)
- [ ] Zona pagada: el precio se calcula correctamente según tarifa del municipio
- [ ] El saldo se debita exactamente (no más, no menos)
- [ ] El estacionamiento activo aparece en el panel con tiempo restante

#### F1.2 — Selección manual en cascada (sin GPS)
1. En el formulario de estacionar, seleccionar calle desde el dropdown.
2. Seleccionar altura.
3. Verificar que si la subcuadra seleccionada es **libre**, aparece el banner verde (sin hacer submit del formulario).
4. Verificar que si es **pagada**, aparece el formulario de duración/precio.

**Qué verificar:**
- [ ] Al cambiar calle, el selector de altura se repopula solo
- [ ] Al seleccionar altura, el sistema detecta el tipo_zona inmediatamente (sin recargar)
- [ ] Zona libre: banner verde aparece, formulario de pago desaparece
- [ ] Zona pagada: formulario de pago aparece, banner oculto

#### F1.3 — Cargar saldo con MercadoPago
1. Ir a `/usuarios/mp/cargar/`.
2. Ingresar un monto (ej: $1000).
3. Verificar que redirige a la pantalla de pago de MP.
4. Completar el pago (en modo prueba si está configurado).
5. Verificar que el saldo se actualiza en el panel del conductor.

**Qué verificar:**
- [ ] El monto mínimo se valida (error si está por debajo del mínimo del municipio)
- [ ] Redirige correctamente a MP
- [ ] Después del pago, el saldo refleja la carga

#### F1.4 — Ver y pagar una infracción propia
1. Tener una infracción pendiente en el vehículo (crearla como inspector previamente).
2. Ir a `/usuarios/mis-infracciones/`.
3. Ver la infracción con monto y estado.
4. Intentar estacionar el mismo vehículo → verificar que el sistema avisa sobre la infracción pendiente.
5. Pagar la infracción (con saldo o MP).
6. Verificar que la infracción pasa a "pagada".

**Qué verificar:**
- [ ] Las infracciones aparecen con monto, fecha, inspector y estado
- [ ] Al intentar estacionar con infracción pendiente → mensaje de aviso claro
- [ ] Si la infracción está dentro del período de gracia → se anula automáticamente al estacionar
- [ ] Pago con saldo: se debita correctamente
- [ ] Estado cambia a "pagada" tras el pago

#### F1.5 — Impugnar una infracción
1. Ir a `/usuarios/mis-infracciones/`.
2. Clic en "Impugnar" en una infracción pendiente.
3. Completar el formulario de impugnación con motivo.
4. Enviar.

**Qué verificar:**
- [ ] El formulario se envía correctamente
- [ ] Aparece mensaje de confirmación
- [ ] La impugnación queda registrada (visible para el admin)

#### F1.6 — Historial y vehículos
1. Ir al historial de estacionamientos.
2. Verificar que muestra fechas, duración y costo.
3. Ir a "Mis vehículos" → ver y agregar un vehículo.

#### F1.7 — Enviar sugerencia de mejora
1. Ir a `/usuarios/sugerencias/nueva/`.
2. Verificar que solo aparecen las áreas del conductor (conductor + general).
3. En el campo **Edad (opcional)**, seleccionar un rango (ej: 26–35).
4. Completar y enviar → verificar que aparece en la lista de "Mis sugerencias".
5. Enviar una segunda sugerencia **sin** seleccionar rango de edad (dejar "Prefiero no decir").

**Qué verificar:**
- [ ] Solo aparecen áreas "conductor" y "general" en el select de área
- [ ] El select de rango de edad está visible y tiene las opciones correctas (menor18, 18-25, 26-35, 36-50, 51-65, mayor65)
- [ ] Enviar con rango seleccionado → funciona correctamente
- [ ] Enviar sin seleccionar rango → también funciona (campo opcional)
- [ ] Las sugerencias enviadas aparecen en `/usuarios/sugerencias/`

#### F1.8 — Estacionar en la última franja horaria 🆕 *sesión 11*
> **Contexto:** antes del fix, si quedaban menos de 60 minutos para el cierre del horario, el sistema no mostraba opciones y el conductor no podía estacionar — pero el inspector sí podía multar. Ahora siempre aparece al menos una opción.

Para testear este flujo necesitás estar cerca del cierre del horario (ej. faltan 45 min, 20 min). Podés simularlo editando el horario del municipio desde el panel admin para que el cierre sea en unos minutos.

**Caso A — quedan entre 30 y 60 minutos:**
1. Configurar cierre del horario para dentro de 45 min.
2. Ir a `/usuarios/estacionar/`.
3. Verificar que aparece **solo la opción "1 hora"** (aunque exceda el cierre).
4. Completar el estacionamiento → el sistema lo cerrará automáticamente al vencer el horario.

**Caso B — quedan menos de 30 minutos:**
1. Configurar cierre del horario para dentro de 15 min.
2. Ir a `/usuarios/estacionar/`.
3. Verificar que aparece **solo la opción "30 min"**.
4. Completar el estacionamiento.

**Qué verificar:**
- [ ] Con 45 min restantes → botón "1 hora" disponible (no pantalla en blanco)
- [ ] Con 15 min restantes → botón "30 min" disponible
- [ ] Con horario ya cerrado → pantalla de "fuera de horario" (no opciones)
- [ ] En ningún caso el mensaje dice "finaliza en breve, no registres" cuando el horario sigue activo

#### F1.9 — GPS on demand: "Detectar mi cuadra" 🆕 *sesión 11*
> **Contexto:** antes el GPS se activaba automáticamente al cargar la página, lo que mostraba un popup de permiso sin contexto. Ahora el conductor debe hacer clic en "Detectar mi cuadra" para activarlo. El flag `gpsYaCorrio` evita que un segundo clic dispare un segundo pedido.

**Caso A — GPS disponible:**
1. Ir a `/usuarios/estacionar/`.
2. Verificar que **no aparece ningún popup de permiso de GPS** al cargar la página.
3. Hacer clic en el botón "Detectar mi cuadra".
4. Aceptar el permiso cuando el navegador lo pida → ver el spinner "Detectando...".
5. Verificar que aparece el nombre de la subcuadra detectada y su tipo (pagada/libre).
6. Hacer clic en "Detectar mi cuadra" una segunda vez (sin recargar) → verificar que **no** hace un segundo pedido de GPS (el botón no actúa si `gpsYaCorrio=true`).

**Caso B — GPS denegado o sin cobertura:**
1. Ir a `/usuarios/estacionar/`.
2. Hacer clic en "Detectar mi cuadra" → denegar el permiso (o estar en zona sin señal).
3. Verificar que aparece el selector manual calle→altura en cascada (no pantalla de error).
4. Seleccionar calle → el selector de altura se repopula solo.
5. Seleccionar altura → verificar que detecta tipo_zona y muestra la respuesta correcta (banner libre o formulario pagado).

**Qué verificar:**
- [ ] Al cargar la página: no aparece popup de GPS automático
- [ ] Botón "Detectar mi cuadra" visible y clicable
- [ ] Spinner aparece mientras se detecta
- [ ] Subcuadra detectada: muestra nombre + tipo (pagada/libre)
- [ ] Segundo clic en el botón: no dispara un nuevo fetch (flag gpsYaCorrio)
- [ ] GPS fallido/denegado → selector manual aparece correctamente, la página no se rompe
- [ ] Link "Ingresar manualmente" también activa el selector sin esperar al GPS

#### F1.10 — Sugerencias de vehículos: últimos usados + otros vinculados 🆕 *sesión 11*
> **Contexto:** antes todos los vehículos aparecían en una lista plana. Ahora se muestran en dos secciones: "Últimos usados" (últimos 3 vehículos con estacionamiento, sin repetidos) y "Otros vinculados" (los restantes). Los emojis indican el tipo.

**Con estacionamientos previos:**
1. Asegurarse de tener al menos 2 vehículos vinculados con estacionamientos registrados.
2. Ir a `/usuarios/estacionar/`.
3. Verificar que aparece la sección "Últimos usados" con hasta 3 vehículos.
4. Verificar que son los últimos 3 usados (más reciente arriba), sin repetidos.
5. Verificar que los vehículos restantes aparecen en "Otros vinculados".
6. Verificar que ningún vehículo aparece en ambas secciones al mismo tiempo.
7. Verificar los emojis: 🛵 para motos, 🚗 para autos.

**Con cuenta sin estacionamientos previos:**
1. Loguearse con un conductor nuevo (sin estacionamientos registrados).
2. Ir a `/usuarios/estacionar/`.
3. Verificar que la sección "Últimos usados" no aparece (o está vacía, sin error).
4. Los vehículos vinculados aparecen directamente en "Otros vinculados".

**Qué verificar:**
- [ ] "Últimos usados" muestra máximo 3 vehículos, sin repetidos
- [ ] El orden es por uso más reciente (más reciente primero)
- [ ] "Otros vinculados" muestra los restantes (no incluye los de "últimos usados")
- [ ] 🛵 para moto, 🚗 para auto en ambas secciones
- [ ] Sin estacionamientos previos: no rompe la página, "Últimos usados" no aparece o está vacía

#### F1.11 — Agregar vehículo inline (sin salir de la página) 🆕 *sesión 11*
> **Contexto:** antes, hacer clic en "Agregar vehículo" navegaba a otra página y el conductor perdía el contexto del estacionamiento que estaba por registrar. Ahora el formulario se expande inline, en la misma página.

1. Ir a `/usuarios/estacionar/`.
2. Hacer clic en "➕ Agregar vehículo".
3. Verificar que el panel de formulario se expande **en la misma página** (no navega a otra URL).
4. Completar patente y tipo de vehículo.
5. Hacer clic en "Guardar" → el panel se cierra y el nuevo vehículo aparece en la lista.
6. Hacer clic de nuevo en "➕ Agregar vehículo" → hacer clic en "Cancelar" → el panel se cierra sin guardar nada.
7. Abrir y cerrar el panel varias veces → verificar que no hay errores.

**Qué verificar:**
- [ ] Clic en "➕ Agregar vehículo" → panel se expande inline (sin cambiar de URL)
- [ ] El formulario tiene campos de patente + tipo de vehículo
- [ ] Guardar correctamente → vehículo aparece en la lista de vehículos
- [ ] "Cancelar" colapsa el panel sin hacer submit
- [ ] Abrir/cerrar múltiples veces → no hay errores JavaScript en consola

---

### Cuestionario de experiencia — Conductor

Completar con observaciones reales durante el testing:

**¿Cuánto tiempo tardaste en hacer tu primer estacionamiento desde cero?**
`_____ minutos`

**¿El GPS funcionó a la primera?**
`[ ] Sí  [ ] No — ¿qué pasó?` _______________

**¿Quedó claro qué significa "zona libre"?**
`[ ] Sí, el banner fue claro  [ ] No, no entendí qué hacer`

**¿Quedó claro cuánto dinero te iba a costar antes de confirmar?**
`[ ] Sí  [ ] No — ¿qué confundió?` _______________

**¿El panel principal muestra la información que necesitás en el día a día?**
`[ ] Sí  [ ] Le falta: _______________`

**¿Encontraste el botón de cargar saldo fácilmente?**
`[ ] Sí  [ ] No`

**¿El flujo de impugnación fue claro?**
`[ ] Sí  [ ] No`

**¿Qué mejorarías en la experiencia del conductor?**
(espacio libre)
_______________

---

## ROL 2: Inspector

**URL de entrada:** `/usuarios/inspectores/`

### Flujos a testear

#### F2.1 — Verificar una patente
1. Ir a `/usuarios/inspectores/verificar/`.
2. Ingresar la patente `AA123BB`.
3. Verificar que muestra el estado del vehículo (activo/vencido/sin registro).
4. Si tiene estacionamiento activo: ver tiempo restante, subcuadra, nombre del conductor.
5. Verificar que suena el sonido correcto (ok.mp3 / warning.mp3 / error.mp3).

**Qué verificar:**
- [ ] El resultado aparece rápido (< 3 segundos)
- [ ] Los sonidos suenan en Chrome Android
- [ ] El color de la pantalla cambia según el estado (verde/rojo/amarillo)
- [ ] Si es exento: aparece claramente la razón de exención
- [ ] Si el horario no está configurado para hoy: el inspector no puede operar

#### F2.2 — Labrar una infracción
1. Desde la pantalla de verificar, con un vehículo **sin** estacionamiento activo y dentro del horario.
2. Clic en "Labrar infracción".
3. Tomar o subir una foto del vehículo.
4. Seleccionar el motivo.
5. Confirmar.
6. Verificar que se imprime el acta (si hay impresora BLE vinculada).
7. Si no hay impresora: verificar que aparece el ticket en pantalla con la opción de reimprimir.

**Qué verificar:**
- [ ] Solo se puede labrar si el inspector está dentro del horario
- [ ] La foto se sube correctamente a Cloudinary
- [ ] El acta tiene watermark con GPS, fecha y nombre del inspector
- [ ] El sistema hace doble copia (según configuración de `segundos_pausa_doble_copia`)
- [ ] Si pausa=0: el inspector debe confirmar manualmente antes de imprimir la copia 2
- [ ] Copia 2: se reconecta automáticamente a la impresora sin diálogo (`reconectarSilencioso()` vía `getDevices()`). Si falla, aparece el botón "Reintentar copia 2" — ese botón tiene gesto fresco y puede abrir el diálogo de vinculación
- [ ] La infracción aparece en "Mis infracciones del día" del inspector

#### F2.3 — Intentar infraccionar dentro del período de gracia
1. Tener un vehículo que acaba de ser infraccionado (hace < X minutos, donde X = tolerancia del municipio).
2. Intentar infraccionar nuevamente.

**Qué verificar:**
- [ ] El sistema informa que el vehículo ya tiene una infracción reciente
- [ ] Respeta el `minutos_entre_infracciones` configurado en el municipio

#### F2.4 — Detección de subcuadra por GPS (inspector)
1. Activar GPS en la pantalla de verificar.
2. Verificar que detecta la subcuadra correcta.

#### F2.5 — Verificación SIA (si está habilitado)
1. Verificar un vehículo con patente de persona con discapacidad.
2. Confirmar que el sistema consulta SIA/ANDIS y muestra el resultado.

#### F2.6 — Resumen del día
1. Ir a `/usuarios/inspectores/resumen/`.
2. Ver las infracciones propias del día.
3. Verificar que si `inspector_ve_sus_infracciones` está desactivado → no aparece el menú.

#### F2.7 — Verificar una moto (formato patente diferente) 🆕 *sesión 11*
> **Contexto:** las motos usan el formato `123ABC` (tres dígitos + tres letras), distinto al auto `AA123BB`. El auto-submit se dispara al completar el patrón; la moto tiene dígitos al inicio, por lo que el auto-submit puede no disparar mientras se tipea. El botón manual "🔍 Verificar" aparece con ≥ 3 caracteres.
>
> ⚠️ **Importante:** este flujo solo funciona durante el horario activo del municipio. Si `horario_activo=False`, el formulario no renderiza en el DOM y ningún JS de verificación se ejecuta (botón no visible, placeholder fijo, sin autosubmit). Esto es comportamiento esperado. Testear siempre dentro del horario configurado.

1. Ir a `/usuarios/inspectores/verificar/`.
2. Seleccionar tipo **Moto** (radio button).
3. Tipear solo los tres dígitos iniciales, por ejemplo `123`.
4. Verificar que aparece el botón "🔍 Verificar" debajo del input.
5. Tipear las letras `ABC` → el auto-submit debería disparar al completar el patrón.
6. Si el auto-submit no dispara (foco perdido, teclado virtual), tocar el botón "🔍 Verificar" manualmente.
7. Verificar que la búsqueda se ejecuta y aparece el resultado.
8. Cambiar de vuelta a tipo **Auto** → verificar que el campo se limpia y el botón desaparece.
9. Cambiar de nuevo a **Moto** → verificar que el campo está vacío (no quedó la patente de auto anterior).

**Qué verificar:**
- [ ] Tipear solo 3 caracteres → botón "🔍 Verificar" aparece
- [ ] Auto-submit funciona al completar `123ABC` (6 caracteres)
- [ ] Botón manual funciona como fallback si auto-submit no dispara
- [ ] Cambiar tipo Auto → Moto: el campo queda vacío
- [ ] Cambiar tipo Moto → Auto: el campo queda vacío
- [ ] El resultado se muestra igual que para un auto (colores, sonido, datos)

#### F2.8 — Inspector en zona de estacionamiento libre 🆕 *sesión 11*
> **Contexto:** en zonas marcadas como `tipo_zona="libre"` no corresponde multar ni verificar. El inspector no debe ver el campo de patente en esa subcuadra.

1. Ir a `/usuarios/inspectores/verificar/`.
2. En el selector de calle/altura, elegir una subcuadra marcada como **libre** (coordinarlo con el admin).
3. Verificar que aparece el **banner verde** "Zona de estacionamiento libre" y que el campo de patente queda oculto.
4. Cambiar a una subcuadra **pagada** en el mismo selector.
5. Verificar que el banner desaparece y el campo de patente vuelve a mostrarse.
6. Si el inspector tiene GPS activo y se detecta una subcuadra libre por GPS: verificar el mismo comportamiento de bloqueo.

**Qué verificar:**
- [ ] Subcuadra libre seleccionada manualmente → campo de patente oculto, banner visible
- [ ] Cambiar a subcuadra pagada → campo de patente visible, banner oculto
- [ ] El inspector **no puede** enviar el formulario mientras la subcuadra activa es libre (no hay campo visible)
- [ ] La subcuadra libre detectada al cargar la página (si hay una activa) también bloquea el formulario desde el inicio

---

### Cuestionario de experiencia — Inspector

**¿El scanner de patentes (lectura QR/manual) fue rápido y confiable?**
`[ ] Sí  [ ] No — ¿qué pasó?` _______________

**¿El feedback visual (colores) y sonoro fue claro para saber el estado del vehículo?**
`[ ] Sí  [ ] No — ¿qué cambiarías?` _______________

**¿La impresora BLE se conectó sin problemas?**
`[ ] Sí  [ ] No conectó  [ ] No tengo impresora`

**¿Si no tenés impresora, quedó claro cómo ver el acta igualmente?**
`[ ] Sí  [ ] No`

**¿El flujo de labrar una infracción es rápido (menos de 2 minutos)?**
`[ ] Sí  [ ] No — ¿qué paso demora más?` _______________

**¿El mensaje de "fuera de horario" es claro y aparece en el momento correcto?**
`[ ] Sí  [ ] No`

**¿Qué información le falta a la pantalla de verificar patente?**
_______________

**¿Qué mejorarías en tu panel?**
_______________

---

## ROL 3: Vendedor

**URL de entrada:** `/usuarios/vendedores/`

### Flujos a testear

#### F3.1 — Registrar un estacionamiento en persona (cobro efectivo)
1. Ir al panel vendedor → "Registrar estacionamiento".
2. Ingresar patente (ej: `BB456CC`).
3. Seleccionar duración.
4. Elegir medio de pago (efectivo, transferencia, débito, crédito, QR).
5. Confirmar el cobro.

**Qué verificar:**
- [ ] Solo disponible dentro del horario configurado
- [ ] Si es domingo/día sin horario: el formulario está deshabilitado
- [ ] El precio coincide con la tarifa del municipio
- [ ] El `saldo_operativo` del vendedor aumentó
- [ ] Se creó un `MovimientoCaja`

#### F3.2 — Cobrar una infracción (si tiene permiso)
1. Ir a `/usuarios/vendedores/cobrar-infraccion/`.
2. Ingresar patente con infracción pendiente.
3. Seleccionar la infracción y el medio de pago.
4. Confirmar el cobro.

**Qué verificar:**
- [ ] Solo aparece si `puede_cobrar_infraccion=True` en el perfil del vendedor
- [ ] La infracción pasa a "pagada"
- [ ] El cobro aparece en el resumen de caja

#### F3.3 — Cobrar un abono mensual
1. Ir a "Cobrar abono".
2. Ingresar patente y tipo (auto/moto).
3. Seleccionar el mes.
4. Elegir medio de pago.
5. Confirmar.

**Qué verificar:**
- [ ] Se puede cobrar fuera de horario (los abonos no tienen restricción horaria)
- [ ] No se puede cobrar un abono duplicado (mismo mes + vehículo + municipio)
- [ ] El precio corresponde al tipo (auto vs moto)

#### F3.4 — Ver y cerrar la caja
1. Ir a `/usuarios/vendedores/caja/`.
2. Ver el resumen de cobros del turno (efectivo, digital, total).
3. Clic en "Cerrar caja".
4. Seleccionar el período (mañana, tarde, noche, etc.).
5. Confirmar el cierre.

**Qué verificar:**
- [ ] El resumen muestra desglose por medio de pago
- [ ] El cierre genera un `CierreCaja`
- [ ] El `saldo_operativo` se resetea a 0 tras el cierre
- [ ] El cierre aparece pendiente de certificación por el admin

#### F3.5 — Ver mis comisiones
1. Ir a `/usuarios/vendedores/comisiones/`.
2. Ver liquidaciones pendientes, depositadas y certificadas.

**Qué verificar:**
- [ ] Solo aparecen liquidaciones del propio vendedor
- [ ] Los estados son claros (pendiente / depositada / certificada)

#### F3.6 — Certificar una comisión y adjuntar factura
1. Cuando una comisión está en estado "depositada".
2. Ir al detalle → confirmar recibo → subir factura (si corresponde).

**Qué verificar:**
- [ ] El vendedor puede certificar solo cuando el tesorero ya depositó
- [ ] Se puede subir el archivo de factura
- [ ] El estado cambia a "certificada"

---

### Cuestionario de experiencia — Vendedor

**¿El formulario de cobro de estacionamiento fue rápido de completar?**
`[ ] Sí  [ ] No — ¿qué demora?` _______________

**¿Los medios de pago disponibles son los que usás en el día a día?**
`[ ] Sí  [ ] Le falta: _______________`

**¿El resumen de caja muestra claramente cuánto tenés que rendir?**
`[ ] Sí  [ ] No — ¿qué falta?` _______________

**¿Encontraste el botón de "Cobrar abono" sin dificultad?**
`[ ] Sí  [ ] No`

**¿El proceso de cierre de caja fue claro?**
`[ ] Sí  [ ] No — ¿qué confundió?` _______________

**¿Entendiste para qué es la sección de comisiones?**
`[ ] Sí  [ ] No`

**¿Qué mejorarías en tu panel?**
_______________

---

## ROL 4: Admin Municipal

**URL de entrada:** `/usuarios/admin-inicio/`

### Flujos a testear

#### F4.1 — Panel principal y navegación
1. Entrar al panel admin.
2. Recorrer el sidebar: Conductores, Inspectores, Vendedores, Infracciones, Rendiciones, Exenciones, Subcuadras, Cobertura, Auditoría, Dashboard.
3. Verificar que los badges de notificación (infracciones, impugnaciones) muestran el número correcto.

#### F4.2 — Gestionar conductores
1. Ir a `/usuarios/admin-usuarios/`.
2. Buscar un conductor por nombre o email.
3. Entrar al detalle de un conductor → ver historial, saldo, vehículos.
4. Editar el perfil (cambiar datos básicos).
5. Ver las impugnaciones pendientes y responder una.

**Qué verificar:**
- [ ] La búsqueda funciona
- [ ] El detalle muestra historial completo
- [ ] Responder una impugnación: el estado cambia y el conductor puede verla

#### F4.3 — Gestionar inspectores
1. Ir a `/usuarios/admin-inspectores/`.
2. Crear un nuevo inspector.
3. Editar nombre/apellido (verificar que se guarda con formato título).
4. Ir a estadísticas → ver infracciones por inspector + exportar Excel.
5. Resetear la contraseña de un inspector.

**Qué verificar:**
- [ ] El inspector nuevo puede loguearse correctamente
- [ ] Las estadísticas muestran datos reales del período
- [ ] El Excel se descarga y se puede abrir

#### F4.4 — Gestionar vendedores
1. Crear un nuevo vendedor con un porcentaje de comisión.
2. Activar/desactivar el permiso de cobrar infracciones.
3. Resetear contraseña.

#### F4.5 — Gestionar infracciones
1. Ir a `/usuarios/admin-infracciones/`.
2. Filtrar por estado (pendiente / pagada / anulada).
3. Abrir el modal de detalle de una infracción.
4. Anular una infracción pendiente → verificar que el modal se cierra correctamente.
5. Aplicar un descuento voluntario a una infracción.

**Qué verificar:**
- [ ] El modal se cierra después de anular (no queda abierto)
- [ ] La infracción pasa a "anulada" en la lista
- [ ] El descuento se aplica correctamente al monto

#### F4.6 — Certificar un cierre de caja
1. Ir a rendiciones → sección "Cierres pendientes".
2. Revisar el desglose de un cierre de vendedor o inspector.
3. Certificar el cierre.

**Qué verificar:**
- [ ] El desglose efectivo/digital es correcto
- [ ] El cierre queda marcado como certificado
- [ ] Solo aparecen cierres del propio municipio

#### F4.7 — Crear una rendición
1. Ir a `/usuarios/admin-rendiciones/`.
2. Seleccionar cierres de caja certificados para incluir en la rendición.
3. Crear la rendición.
4. Verificar que se generaron automáticamente las `LiquidacionComision` para cada vendedor.

**Qué verificar:**
- [ ] Solo se pueden incluir cierres certificados
- [ ] Los totales calculados son correctos (efectivo + digital)
- [ ] Las liquidaciones de comisión aparecen creadas automáticamente en estado "pendiente"
- [ ] La rendición queda en estado "pendiente" esperando al tesorero

#### F4.8 — Gestionar subcuadras (requiere flag activo) 🆕 *sesión 14*
> **Contexto:** por defecto solo el superadmin puede acceder a `/admin-subcuadras/`. El superadmin puede habilitarlo por municipio activando "📍 Admin puede gestionar subcuadras" en `editar_municipio`. Si el flag está desactivado, el admin ve un mensaje de error explicativo en lugar de la página.

**Con flag DESACTIVADO:**
1. Loguearse como admin municipal.
2. Intentar acceder a `/usuarios/admin-subcuadras/` directamente.
3. Verificar que aparece un mensaje: "No tenés autorización para gestionar subcuadras. Pedí al superadmin que active este módulo para tu municipio."

**Con flag ACTIVADO (habilitarlo desde superadmin primero):**
1. Ir a `/usuarios/admin-subcuadras/`.
2. Ver el mapa con los pins (azul = pagado, verde = libre).
3. Agregar una subcuadra nueva haciendo clic en el mapa (poner latitud/longitud).
4. Editar el nombre (calle/altura) de una subcuadra existente con el botón ✏️.
5. Verificar que el pin del mapa se actualiza al agregar coordenadas.

**Qué verificar:**
- [ ] Con flag desactivado: admin ve mensaje de error claro (no 403 genérico)
- [ ] Con flag activado: el mapa carga correctamente (OpenStreetMap)
- [ ] Los pins tienen el color correcto según tipo_zona (azul = pagado, verde = libre)
- [ ] Al hacer clic en un pin: muestra popup con nombre y tipo
- [ ] La edición guarda correctamente calle y altura
- [ ] No se puede duplicar una subcuadra con la misma calle+altura

#### F4.9 — Dashboard con filtro de fechas
1. Ir a `/usuarios/admin-dashboard/`.
2. Filtrar por un rango de fechas.
3. Verificar totales de infracciones, estacionamientos y recaudación.

#### F4.10 — Auditoría de staff
1. Ir a auditoría de staff.
2. Filtrar por vendedor/inspector en un rango de fechas.
3. Verificar que se muestran los movimientos de caja y las infracciones.

#### F4.11 — Auditoría de resets de contraseña 🆕 *sesión 14*
> **Contexto:** cada vez que el admin usa "Resetear al DNI" o "Establecer contraseña" en el detalle de un conductor, el sistema registra el evento en `AuditoriaPassword` (quién, a quién, cuándo, tipo). El historial aparece dentro de la sección "🔑 Cambiar contraseña" en la vista de detalle del conductor.

1. Ir a `/usuarios/admin-usuarios/` → abrir el detalle de cualquier conductor.
2. Expandir la sección "🔑 Cambiar contraseña".
3. Ejecutar "Resetear al DNI" → confirmar → volver al detalle del conductor.
4. Expandir la sección "🔑 Cambiar contraseña" de nuevo.
5. Verificar que la tabla de historial aparece con el reset recién hecho.
6. Verificar que muestra: fecha/hora, correo del admin logueado, tipo "Reset al DNI".
7. Ejecutar "Establecer contraseña" con una contraseña temporal → volver al detalle.
8. Verificar que la tabla muestra ahora dos entradas (orden: más reciente primero).

**Qué verificar:**
- [ ] Antes del primer reset: la tabla de historial no aparece (vacía → sección oculta)
- [ ] Después del primer reset: la tabla aparece con 1 fila
- [ ] Fecha/hora de la fila: coincide con el momento del reset (margen de ±1 min)
- [ ] Admin: muestra el correo del admin logueado (el que hizo la acción)
- [ ] Tipo "Reset al DNI" o "Contraseña personalizada" según la acción
- [ ] Segunda acción → segunda fila, la más reciente aparece primero
- [ ] Se muestran máximo 10 entradas (si hay más, las más viejas desaparecen de la vista)

#### F4.12 — Sidebar condicional por flags de superadmin 🆕 *sesión 15*
> **Contexto:** los links "📍 Subcuadras", "📊 Cobertura" y "🗺️ Mapa de calor" solo aparecen en el sidebar si el superadmin los activó para ese municipio. Si no están habilitados, tampoco deben aparecer en el menú.

1. Con un admin de un municipio sin `puede_gestionar_subcuadras=True`: verificar que "📍 Subcuadras" y "📊 Cobertura" **no aparecen** en el sidebar.
2. Intentar acceder directamente a `/usuarios/admin-subcuadras/` → debe mostrar pantalla de "Módulo no habilitado" con estilo (no un 403 sin CSS).
3. El superadmin activa el flag en "Editar municipio" → el admin ahora ve los links en el sidebar.
4. Mismo test para `mapa_infracciones_activo` y "🗺️ Mapa de calor".

**Qué verificar:**
- [ ] Sin flag: links ausentes del sidebar
- [ ] Sin flag: acceso directo a la URL muestra página de acceso denegado con estilo (🔒, botón "Volver al panel")
- [ ] Con flag activado por superadmin: links aparecen en el sidebar
- [ ] Solo el superadmin puede activar/desactivar estos flags

#### F4.13 — Tabs en /admin-staff/ con sticky headers 🆕 *sesión 15*
1. Ir a `/usuarios/admin-staff/`.
2. Verificar que se ven dos tabs: "💰 Vendedores" y "👮 Inspectores".
3. El tab activo se resalta visualmente. El tab por defecto es "Vendedores".
4. Cambiar al tab "Inspectores" → verificar que la URL cambia a `?tab=inspectores` sin recargar la página.
5. Recargar la página → verificar que sigue en el tab "Inspectores" (estado persiste en URL).
6. Con listas largas: hacer scroll dentro de la tabla → los encabezados de columna deben permanecer visibles (sticky).

**Qué verificar:**
- [ ] Dos tabs separados: Vendedores e Inspectores
- [ ] Cambiar de tab no recarga la página (history.replaceState)
- [ ] URL refleja el tab activo (`?tab=vendedores` o `?tab=inspectores`)
- [ ] Recargar con `?tab=inspectores` carga el tab correcto
- [ ] Headers sticky: al hacer scroll en listas largas los encabezados siguen visibles

#### F4.14 — Footer "¿Cómo usar el panel?" en todos los roles 🆕 *sesión 15*
> **Contexto:** todos los paneles (admin, inspector, vendedor, tesorero) ahora tienen el tutorial en el **pie de página** del panel. Antes lo tenían en la parte superior o en lugares inconsistentes.

Para cada rol:
1. Ir al panel principal del rol.
2. Hacer scroll hasta el final de la página.
3. Verificar que aparece un separador horizontal y luego el bloque "📖 ¿Cómo usar el panel?" (colapsable) + "💡 ¿Tenés alguna sugerencia? Enviala acá →".
4. Hacer clic en el `<summary>` para expandir el tutorial → verificar que el contenido es correcto para ese rol.
5. Hacer clic en "Enviala acá →" → verificar que redirige a la página de sugerencias.

**Qué verificar:**
- [ ] Admin: tutorial + sugerencias al pie del contenido principal (antes del cierre del div)
- [ ] Inspector: tutorial + sugerencias al pie de la sección principal (antes de `</section>`)
- [ ] Vendedor: tutorial + sugerencias al pie del panel (antes del cierre del div)
- [ ] Tesorero: tutorial + sugerencias al pie del panel (antes de `</div>`)
- [ ] Tutorial colapsable: cerrado por defecto, se expande al hacer clic
- [ ] Link de sugerencias: redirige a la URL de envío de sugerencias

---

### Cuestionario de experiencia — Admin Municipal

**¿El panel principal te da una vista clara del estado del sistema?**
`[ ] Sí  [ ] No — ¿qué falta?` _______________

**¿La navegación del sidebar es intuitiva?**
`[ ] Sí  [ ] No — ¿qué confundió?` _______________

**¿El proceso de crear una rendición fue claro (qué cierres incluir, qué pasa al crearla)?**
`[ ] Sí  [ ] No — ¿qué confundió?` _______________

**¿Las liquidaciones de comisión se crearon solas sin que tengas que hacer nada extra?**
`[ ] Sí  [ ] No`

**¿La gestión de subcuadras en el mapa fue fácil de usar?**
`[ ] Sí  [ ] No — ¿qué fue difícil?` _______________

**¿El modal de detalle de infracciones funciona correctamente (se cierra tras anular)?**
`[ ] Sí  [ ] No`

**¿La exportación de Excel de inspectores funcionó?**
`[ ] Sí  [ ] No`

**¿Qué mejorarías en tu panel?**
_______________

---

## ROL 5: Tesorero

**URL de entrada:** `/usuarios/tesorero/`

### Flujos a testear

#### F5.1 — Panel y acceso a comisiones
1. Entrar al panel tesorero.
2. Ver las cards disponibles: rendiciones, comisiones a depositar.
3. Clic en "Comisiones a depositar" → redirige a `/usuarios/admin-rendiciones/?seccion=comisiones`.

**Qué verificar:**
- [ ] La card "Comisiones a depositar" es clickable y lleva al lugar correcto
- [ ] Solo aparecen rendiciones y liquidaciones del propio municipio

#### F5.2 — Validar una rendición
1. Ir al listado de rendiciones pendientes.
2. Abrir el detalle de una rendición.
3. Opción A: validar → la rendición pasa a "validada".
4. Opción B: observar → el campo de notas es **obligatorio** (no se puede enviar sin notas).

**Qué verificar:**
- [ ] El detalle muestra cierres incluidos, totales y liquidaciones
- [ ] Observar sin notas: el formulario no se envía (validación JS + backend)
- [ ] Al observar con notas: la rendición pasa a "observada" y el admin puede verlo
- [ ] Al validar: la rendición pasa a "validada"

#### F5.3 — Depositar comisiones de vendedores
1. Ir a la sección de comisiones.
2. Ver las liquidaciones en estado "pendiente".
3. Depositar una comisión: ingresar número de comprobante + subir archivo de comprobante.
4. Confirmar el depósito.

**Qué verificar:**
- [ ] El monto a depositar es correcto (suma de comisiones del período)
- [ ] El número de comprobante se guarda
- [ ] El archivo se sube correctamente
- [ ] La liquidación pasa a estado "depositada"
- [ ] El vendedor ahora puede certificar el recibo

#### F5.4 — Ver historial de rendiciones
1. Ver las rendiciones pasadas en todos los estados (pendiente, validada, observada).
2. Entrar al detalle de una rendición validada.

**Qué verificar:**
- [ ] El historial está ordenado por fecha
- [ ] El detalle de rendición validada es accesible (solo lectura)

---

### Cuestionario de experiencia — Tesorero

**¿El panel principal te muestra lo que necesitás de un vistazo?**
`[ ] Sí  [ ] No — ¿qué falta?` _______________

**¿El proceso de validar/observar una rendición fue claro?**
`[ ] Sí  [ ] No — ¿qué confundió?` _______________

**¿La obligatoriedad de las notas al observar quedó clara (no se puede enviar sin notas)?**
`[ ] Sí  [ ] No`

**¿El proceso de depositar la comisión fue intuitivo?**
`[ ] Sí  [ ] No — ¿qué fue difícil?` _______________

**¿Qué información extra necesitarías ver en el panel?**
_______________

**¿Qué mejorarías en tu experiencia como tesorero?**
_______________

---

## ROL 6: Superadmin

**URL de entrada:** `/superadmin/municipios/`

### Flujos a testear

#### F6.1 — Gestionar municipios
1. Ver el listado de municipios.
2. Entrar a editar un municipio: configurar tarifas, horarios, colores, logo.
3. Guardar cada sección por separado (las secciones son independientes).
4. Verificar la alerta JS de "cambios sin guardar".

**Qué verificar:**
- [ ] La alerta de cambios sin guardar aparece si se intenta salir sin guardar
- [ ] Los colores del municipio se reflejan en tiempo real (o tras refresh)
- [ ] El logo se sube correctamente

#### F6.2 — Gestionar subcuadras de un municipio desde superadmin
1. En la pantalla de editar municipio, clic en "📍 Subcuadras".
2. Verificar que redirige a `/superadmin/municipio/<id>/subcuadras/`.
3. Agregar, editar y asignar coordenadas a subcuadras.
4. Volver al municipio con el botón "← Volver al municipio".

**Qué verificar:**
- [ ] El botón de volver lleva de vuelta a `editar_municipio`
- [ ] Los cambios de subcuadras se guardan correctamente
- [ ] El mapa colorea correctamente (azul/verde) según tipo_zona

#### F6.3 — Gestionar módulos premium
1. Activar/desactivar módulos en un municipio.
2. Verificar que el cambio afecta las funcionalidades disponibles para ese municipio.

#### F6.4 — Generar token TV
1. En editar municipio → sección "Dashboard TV".
2. Regenerar el token.
3. Abrir la URL `/tv/<token>/` → verificar que muestra el dashboard público.

#### F6.5 — Gestionar sugerencias de mejora
1. Ir a `/superadmin/sugerencias/`.
2. Ver sugerencias enviadas por conductores/inspectores.
3. Cambiar el estado de una sugerencia (en revisión, implementada, descartada).

#### F6.6 — Habilitar gestión de subcuadras para admin municipal 🆕 *sesión 14*
1. En editar municipio → buscar el checkbox "📍 Admin puede gestionar subcuadras".
2. Activarlo → guardar.
3. Loguearse como admin del municipio → acceder a `/usuarios/admin-subcuadras/`.
4. Verificar que el admin puede ver el mapa y crear/editar subcuadras.
5. Volver a superadmin → desactivar el flag → guardar.
6. Loguearse como admin e intentar acceder a `/usuarios/admin-subcuadras/`.
7. Verificar que aparece el mensaje de "sin autorización".

**Qué verificar:**
- [ ] Con flag activado: admin accede sin problemas al mapa de subcuadras
- [ ] Con flag desactivado: admin ve mensaje explicativo (no una pantalla de error genérica)
- [ ] El superadmin siempre puede acceder a `/admin-subcuadras/` independientemente del flag

#### F6.7 — Toggle inspector ve sus infracciones
1. En editar municipio → sección de configuración.
2. Activar/desactivar `inspector_ve_sus_infracciones`.
3. Loguearse como inspector y verificar que el menú de resumen aparece/desaparece.

#### F6.8 — Limpiar datos de prueba
1. En editar municipio → "Zona de peligro".
2. Escribir `CONFIRMAR+<NOMBRE>` en el campo.
3. Verificar que limpia solo los datos de ese municipio.

---

### Cuestionario de experiencia — Superadmin

**¿La configuración del municipio por secciones (tarifas, horarios, colores...) fue clara?**
`[ ] Sí  [ ] No — ¿qué sección fue confusa?` _______________

**¿La alerta de "cambios sin guardar" funcionó correctamente?**
`[ ] Sí  [ ] No`

**¿Pudiste gestionar las subcuadras del municipio desde la vista de superadmin?**
`[ ] Sí  [ ] No — ¿qué falló?` _______________

**¿Los módulos premium son fáciles de activar/desactivar?**
`[ ] Sí  [ ] No`

**¿El dashboard TV público funciona correctamente con el token?**
`[ ] Sí  [ ] No`

**¿Qué mejorarías en tu panel de superadmin?**
_______________

---

## Pago público sin registro

**URL de entrada:** `/usuarios/pagar/`

### Flujos a testear

#### FP.0 — Confirmación de patente antes de buscar 🆕 *sesión 15*
> **Contexto:** para evitar errores de tipeo, el formulario de búsqueda requiere ingresar la patente dos veces. El botón "Buscar →" se deshabilita si los dos campos no coinciden.

1. Ir a `/usuarios/pagar/`.
2. Ingresar una patente en el primer campo (ej: `AA123BB`).
3. Ingresar una patente DISTINTA en el segundo campo (ej: `AA123BC`).
4. Verificar que aparece el aviso "⚠️ Las patentes no coinciden" y el botón queda deshabilitado.
5. Corregir el segundo campo para que coincida con el primero.
6. Verificar que el aviso desaparece y el botón se habilita.
7. Enviar el formulario.

**Qué verificar:**
- [ ] Con patentes distintas: aviso visible, botón deshabilitado
- [ ] Con patentes iguales: aviso oculto, botón habilitado
- [ ] El submit con JS desactivado también está protegido (handler en `submit`)

#### FP.1 — Consultar deuda por patente
1. Ir a `/usuarios/pagar/`.
2. Ingresar la misma patente en ambos campos (con infracciones pendientes).
3. Verificar que muestra la deuda correctamente.
4. Pagar la infracción con MercadoPago.

**Qué verificar:**
- [ ] La búsqueda funciona sin estar logueado
- [ ] El precio de la infracción es correcto
- [ ] Después del pago (webhook MP), la infracción pasa a "pagada"

#### FP.2 — Estacionar sin registro
1. Ir a `/usuarios/pagar/`.
2. Ingresar una patente.
3. Activar GPS → verificar que detecta subcuadra.
4. Si es zona libre: ver banner verde, no hay opción de pago.
5. Si es zona pagada: seleccionar duración y pagar con MP.

**Qué verificar:**
- [ ] GPS funciona en el flujo público (sin login)
- [ ] Zona libre: no se registra pago
- [ ] La selección en cascada (sin GPS) también detecta zona libre

---

---

## TEST COMPLETO: Flujo de comisiones de vendedores (punta a punta)

Este test cubre el ciclo completo desde que un vendedor cobra hasta que recibe su comisión. Hay que hacerlo una sola vez, en orden, con los roles en sesiones separadas (abrir el browser como incógnito para cada rol, o tener usuarios de prueba distintos).

**Prerrequisitos antes de arrancar:**
- Un vendedor con `porcentaje_ganancia > 0` (ej: 10%)
- Un admin con `es_admin=True` en el mismo municipio
- Un tesorero con `es_tesorero=True` en el mismo municipio
- El municipio tiene una tarifa y horario activo para hoy
- Tener a mano una calculadora — vas a verificar montos en cada paso

---

### PASO 1 — Vendedor cobra estacionamientos (genera movimientos de caja)

**Quién:** vendedor@test.com | **URL:** `/usuarios/vendedores/`

1. Ir al panel vendedor → "Registrar estacionamiento".
2. Ingresar una patente cualquiera (ej: `AA123BB`).
3. Seleccionar duración: 1 hora.
4. Medio de pago: efectivo.
5. Confirmar el cobro.
6. **Anotar el monto cobrado** (ej: $500).
7. Repetir una o dos veces con patentes distintas para tener varios movimientos.
8. Ir a `/usuarios/vendedores/caja/` → verificar el resumen de caja.
9. **Anotar el total recaudado** (suma de todos los cobros del turno).

**Qué verificar:**
- [ ] Cada cobro generó un `MovimientoCaja` (visible en el resumen de caja)
- [ ] El resumen muestra el desglose por medio de pago
- [ ] La suma de los montos en el resumen coincide con lo que cobraste manualmente

**💡 ¿Cómo se calcula la comisión?**
`comision_monto = monto_cobrado × porcentaje_ganancia / 100`
Ej: $500 cobrados × 10% = $50 de comisión por ese movimiento.

---

### PASO 2 — Vendedor cierra su caja (genera el CierreCaja)

**Quién:** vendedor@test.com | **URL:** `/usuarios/vendedores/caja/`

1. En el resumen de caja → clic en "Cerrar caja".
2. Seleccionar el período (ej: "Mañana").
3. Confirmar el cierre.
4. **Anotar el `ganancia_usuario` del cierre** — es la suma de las comisiones de todos los movimientos del turno.

**Qué verificar:**
- [ ] El cierre se creó correctamente y aparece en el historial de cierres
- [ ] El `saldo_operativo` del vendedor volvió a 0
- [ ] El estado del cierre es "pendiente de certificación" (no certificado todavía)
- [ ] La `ganancia_usuario` del cierre = suma de `comision_monto` de cada movimiento (calcularlo a mano y verificar)

**Referencia de cálculo esperada:**
Si cobraste $500 + $300 + $200 = $1000, y el porcentaje es 10%:
- Movimiento 1: $50 de comisión
- Movimiento 2: $30 de comisión
- Movimiento 3: $20 de comisión
- `ganancia_usuario` del cierre = $100

---

### PASO 3 — Admin certifica el cierre del vendedor

**Quién:** admin@test.com | **URL:** `/usuarios/admin-rendiciones/`

1. Ir a `/usuarios/admin-rendiciones/`.
2. En la sección "Cierres pendientes de certificación", buscar el cierre que recién hizo el vendedor.
3. Abrir el detalle del cierre → revisar el desglose (efectivo, digital, total recaudado, comisión).
4. **Verificar que los montos coinciden** con lo que anotaste en el paso 1.
5. Certificar el cierre.

**Qué verificar:**
- [ ] El cierre del vendedor aparece en "Cierres pendientes"
- [ ] El desglose muestra efectivo/digital/total con los valores correctos
- [ ] La `ganancia_usuario` (comisión del vendedor) coincide con lo calculado en el paso 2
- [ ] Después de certificar: el cierre pasa a estado "certificado"
- [ ] El propio cierre del admin (si hubiera uno) NO muestra el botón "Certificar" → muestra el mensaje de que el tesorero debe certificarlo desde su panel

**⚠️ Diferencia entre cierre de vendedor y cierre de admin:**
El admin puede certificar los cierres de los vendedores. Para el cierre propio del admin, es el tesorero quien lo certifica (desde el panel del tesorero en `cierres_admin_sin_certificar`).

---

### PASO 4 — Admin crea la rendición (genera LiquidacionComision)

**Quién:** admin@test.com | **URL:** `/usuarios/admin-rendiciones/crear/`

1. Ir a `/usuarios/admin-rendiciones/` → clic en "Crear rendición".
2. En el formulario, ver la lista de cierres certificados disponibles para incluir.
3. Seleccionar el cierre del vendedor que se acaba de certificar.
4. Si hay más cierres certificados de otros vendedores, seleccionarlos también.
5. Confirmar la creación de la rendición.

**Qué verificar:**
- [ ] Solo aparecen en la lista los cierres **certificados** (los pendientes no deben aparecer)
- [ ] Al crear la rendición, el sistema genera automáticamente una `LiquidacionComision` por cada vendedor incluido
- [ ] La rendición queda en estado "pendiente" (esperando que el tesorero la valide)
- [ ] Las liquidaciones de comisión quedan en estado "pendiente"
- [ ] El monto de la `LiquidacionComision` del vendedor = la `ganancia_usuario` de su cierre incluido

**Cómo verificar las liquidaciones creadas:**
En la misma pantalla de rendiciones, después de crear, debería aparecer la rendición con el desglose de liquidaciones. Verificar que la comisión del vendedor de prueba sea exactamente la que calculaste en el paso 2.

---

### PASO 5 — Tesorero valida la rendición

**Quién:** tesorero@test.com | **URL:** `/usuarios/tesorero/`

1. Entrar al panel tesorero.
2. Ver las rendiciones pendientes de validación.
3. Abrir el detalle de la rendición que recién creó el admin.
4. **Revisar el detalle**: cierres incluidos, totales, liquidaciones de comisión por vendedor.
5. Si todo está correcto → validar la rendición.
6. Si hay algo incorrecto → observar (escribir las notas de observación — campo obligatorio).

**Qué verificar:**
- [ ] La rendición pendiente aparece en el panel del tesorero
- [ ] El detalle muestra los cierres incluidos con sus montos
- [ ] Las liquidaciones de comisión están listadas por vendedor con los montos correctos
- [ ] Intentar observar sin escribir notas → el formulario no debe enviarse (validación)
- [ ] Al validar: la rendición pasa a estado "validada"

---

### PASO 6 — Tesorero deposita la comisión al vendedor

**Quién:** tesorero@test.com | **URL:** `/usuarios/tesorero/depositar/<liquidacion_id>/`

1. Desde el panel tesorero → ir a la sección de comisiones a depositar.
2. Ver la `LiquidacionComision` del vendedor en estado "pendiente".
3. Clic en "Depositar comisión".
4. Completar el formulario:
   - Número de comprobante (ej: `TRF-2026-0001`)
   - Subir el archivo de comprobante (PDF o imagen)
5. Confirmar el depósito.

**Qué verificar:**
- [ ] El monto a depositar coincide con el calculado en el paso 2
- [ ] El número de comprobante se guarda correctamente
- [ ] El archivo de comprobante se sube sin error
- [ ] La liquidación pasa a estado "depositada" (no "certificada" todavía — eso lo hace el vendedor)
- [ ] El vendedor ahora puede ver la comisión como "depositada" en su panel

---

### PASO 7 — Vendedor certifica que recibió la comisión

**Quién:** vendedor@test.com | **URL:** `/usuarios/vendedores/comisiones/`

1. Ir a `/usuarios/vendedores/comisiones/`.
2. Ver la liquidación en estado "depositada" (con el comprobante que subió el tesorero).
3. Revisar el comprobante (nombre del banco, número, monto).
4. Confirmar que recibió el depósito → clic en "Certificar recibo".
5. Si el municipio requiere factura → subir el archivo de factura en `/usuarios/vendedores/comisiones/<id>/factura/`.

**Qué verificar:**
- [ ] La liquidación aparece con estado "depositada" y el comprobante del tesorero es visible
- [ ] El vendedor NO puede certificar antes de que el tesorero deposite (estado "pendiente" no tiene botón de certificar)
- [ ] Al certificar: la liquidación pasa a estado "certificada"
- [ ] La factura (si aplica) se sube correctamente

---

### Verificación final de montos — Tabla de reconciliación

Al terminar el test, completar esta tabla y verificar que los números cierran:

| Concepto | Valor esperado | Valor real del sistema | ¿Coincide? |
|----------|---------------|----------------------|-----------|
| Total recaudado por el vendedor | (suma de cobros) | (ver resumen de caja) | [ ] |
| `ganancia_usuario` del CierreCaja | (total × % comisión) | (ver detalle del cierre) | [ ] |
| Monto de la LiquidacionComision | (igual a ganancia_usuario) | (ver detalle de rendición) | [ ] |
| Monto depositado por el tesorero | (igual a ganancia_usuario) | (ver comprobante) | [ ] |

Si alguna celda no coincide, hay un bug de cálculo. Reportarlo con los valores exactos y el `id` de los objetos involucrados (CierreCaja, LiquidacionComision).

---

### Checklist rápido — Flujo de comisiones completo

- [ ] **Paso 1** — Vendedor cobró estacionamientos y el resumen de caja es correcto
- [ ] **Paso 2** — Vendedor cerró caja y `ganancia_usuario` = suma de comisiones de sus movimientos
- [ ] **Paso 3** — Admin certificó el cierre del vendedor; el propio cierre del admin NO muestra botón "Certificar"
- [ ] **Paso 4** — Admin creó la rendición; se generaron `LiquidacionComision` automáticamente
- [ ] **Paso 5** — Tesorero validó la rendición; observar sin notas falla correctamente
- [ ] **Paso 6** — Tesorero depositó la comisión con comprobante; la liquidación pasó a "depositada"
- [ ] **Paso 7** — Vendedor certificó el recibo; la liquidación pasó a "certificada"
- [ ] **Montos** — Tabla de reconciliación completa, todos los valores coinciden

---

## Casos borde — testear en cualquier rol

| Caso | Qué probar | Resultado esperado |
|------|-----------|-------------------|
| Fuera de horario | Inspector intenta labrar a las 00:00 | Pantalla bloqueada con mensaje |
| Infracción dentro de gracia | Conductor estaciona inmediatamente tras recibir multa | Infracción anulada automáticamente |
| Infracción fuera de gracia | Conductor estaciona pasado el período de gracia | La infracción queda pendiente, se puede estacionar pero aparece aviso |
| Saldo insuficiente | Conductor intenta estacionar sin saldo suficiente | Error claro, no se registra el estacionamiento |
| Abono duplicado | Vendedor intenta cobrar el mismo mes dos veces | Error "ya existe abono para este mes" |
| Patente inexistente | Cualquier rol busca una patente que no existe | El sistema la crea como nuevo vehículo (verificar) |
| Acceso cruzado | Inspector intenta acceder a `/usuarios/admin-inicio/` | Redirige al panel correcto del inspector |
| Multi-municipio | Admin de municipio A intenta ver datos del municipio B | Error 404 o redirección |
| Zona libre + submit manual | Conductor envía el formulario de estacionar en zona libre | Backend rechaza el intento de pago |

---

## Checklist final cross-rol

Después de testear todos los roles:

- [ ] **Flujo de comisiones completo:** ver sección "TEST COMPLETO: Flujo de comisiones de vendedores (punta a punta)" y completar su checklist de 7 pasos con verificación de montos.
- [ ] **Zona libre de punta a punta:** inspector confirma que una subcuadra es libre en el mapa → conductor la detecta por GPS y no paga → conductor la detecta en cascada manual y no paga → pago público tampoco genera pago.
- [ ] **Infracción de punta a punta:** inspector labró → conductor impugnó → admin respondió la impugnación → conductor pagó → estado = pagada.
- [ ] **Dark mode:** todos los paneles se ven correctamente en modo oscuro (sin textos ilegibles ni fondos raros).
- [ ] **Mobile:** las pantallas que usan los inspectores y conductores se ven bien en Chrome Android (pantalla chica, touch).
- [ ] **Auditoría de contraseñas:** admin resetea la contraseña de un conductor → historial aparece en el detalle del conductor → muestra fecha, admin y tipo correctamente.
- [ ] **Subcuadras con flag:** superadmin activa `puede_gestionar_subcuadras` → admin accede a `/admin-subcuadras/` → superadmin desactiva → admin ve mensaje de error.
- [ ] **Sin errores 500 en ningún flujo** (revisar Sentry o los logs de Railway al final del testing).
