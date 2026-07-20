# Pendiente — Estacionamiento Proyecto

Última actualización: 2026-07-20

---

## 🔴 Alta prioridad

### Media storage persistente (Cloudinary)
Las fotos de infracciones se guardan en disco local (`media/`). Railway tiene **filesystem efímero**: los archivos se borran al hacer redeploy o restart.

Pasos:
1. Crear cuenta en https://cloudinary.com (plan free, 25 GB)
2. `pip install cloudinary django-cloudinary-storage` + agregar a `requirements.txt`
3. En `settings.py`:
   ```python
   INSTALLED_APPS += ["cloudinary_storage", "cloudinary"]
   CLOUDINARY_STORAGE = {
       "CLOUD_NAME": env("CLOUDINARY_CLOUD_NAME"),
       "API_KEY":    env("CLOUDINARY_API_KEY"),
       "API_SECRET": env("CLOUDINARY_API_SECRET"),
   }
   DEFAULT_FILE_STORAGE = "cloudinary_storage.storage.MediaCloudinaryStorage"
   ```
4. Agregar 3 variables en Railway: `CLOUDINARY_CLOUD_NAME`, `CLOUDINARY_API_KEY`, `CLOUDINARY_API_SECRET`

**Afecta**: `Infraccion.foto`, `Municipio.logo`.

### Verificar.html — subcuadra + exento parcial antes del acta

Dos mejoras relacionadas:

**1. Selector de subcuadra en verificar.html (trazabilidad)**
El inspector debe seleccionar en qué subcuadra está patrullando *antes* de verificar,
para que la infracción registre la ubicación correcta. Actualmente se selecciona en el
formulario del acta pero no hay contexto de dónde está el inspector al escanear.
— Agregar selector de subcuadra en la pantalla de verificación.
— Pasar la subcuadra seleccionada a `registrar_infraccion` por query param o sesión.

**2. Exento parcial: mostrar estado ANTES de ir al acta**
Si el resultado es `EXENTO_PARCIAL`, el inspector actualmente ve el botón de infraccionar
sin saber si está en la subcuadra exenta o no.
— Mostrar al momento de verificar si el vehículo está exento en la subcuadra actual.
— Solo si está FUERA de sus subcuadras exentas mostrar la opción de infraccionar.
— Actualmente esto se resuelve al "grabar el acta" (demasiado tarde).

### Watermark: agregar subcuadra al texto de la foto
El watermark actual incluye: patente, inspector, GPS, fecha/hora.
Falta: **subcuadra** donde se labró el acta.
— Modificar `_agregar_marca_de_agua_gps` para recibir y mostrar `subcuadra`.
— Actualizar llamada en `crear_infraccion()` y pasar `subcuadra.nombre`.

### Bug: foto en infracción — verificar flujo completo
Algunas infracciones se guardaron sin foto. La foto tiene que mostrar:
coordenadas GPS + subcuadra + timestamp.
— Una vez implementado Cloudinary, verificar manualmente que la foto llega correcta a la BD.
— Si el problema persiste, agregar log en `crear_infraccion()` para registrar si `foto` llega None.

---

## 🟡 Media prioridad

### 1. Panel admin: métrica "Sin rendir a tesorería"
Reemplazar `${{ total_cobrado }}` (suma histórica total) por el monto acumulado
**sin rendir a tesorería** del municipio.
Cálculo: suma de `MovimientoCaja.monto` donde `tipo="ingreso"` y el `CierreCaja`
asociado aún no fue certificado (o donde no hay cierre de caja todavía).
Incluir también rendiciones de puntos de venta que ya rindieron.

### 2. Alta de conductor desde admin
Desde `/usuarios/admin-usuarios/` agregar botón "➕ Nuevo conductor".
Form: nombre, apellido, correo, contraseña provisional.
Después de crear → ir al detalle del conductor para agregar vehículo y exención.
Permite al admin registrar conductores que vienen en persona sin que se registren solos.

### 3. Cobrar abono: comprobante imprimible
Después de confirmar el cobro de un abono (✅ Confirmar cobro — ${{ precio }}),
mostrar comprobante para imprimir/entregar. Similar al comprobante de cargar_saldo.
Debe incluir: patente, vehículo, mes, monto, quién cobró, fecha/hora, municipio.

### 4. Admin-vendedores: historial de operaciones del punto de venta
Click en nombre del vendedor → nueva vista con:
- Todos los `MovimientoCaja` del vendedor (fecha, tipo, descripción, monto, comisión)
- Posibilidad de editar/anular movimientos individuales (con motivo)
- Totales del período

### 5. Admin-rendiciones: separar en dos secciones
`/usuarios/admin-rendiciones/` debe mostrar claramente separadas:
- **Rendiciones a Tesorería** (del admin al tesorero): historial, estados, observaciones
- **Comisiones a Puntos de Venta** (del municipio a los vendedores): pendientes de depósito,
  depositadas, certificadas por el vendedor

Flujo ya implementado en el modelo (`LiquidacionComision`):
  `pendiente` → tesorería marca como `depositada` → vendedor certifica como `certificada`.
La UI de separación es lo que falta.

### 6. Admin-exenciones: flujo completo + listado global
**Agregar exención a patente nueva:**
Si la patente ingresada no existe en el sistema:
  1. Crear/buscar conductor por DNI o correo
  2. Agregar la patente a ese conductor
  3. Otorgar la exención
Si existe pero no tiene exención → ir directamente al formulario de exención.

**Listado global de exenciones:**
Mostrar tabla de TODAS las patentes con exención activa:
- Patente, tipo de vehículo, conductor, tipo de exención (Global/Parcial), subcuadras exentas (si parcial)
Filtros: tipo de exención, estado.

### 7. Transferencia de saldo entre usuarios
El conductor puede transferir saldo a otro conductor. El receptor tiene **24 horas** para aceptar;
si no responde, el monto se reintegra automáticamente al emisor.
Pendiente de diseño:
- Nuevo modelo `TransferenciaSaldo` (emisor, receptor, monto, estado: `pendiente`/`aceptada`/`rechazada`/`expirada`, creado_en).
- Vista de envío (buscar receptor por correo o DNI).
- Vista de recepción/rechazo (notificación en el panel del receptor).
- Lógica de expiración: verificar en login o con tarea periódica (Celery o chequeo reactivo).

### 8. Configurar email en Railway (recuperación de contraseña)
En local los emails aparecen en la consola (backend `console`). En Railway hay que setear 3 variables:
```
EMAIL_HOST_USER=tumail@gmail.com
EMAIL_HOST_PASSWORD=xxxx xxxx xxxx xxxx   ← contraseña de app de Google
DEFAULT_FROM_EMAIL=Sistema Estacionamiento <tumail@gmail.com>
```
**Disparador**: cuando se reactive el deploy en Railway.

### 9. Tests faltantes
- Flujo MP webhook (integración)
- `TestWatermarkGPS` pasando en Railway (verificar con Cloudinary activo)

---

## 🟢 Baja prioridad / Futuras versiones

### Rendiciones: balances mensuales + rol Staff
- Resumen mensual de rendiciones a tesorería (totales por período)
- Campos para enviar el resumen por mail a personas del Staff
- Nuevo rol `Staff`: solo reciben mails del sistema, pero también son usuarios.
  Algunos comparten correo con su cuenta de sistema → manejar como alias o campo separado.
- Implementar envío de mails desde Django (depende de ítem 8)

### Flujo tesorería → vendedor: verificar UI completa
El modelo `LiquidacionComision` ya tiene el flujo modelado:
  Tesorería deposita → vendedor certifica recepción.
Existe `depositar_comision` (tesorero) y `certificar_comision` (vendedor).
Verificar que la UI del vendedor sea clara para confirmar que recibió su comisión.

### Responsive > 1050px
En pantallas grandes el layout del panel admin (sidebar 260px + contenido) queda con
mucho espacio vacío. Revisar grid y max-width del contenido principal.

### PWA / App móvil sin Play Store
`manifest.json` + service worker básico (offline fallback).

### Evaluar migración a Digital Ocean
**Disparador**: cuando el sistema tenga usuarios reales pagando.

### Inspector como cobrador
Agregar rol "inspector" al decorator de `registrar_estacionamiento_vendedor` y `cobrar_abono`.

### Mejoras OAuth y UI
- Pantalla de consentimiento Google: completar logo, descripción, dominio verificado
- Modo alto contraste / uso en exterior con sol
- Separar `settings_dev.py` / `settings_prod.py`

### Limpiar inicio_admin.html
`templates/admin/inicio_admin.html` existe pero no se usa. El panel real es `panel_admin.html`.
Eliminar o redirigir.

---

## ✅ Resuelto

### feat: mejoras UI admin y vendedor (commit 2861f48, 2026-07-20) ✅
- **cobrar-infraccion**: muestra TODAS las infracciones pendientes por patente (no solo la última).
  View: queryset completo. Template: loop con card por infracción, botón Cobrar individual.
- **gestionar_inspectores**: eliminados `periodicidad_rendicion` y `porcentaje_ganancia` del form de crear inspector.
- **cobrar_abono**: template movido a `templates/admin/cobrar_abono.html`, view actualizado, botón quitado del panel vendedor.
- **gestionar_vendedores**: tabla con datos completos (negocio, propietario, teléfono, horario).
- **panel_admin**: infracciones_recientes muestra 20 en vez de 5.

### Modal "detalle de infracción" + motivo_anulacion (commit anterior, 2026-07-20) ✅
- Campo `motivo_anulacion = models.TextField(blank=True, default="")` en `Infraccion` + migración 0040.
- Vista `admin_infracciones`: acciones Cobrar y Anular por POST (con validación de motivo vacío).
- Template `infracciones.html`: modal JS con foto, todos los datos, botones Cobrar/Anular por infracción.
- Panel admin: infracciones_recientes clickeables → abren modal con `?detalle=ID`.

### Geoposición en infracción: watermark GPS ✅
- `services/infracciones.py::_agregar_marca_de_agua_gps`: overlay oscuro + texto con patente, inspector, GPS, fecha/hora.
- `crear_infraccion()` aplica el watermark automáticamente cuando hay `foto and gps_lat and gps_lon`.
- `registrar_infraccion` (view) lee GPS del POST y lo pasa al service.
- Template: JS captura GPS, chip visual de estado, campos ocultos, botón deshabilitado hasta obtener ubicación.
- Pillow 12.0.0 en `requirements.txt`.
- Tests: `TestWatermarkGPS` en `tests_servicios.py` (3 tests verdes).

### feat: mejoras post-presentación municipal (commit e79eb22, 2026-07-16) ✅
- Registro de conductor con nombre + apellido (evita redirect middleware).
- Nombres en title case.
- Sanitización de patentes (`sanitizar_patente()` en `utils.py`, 11 templates).
- Mínimo 1 hora (`calcular_opciones_duracion()` arranca en `n=2`).
- Reintegro < 30 min (`UMBRAL_REINTEGRO_MINUTOS = 30`).
- Admin cargar saldo: bug corregido (mostraba correo del admin en vez del conductor).
- MercadoPago nombre: corregido en portal de MP.

### Panel admin sidebar + nuevas vistas ✅
- Layout dos columnas: sidebar 260px fijo + contenido.
- ⚡ Acciones rápidas: 🚗 Registrar, 💳 Cargar saldo, 📅 Cobrar abono, ⚠️ Cobrar infracción, 🅿️ Estacionamientos.
- Gestión lateral con badges de pendientes.
- Vistas nuevas: `admin_vehiculos` y `admin_estacionamientos` con filtros y paginación.

### Cargar saldo: comprobante imprimible ✅
La vista `cargar_saldo` muestra comprobante con monto, nuevo saldo, fecha/hora y quien lo registró.
`@media print` oculta nav/footer. Botón "🖨 Imprimir comprobante".

### Inspector UI: múltiples mejoras ✅
- `base.html` truncado (bug crítico): hamburger no funcionaba en ninguna vista. Corregido.
- Eliminado `id="form-subcuadra"` del flujo de verificación.
- Oculto botón "Modo calle/escritorio".
- Placeholder moto: `123-ABC`.
- Rediseño `registrar_infraccion.html`: chip GPS, label FOTO, botón grande.

### Cobrar abono: fixes ✅
- "Volver" usa `volver_url` desde el view (admin → panel_admin, vendedor → panel_vendedor).
- Eliminado mensaje "Comisión generada: $0".

### Otros ✅
- `ticket.html` rediseñado con header verde, patente grande, `@media print`.
- Eliminado aviso "mejora futura" de gestionar_horarios (cierre automático ya implementado).
- Inspector PDF del día: `pdf_infracciones_hoy` con reportlab.
- Rol Tesorero: flujo completo (validar rendiciones, liquidaciones, 17 tests).
- 106 tests pasando.
