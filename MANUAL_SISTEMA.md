# Manual del Sistema de Estacionamiento Medido

---

## 1. Flujo de Datos

### Entidades principales

```
Municipio
  ├── Usuario (admin / inspector / vendedor / conductor)
  │     └── VehiculoUsuario ──→ Vehiculo
  │           └── tipo_exencion, notas_exencion
  ├── Subcuadra (calle + altura)
  ├── Tarifa (precio_por_hora)
  ├── HorarioEstacionamiento (día + hora_inicio + hora_fin)
  ├── DiaEspecial (fecha + tipo + cobro_activo)
  ├── Estacionamiento (activo / finalizado)
  ├── Infraccion (pendiente / pagada / anulada)
  ├── MovimientoCaja (ingreso / egreso)
  └── CierreCaja
```

### Ciclo de vida de un estacionamiento

```
Conductor paga
  → Estacionamiento (estado=ACTIVO, hora_inicio, duracion_min, costo_base)
  → MovimientoCaja tipo=ingreso (para el vendedor/inspector que cobró)

Al vencer duracion:
  → Estacionamiento (estado=FINALIZADO, hora_fin, costo_final)
  → Inspector puede escanear → IMPAGO → Infraccion

Inspector escanea en plazo de tolerancia (15 min post-vencimiento):
  → VerificacionInspector (resultado=verificado)
  → Estado: PENDIENTE_PAGO (no se puede infraccionar aún)
  → Si conductor paga dentro de esos 15 min → mensaje "Infracción cancelada"

Conductor paga una infracción:
  → Infraccion (estado=pagada, fecha_pago)
  → usuario.saldo -= infraccion.monto
  → MovimientoCaja tipo=ingreso
```

### Ciclo de vida de una exención

```
Admin busca vehículo por patente (desde detalle_usuario o panel_exenciones)
  → Carga tipo_exencion (discapacitado / vecino_frentista / jubilado / fuerza / vehiculo_oficial)
  → Carga notas_exencion (nro de documento, fecha de vencimiento, resolución)
  → Marca exento_global=True (no paga en ningún lado)
    OR
  → Selecciona subcuadras_exentas (paga en el resto, pero no en esas)

Inspector escanea vehículo con exención:
  EXENTO_TOTAL → ✅ OK, no hay acción
  EXENTO_PARCIAL en su subcuadra → ✅ OK
  EXENTO_PARCIAL fuera de su subcuadra → 🚨 INFRACCIONAR (paga igual en esa zona)
```

---

## 2. Flujo de Sistema

### Flujo de cobro (conductor paga solo)

```
1. Conductor inicia sesión (correo/contraseña o Google)
2. Va a "Estacionar" → elige su vehículo o ingresa patente
3. Elige duración (1, 2, 3 horas)
4. Sistema calcula costo = duracion × tarifa_por_hora
5. Descuenta de usuario.saldo
6. Crea Estacionamiento ACTIVO
7. Conductor ve timer en pantalla de inicio
8. Al vencer: estado pasa a FINALIZADO automáticamente
```

### Flujo de cobro manual (inspector o vendedor cobra en calle)

```
1. Inspector/Vendedor va a "Cobro manual"
2. Ingresa patente del vehículo
3. Elige duración
4. Sistema crea Estacionamiento + MovimientoCaja (ingreso para el operador)
5. Genera ticket de cobro
```

### Flujo de verificación e infracción

```
1. Inspector abre "Verificar vehículo"
2. Ingresa patente (teclado o escáner)
3. Sistema evalúa:
   - ¿Exento total? → ✅ libre
   - ¿Pago activo o abono mensual vigente? → ✅ OK
   - ¿Exento parcial en esta subcuadra? → ✅ libre
   - ¿Exento parcial fuera de su subcuadra? → 🚨 INFRACCIONAR
   - ¿Tolerancia (15 min desde última verificación)? → ⏳ esperar
   - ¿Impago / No registrado? → 🚨 INFRACCIONAR
4. Si infracción: inspector confirma, puede sacar foto
   (el sistema captura las coordenadas GPS automáticamente)
5. Se genera Infraccion (estado=pendiente) con geoposición registrada
6. Conductor puede resolver la infracción de dos formas (ver abajo)
```

### Flujo de resolución de infracción — conductor estaciona

```
Conductor registra estacionamiento para ese vehículo
  → Sistema detecta infracción pendiente del vehículo

  ┌─ Dentro del período de gracia (configurado en Admin → Municipio) ──────────┐
  │  Infracción se ANULA automáticamente sin cobrar nada                       │
  │  Conductor ve mensaje verde: "Infracción anulada por período de gracia"    │
  └────────────────────────────────────────────────────────────────────────────┘

  ┌─ Fuera del período de gracia ──────────────────────────────────────────────┐
  │  Estacionamiento se registra normalmente (se cobra el estacionamiento)     │
  │  Infracción queda PENDIENTE de pago                                        │
  │  Conductor ve notificación con 3 timestamps:                               │
  │    🔍 Hora en que fue verificado por el inspector                          │
  │    ⏱  Hora en que venció el período de gracia                             │
  │    🚗 Hora en que registró el estacionamiento                              │
  │  Botón "Ir a pagar la infracción ($X)" → redirige a Mis Infracciones      │
  └────────────────────────────────────────────────────────────────────────────┘
```

### Flujo de resolución de infracción — vendedor cobra por patente

```
Conductor va al kiosco del vendedor a pagar la infracción en efectivo

Vendedor → "Cobrar infracción" → ingresa patente → ve la infracción pendiente
  → Confirma el cobro

  ┌─ Dentro del período de gracia ─────────────────────────────────────────────┐
  │  Infracción se ANULA sin cobrar (el conductor no paga nada)                │
  └────────────────────────────────────────────────────────────────────────────┘

  ┌─ Fuera del período de gracia ──────────────────────────────────────────────┐
  │  Vendedor cobra el monto en efectivo al conductor                          │
  │  Sistema registra MovimientoCaja (ingreso, medio_pago=efectivo)            │
  │  Infracción pasa a estado PAGADA                                           │
  └────────────────────────────────────────────────────────────────────────────┘
```

### Flujo de rendición de caja (inspector/vendedor → admin)

```
Inspector/Vendedor:
  → Acumula movimientos (cobros manuales, infracciones cobradas)
  → Desde "Caja" puede ver el total pendiente
  → Confirma cierre de caja

Admin:
  → Ve la rendición pendiente en el panel del inspector/vendedor
  → Confirma la rendición
  → El saldo del operador se actualiza
  → Queda registro en CierreCaja con auditoría de quién y cuándo
```

### Flujo de horarios y días especiales

```
Admin carga horario semanal tipo:
  Lun-Vie: 08:00 - 15:00  → activo=True
  Sáb: 08:00 - 12:00       → activo=True
  Dom: —                    → activo=False

Admin carga días especiales (con prioridad sobre el horario):
  25/05 Feriado Nacional → cobro_activo=False (libre)
  01/01 Año Nuevo        → cobro_activo=False (libre)
  Caso especial: día de cobro fuera del horario habitual → cobro_activo=True

El sistema consulta:
  1. ¿Hay DiaEspecial para hoy? → usa cobro_activo de ese registro
  2. Si no hay → ¿el horario semanal está activo para hoy? → usa hora_inicio/hora_fin
  3. Si no hay horario para hoy → cobro libre

El sistema cierra automáticamente los estacionamientos activos cuando vence el
horario configurado, aplicando reintegro proporcional si el conductor pagó
por más tiempo del que quedaba disponible.
```

---

## 3. Tipos de Exención — Cuándo usar cada uno

| Tipo | Cuándo aplicar | Documentación requerida |
|------|----------------|------------------------|
| **Discapacitado** | Conductor con certificado de discapacidad vigente | Certificado CUD + DNI |
| **Vecino frentista** | Propietario/inquilino de inmueble en zona de cobro | Cédula de domicilio + DNI con mismo domicilio |
| **Jubilado** | Conductor jubilado/pensionado | Credencial de jubilado ANSES vigente |
| **Fuerzas de seguridad** | Policía, bomberos, gendarmería, prefectura (uso personal) | Credencial institucional |
| **Vehículo oficial** | Vehículos del estado municipal/provincial/nacional | Patente institucional / habilitación oficial |

### Notas importantes
- La exención **global** exime al vehículo en todo el municipio.
- La exención **parcial** exime en subcuadras específicas (ej: frente a la casa del vecino frentista).
- Si el vehículo exento parcial es escaneado fuera de sus subcuadras exentas → **paga igual**.
- El admin debe registrar siempre el **número de documento o certificado** en el campo `notas_exencion`.
- Las exenciones **no tienen vencimiento automático** — el admin debe revisarlas periódicamente.

---

## 4. FAQ por Rol

### FAQ — Administrador

**¿Cómo agrego un conductor?**
El conductor se registra solo (web o Google). Si viene en persona, el admin lo busca en "Conductores" por correo o nombre. Si no existe, el conductor debe crear su cuenta primero.

**¿Cómo le cargo un vehículo a un conductor?**
Busco al conductor en "Conductores" → "Ver" → sección "Agregar vehículo" → ingreso la patente.

**¿Cómo exento un vehículo?**
Desde el detalle del conductor → "Gestionar exenciones" junto al vehículo. O directamente desde "Panel → Exenciones" buscando la patente. Elijo el tipo, anoto el número de documento y marco exento global o selecciono las subcuadras.

**¿Cómo configuro los horarios?**
Panel Admin → "🕐 Horarios". Marco cada día como activo/inactivo y defino la franja horaria. Guardo.

**¿Cómo cargo un feriado?**
Panel Admin → "🕐 Horarios" → "📌 Días especiales" → "Agregar día especial". Pongo la fecha, tipo (feriado/festivo/duelo) y descripción. Por defecto queda como libre de cobro.

**¿Cómo veo las infracciones?**
Panel Admin → barra lateral de Gestión → "📋 Infracciones". Puedo filtrar por patente, inspector, estado y fecha. Puedo anular infracciones pendientes.

**¿Cómo anulo una infracción?**
En "📋 Infracciones" → busco la infracción → botón "Anular" (solo si está pendiente).

**¿Cómo cargo saldo a un conductor?**
En ⚡ Acciones rápidas → "💳 Cargar saldo" → busco al conductor → ingreso el monto → confirmo. El sistema muestra un comprobante con el monto, nuevo saldo, fecha/hora y quién lo registró, listo para imprimir.

**¿Cómo veo el historial de estacionamientos?**
Panel Admin → "🅿️ Estacionamientos" en Acciones rápidas. Puedo filtrar por patente, estado y rango de fechas.

**¿Cómo veo todos los vehículos registrados?**
Panel Admin → Gestión → "🚗 Vehículos". Puedo filtrar por patente y tipo (auto/moto). Muestra el conductor asignado y si tiene exención.

**¿Cómo cobro un abono mensual?**
Panel Admin → "📅 Cobrar abono" en Acciones rápidas. Ingresá la patente, elegí el vehículo, seleccioná el mes y el monto. El cobro queda registrado al 100% en tesorería (sin comisión para el admin).

**¿Cómo cambio la tarifa por hora?**
Panel Admin → "💲 Tarifas" → ingreso el nuevo precio → guardar.

**¿Cómo configuro el porcentaje de ganancia de un inspector?**
Panel Admin → "👮 Inspectores" → click en el inspector → sección "Configuración de rendición".

---

### FAQ — Inspector

**¿Cómo verifico un vehículo?**
Desde mi panel → "🚓 Verificar vehículo". Ingreso la patente directamente. El sistema me muestra el estado.

**¿Tengo que seleccionar subcuadra antes de verificar?**
No. Ingresás la patente directamente y el sistema evalúa el estado del vehículo.

**¿Cómo registro una infracción?**
Si el resultado es 🚨 INFRACCIONAR, aparece el formulario de infracción. Sacás la foto (el sistema captura las coordenadas GPS automáticamente), confirmás y se genera el acta.

**¿Qué pasa si el vehículo tiene exención parcial?**
Si está en una de sus subcuadras exentas → aparece ✅ OK. Si está fuera de ellas → aparece 🚨 INFRACCIONAR — el vehículo igual debe pagar en esa zona.

**¿Qué significa "En plazo de tolerancia"?**
Que el vehículo fue escaneado recientemente (menos de 15 minutos). No podés infraccionar todavía. Volvé en unos minutos.

**¿Cómo cierro mi caja?**
Panel Inspector → "🧾 Caja". Ahí ves tus movimientos abiertos y el total a rendir. Si hay movimientos pendientes, aparece el botón "Confirmar cierre de caja".

**¿Puedo cobrar manualmente a un vehículo exento?**
No. Si el vehículo tiene exención total, el sistema bloquea el cobro manual con un mensaje de error.

**¿Qué es el saldo operativo?**
Es el total de ingresos acumulados que gestionaste (cobros + infracciones cobradas). Te da una idea de cuánto dinero pasó por tu caja.

---

### FAQ — Conductor

**¿Cómo pago el estacionamiento?**
Iniciás sesión → "Estacionar" → elegís tu auto (o ingresás la patente) → elegís la duración → el sistema descuenta del saldo.

**¿Cómo cargo saldo?**
Desde tu panel de inicio → "Recargar saldo" → elegís el monto → te redirige a MercadoPago.

**¿Qué pasa si se me vence el tiempo?**
Podés seguir estacionado, pero si un inspector pasa, te puede infraccionar. Tenés 15 minutos de tolerancia desde que vence el tiempo pagado.

**Me avisaron que tengo una infracción. ¿Cómo la pago?**
Desde tu panel → "Mis infracciones". Ves el detalle y podés pagarla con tu saldo. Si no tenés saldo, podés ir a un kiosco vendedor y pagar en efectivo.

**¿Qué pasa si registro un estacionamiento y tenía una infracción pendiente?**
El sistema lo detecta automáticamente. Si estás dentro del período de gracia configurado por el municipio, la infracción se anula sin cobrar y ves un mensaje verde. Si ya venció el período de gracia, el estacionamiento igual se registra pero ves una notificación con los horarios exactos y un link para ir a pagar la infracción.

**¿Cómo sé si mi vehículo está exento?**
El admin te lo indica cuando procesó tu exención. Podés ver el estado de tus vehículos en el perfil.

**Me aparece "Infracción anulada automáticamente". ¿Qué significa?**
Tu vehículo tenía una infracción pendiente, pero registraste el estacionamiento dentro del período de gracia que configura el municipio. La infracción se canceló automáticamente sin costo.

**¿Cómo pago el abono mensual?**
Desde tu panel de inicio → "📅 Pagar abono". Elegís el vehículo y el mes (podés pagar el mes anterior, el actual o el siguiente). El sistema te muestra el precio y tu saldo disponible. Si tenés saldo suficiente, confirmás y se descuenta automáticamente. Si no tenés saldo, podés cargar con MercadoPago primero.

**¿Qué hago si no tengo cuenta de email?**
Podés entrar con tu cuenta de Google directamente.

---

### FAQ — Vendedor

**¿Cómo registro un estacionamiento?**
Panel Vendedor → "Registrar estacionamiento" → ingresás la patente → la duración → el sistema genera el cobro y el ticket. Si el vehículo tenía una infracción pendiente, el sistema te avisa automáticamente (anulada si está en gracia, pendiente si no).

**¿Cómo cobro una infracción por patente?**
Panel Vendedor → "Cobrar infracción" → ingresás la patente → ves la infracción pendiente → confirmás el cobro. El sistema aplica automáticamente la tolerancia de gracia: si el conductor llega dentro del período, la infracción se anula sin cobrar; si no, cobrás el monto en efectivo y queda registrado en tu caja.

**¿Cómo veo mi resumen de caja?**
Panel Vendedor → "Resumen de caja". Mostrá los movimientos del período.

**¿Cómo hago la rendición al admin?**
Cuando tenés movimientos abiertos aparece el botón "Confirmar cierre de caja". El admin lo verifica de su lado.

---

## 5. Instrucciones de Uso — Paso a Paso

### Puesta en marcha inicial (admin)

1. Crear cuenta admin con `python manage.py crear_admin` (o desde Railway Console)
2. Entrar al sistema con correo y contraseña del admin
3. Ir a **Panel Admin → 💲 Tarifas** → cargar el precio por hora
4. Ir a **Panel Admin → 🕐 Horarios** → configurar los días y horarios de cobro
5. Ir a **Panel Admin → 👮 Inspectores** → crear cuentas de inspectores
6. Ir a **Panel Admin → 💰 Vendedores** → crear cuentas de vendedores
7. Compartir correos y contraseñas con el equipo

### Alta de conductor con exención

1. El conductor se registra en el sistema (web o Google)
2. Admin va a **Panel Admin → 👤 Conductores** → busca por correo
3. Click en "Ver" → agrega el vehículo (patente)
4. Click en "Gestionar exenciones" junto al vehículo
5. Selecciona el tipo de exención, anota el nro de documento
6. Marca "Exento global" o selecciona subcuadras exentas
7. Guarda

### Inicio de turno de inspector

1. Inspector inicia sesión
2. Panel Inspector → "🚓 Verificar vehículo"
3. Ingresa la patente del vehículo a verificar
4. El sistema muestra el estado directamente

### Fin de turno — cierre de caja

1. Inspector va a "🧾 Caja"
2. Revisa los movimientos pendientes
3. Click en "Confirmar cierre de caja"
4. Admin recibe la rendición para revisar

### Carga de feriado

1. Panel Admin → "🕐 Horarios" → "📌 Días especiales"
2. Clic en "Agregar día especial"
3. Fecha: la del feriado
4. Tipo: "Feriado nacional"
5. Descripción: nombre del feriado
6. ¿Cobrar ese día?: desmarcado (libre de cobro)
7. Guardar

### Carga de saldo con comprobante

1. Panel Admin → ⚡ Acciones rápidas → "💳 Cargar saldo"
2. Buscar al conductor por correo o nombre
3. Click en "Ver" → "Cargar saldo manualmente"
4. Ingresar el monto → Confirmar
5. El sistema muestra el comprobante con nombre del conductor, monto, nuevo saldo, fecha/hora y quién lo registró
6. Click en "🖨 Imprimir comprobante" para imprimir o guardar como PDF

---

## 6. Configuración de Producción

### Variables de entorno requeridas en Railway

| Variable | Descripción |
|----------|-------------|
| `SECRET_KEY` | Clave secreta de Django |
| `DEBUG` | `False` en producción |
| `ALLOWED_HOSTS` | `estacionamiento.up.railway.app` |
| `DATABASE_URL` | URL de PostgreSQL (Railway lo inyecta automáticamente) |
| `SITE_ID` | ID del site en Django Admin → Sites (actualmente `2`) |
| `GOOGLE_CLIENT_ID` | Client ID de OAuth 2.0 de Google Cloud |
| `GOOGLE_CLIENT_SECRET` | Client Secret de OAuth 2.0 de Google Cloud |
| `MP_ACCESS_TOKEN` | Access token de MercadoPago (sandbox o producción) |
| `CSRF_TRUSTED_ORIGINS` | `https://estacionamiento.up.railway.app` |

### Primer deploy en un entorno nuevo

1. Crear proyecto en Railway + servicio PostgreSQL
2. Configurar todas las variables de entorno
3. Conectar repo GitHub → Railway autodeploy
4. En Railway Console: `python manage.py crear_admin` para el primer admin
5. En Django Admin → Sites: crear site con el dominio real
6. En Django Admin → Social Applications: crear app Google con el Client ID/Secret
7. Cargar tarifa, horarios e inspectores

### Branding por municipio

Desde Django Admin → Municipios → editar municipio:
- **Logo:** imagen PNG/SVG con fondo transparente (altura recomendada 80px)
- **Color primario:** hex del color principal (ej: `#1a7a3c`)
- **Color secundario:** hex del color hover (ej: `#155f2e`)
- **Nombre del sistema:** texto del navbar si no hay logo (ej: `Estacionamiento Medido`)

---

## 7. Mejoras Futuras (roadmap)

- **Geoposición en foto de infracción:** watermark GPS sobre la foto (coordenadas ya se capturan, falta estamparlas en la imagen)
- **Transferencia de saldo entre conductores** con ventana de aceptación de 24 horas
- **PWA / App instalable** sin publicar en tiendas (manifest.json + service worker)
- **Adjunto de documentos** en exenciones (foto de cédula, certificado de discapacidad, etc.)
- **Notificaciones push** al conductor cuando se acerca el vencimiento
- **Dashboard de métricas** para admin (recaudación por día, inspector más activo, etc.)
- **Integración con padrón municipal** para verificar vecinos frentistas automáticamente
- **Renovación de exenciones** con fecha de vencimiento y aviso al admin
- **MercadoPago producción** (migrar de sandbox a credenciales productivas)
- **Configurar email en Railway** (recuperación de contraseña en producción)


Para enviar por whatsapp:
🛠️ ADMINISTRADOR — EstacionAR
Panel Admin → ⚡ Acciones rápidas:
🚗 Registrar estacionamiento
💳 Cargar saldo (genera comprobante para imprimir)
📅 Cobrar abono mensual
⚠️ Cobrar infracción
🅿️ Ver historial de estacionamientos
Gestión lateral:
🚗 Vehículos — ver todos los autos/motos registrados, filtrar por patente o tipo
📋 Infracciones — filtrar, anular
👤 Conductores, 👮 Inspectores, 💰 Vendedores
💲 Tarifas, 🕐 Horarios, 📌 Días especiales
Para cargar saldo con comprobante:
Acciones rápidas → 💳 Cargar saldo → buscar conductor → ingresar monto → confirmar → 🖨 Imprimir comprobante
Para cobrar abono mensual:
Acciones rápidas → 📅 Cobrar abono → ingresar patente → elegir mes → confirmar (100% va a tesorería, sin comisión)
Para exentar un vehículo:
Conductores → Ver → Gestionar exenciones → elegir tipo → anotar nro de documento → guardar
Para cargar un feriado:
Horarios → Días especiales → Agregar → fecha + tipo "Feriado nacional" → dejar desmarcado "cobrar ese día"

🚓 INSPECTOR — EstacionAR
Para verificar un vehículo:

Entrá a tu panel → "Verificar vehículo"
Ingresá la patente directamente (no hace falta elegir subcuadra)
El sistema te muestra el estado: ✅ OK / 🚨 INFRACCIONAR / ⏳ En tolerancia

Para autos: la patente tiene formato AAA111
Para motos: la patente tiene formato 123-ABC
Si el resultado es 🚨 INFRACCIONAR:
Aparece el formulario. Sacá la foto (el GPS se captura solo), completá los datos y confirmá. Se genera el acta automáticamente.
Tolerancia: si el vehículo fue verificado hace menos de 15 minutos no podés infraccionar. Volvé en unos minutos.
Exentos parciales: si el vehículo tiene exención en OTRA subcuadra, en la tuya igual hay que infraccionar. El sistema te lo indica.
Al terminar el turno:
Panel → 🧾 Caja → ver movimientos → "Confirmar cierre de caja"

💰 VENDEDOR — EstacionAR
Para registrar un estacionamiento:
Panel → "Registrar estacionamiento" → patente → duración → confirmar → se genera el ticket
Para cobrar una infracción:
Panel → "Cobrar infracción" → patente → ver detalle → confirmar cobro
⚠️ Si el conductor llega dentro del período de gracia, la infracción se ANULA sin cobrar.
Para cobrar un abono mensual:
Panel → "Cobrar abono" → patente → elegir mes → confirmar
(Genera comisión para vos según el porcentaje configurado)
Para ver tu caja:
Panel → "Resumen de caja"
Para hacer la rendición:
Cuando tenés movimientos abiertos aparece el botón "Confirmar cierre de caja". El admin lo verifica de su lado.

🚗 CONDUCTOR — EstacionAR
Para estacionar:
Ingresá al sistema → "Estacionar" → elegí tu auto → elegí duración (1, 2 o 3 horas) → se descuenta del saldo
Para cargar saldo:
Panel de inicio → "Recargar saldo" → elegí el monto → MercadoPago
Para pagar el abono mensual:
Panel de inicio → "📅 Pagar abono" → elegí vehículo y mes → confirmar (se descuenta del saldo)
Para ver y pagar infracciones:
Panel → "Mis infracciones" → podés pagar con tu saldo digital
También podés ir a un kiosco vendedor a pagar en efectivo.
Si registrás un estacionamiento y tenías una infracción pendiente:
— Dentro del período de gracia → la infracción se ANULA sola, sin costo ✅
— Fuera del período → el estacionamiento igual se registra, pero aparece un aviso con los horarios exactos y un botón para ir a pagar la infracción
