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
1. Inspector abre "Verificar vehículo" → elige subcuadra donde patrulla
2. Ingresa patente (teclado o escáner)
3. Sistema evalúa:
   - ¿Exento total? → ✅ libre
   - ¿Pago activo? → ✅ OK
   - ¿Exento parcial en esta subcuadra? → ✅ libre
   - ¿Exento parcial fuera de su subcuadra? → 🚨 INFRACCIONAR
   - ¿Tolerancia (15 min desde última verificación)? → ⏳ esperar
   - ¿Impago / No registrado? → 🚨 INFRACCIONAR
4. Si infracción: inspector confirma subcuadra y puede sacar foto
5. Se genera Infraccion (estado=pendiente)
6. Conductor recibe notificación
7. Conductor puede pagar la infracción desde su panel
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

(Cierre automático de estacionamientos al vencer horario: mejora futura)
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
Panel Admin → "📋 Infracciones". Puedo filtrar por patente, inspector, estado y fecha. Puedo anular infracciones pendientes.

**¿Cómo anulo una infracción?**
En "📋 Infracciones" → busco la infracción → botón "Anular" (solo si está pendiente).

**¿Cómo cargo saldo a un conductor?**
Desde "Conductores" → "Ver" conductor → "Cargar saldo manualmente".

**¿Cómo cambio la tarifa por hora?**
Panel Admin → "💲 Tarifas" → ingreso el nuevo precio → guardar.

**¿Cómo configuro el porcentaje de ganancia de un inspector?**
Panel Admin → "👮 Inspectores" → click en el inspector → sección "Configuración de rendición".

---

### FAQ — Inspector

**¿Cómo verifico un vehículo?**
Desde mi panel → "🚓 Verificar vehículo". Primero elijo en qué subcuadra estoy patrullando (selector arriba). Ingreso la patente. El sistema me muestra el estado.

**¿Puedo infraccionar en modo calle?**
Sí. En la pantalla de verificar hay un botón "📱 Modo calle" que agranda la interfaz para usar con el celular al sol.

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
Desde tu panel → "Mis infracciones". Ves el detalle y podés pagarla desde ahí.

**¿Cómo sé si mi vehículo está exento?**
El admin te lo indica cuando procesó tu exención. Podés ver el estado de tus vehículos en el perfil.

**Me dice que pagué a tiempo y se canceló la infracción. ¿Qué significa?**
Un inspector escaneó tu patente, pero pagaste el estacionamiento antes de que pasaran los 15 minutos de tolerancia. La infracción fue automáticamente cancelada.

**¿Qué hago si no tengo cuenta de email?**
Podés entrar con tu cuenta de Google directamente.

---

### FAQ — Vendedor

**¿Cómo registro un estacionamiento?**
Panel Vendedor → "Registrar estacionamiento" → ingresás la patente → la duración → el sistema genera el cobro y el ticket.

**¿Cómo veo mi resumen de caja?**
Panel Vendedor → "Resumen de caja". Mostrá los movimientos del período.

**¿Cómo hago la rendición al admin?**
Igual que el inspector: cuando tenés movimientos abiertos aparece el botón "Confirmar cierre de caja". El admin lo verifica de su lado.

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
3. Selecciona la subcuadra donde va a patrullar
4. Comienza a escanear patentes

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

---

## 6. Mejoras Futuras (roadmap)

- **Cierre automático de estacionamientos** al vencer el horario + reintegro proporcional
- **Adjunto de documentos** en exenciones (foto de cédula, certificado de discapacidad, etc.)
- **Verificación documental** por parte del admin antes de aprobar la exención
- **Notificaciones push** al conductor cuando se acerca el vencimiento
- **Dashboard de métricas** para admin (recaudación por día, inspector más activo, etc.)
- **App móvil** para inspectores (PWA o nativa)
- **Integración con padrón municipal** para verificar vecinos frentistas automáticamente
- **Renovación de exenciones** con fecha de vencimiento y aviso al admin
