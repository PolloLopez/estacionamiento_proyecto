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

### Bug: foto en infracción — verificar flujo completo
Algunas infracciones se guardaron sin foto.
— Una vez implementado Cloudinary, verificar end-to-end que foto llega a la BD.
— Si persiste, agregar log en `crear_infraccion()` cuando `foto` llega None.

---

## 🟡 Media prioridad

### 1. Transferencia de saldo entre usuarios
El conductor puede transferir saldo a otro conductor. El receptor tiene **24 horas** para aceptar;
si no responde, el monto se reintegra automáticamente al emisor.
Pendiente de diseño:
- Nuevo modelo `TransferenciaSaldo` (emisor, receptor, monto, estado, creado_en).
- Vista de envío (buscar receptor por correo o DNI).
- Vista de recepción/rechazo (notificación en panel del receptor).
- Lógica de expiración: verificar en login o con tarea periódica.

### 2. Configurar email en Railway (recuperación de contraseña)
En local los emails aparecen en la consola. En Railway hay que setear 3 variables:
```
EMAIL_HOST_USER=tumail@gmail.com
EMAIL_HOST_PASSWORD=xxxx xxxx xxxx xxxx   ← contraseña de app de Google
DEFAULT_FROM_EMAIL=Sistema Estacionamiento <tumail@gmail.com>
```
**Disparador**: cuando se reactive el deploy en Railway.

### 3. Tests faltantes
- Flujo MP webhook (integración)
- `TestWatermarkGPS` pasando en Railway (verificar con Cloudinary activo)

---

## 🟢 Baja prioridad / Futuras versiones

### Rendiciones: balances mensuales + rol Staff
- Resumen mensual de rendiciones a tesorería
- Nuevo rol `Staff`: solo reciben mails
- Implementar envío de mails desde Django (depende de email Railway)

### Flujo tesorería → vendedor: verificar UI completa
El modelo `LiquidacionComision` ya tiene el flujo modelado.
Verificar que la UI del vendedor sea clara para certificar que recibió su comisión.

### Responsive > 1050px
En pantallas grandes el layout del panel admin queda con mucho espacio vacío.

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
`templates/admin/inicio_admin.html` existe pero no se usa. Eliminar o redirigir.

---

## ✅ Resuelto

### feat: inspector — subcuadra + exento parcial + watermark (2026-07-20) ✅
- **verificar.html**: selector de subcuadra visible (dropdown, guarda en sesión).
  Inspector elige dónde está patrullando antes de verificar.
- **services/verificacion.py**: cuando el vehículo tiene exención parcial pero está
  FUERA de su zona exenta → retorna `EXENTO_PARCIAL` con `exento_en_subcuadra_actual=False`.
  El template ya mostraba el botón de infraccionar en ese caso.
- **registrar_infraccion**: lee `subcuadra_inspector_id` de sesión en lugar de usar
  la subcuadra default. El dropdown del acta queda pre-seleccionado con la subcuadra activa.
- **_agregar_marca_de_agua_gps**: nuevo parámetro `subcuadra` (opcional). Se agrega
  "Subcuadra: ..." como línea del overlay de la foto.
- 6 nuevos tests: `TestExentoParcialFueraDeZona` (4) + `TestWatermarkConSubcuadra` (2).

### feat: mejoras UI admin — exenciones, rendiciones, historial (commit 4152c0d, 2026-07-20) ✅
- **exenciones.html**: si el vehículo no existe → form para crearlo + asignar exención.
  Listado global de todos los vehículos con exención activa en el municipio.
- **rendiciones.html**: 3 secciones con tabs (Cierres de caja / Rendiciones a tesorería / Comisiones a vendedores).
  `LiquidacionComision` agregado al context. Navegación por `?seccion=`.
- **historial_vendedor**: nueva view + URL + template. MovimientoCaja con filtros por fecha,
  totales (ingresos, egresos, comisiones, neto municipio). Botón en gestionar_vendedores.
- **crear_conductor**: nueva view + URL + template. Alta desde admin (nombre, apellido, correo, contraseña).
  Valida duplicados y contraseña mínima. Redirige a detalle_usuario_admin.
- **gestionar_usuarios.html**: botón "➕ Nuevo conductor".

### feat: métricas y abono (2026-07-20) ✅
- **panel_admin**: métrica "Sin rendir a tesorería" = abiertos (cerrado=False) + CierreCaja no certificados.
- **cobrar_abono**: comprobante imprimible después de confirmar el cobro. `@media print`.

### feat: mejoras UI admin y vendedor (commit 2861f48, 2026-07-20) ✅
- **cobrar-infraccion**: todas las infracciones pendientes por patente (loop con card individual).
- **gestionar_inspectores**: eliminados `periodicidad_rendicion` y `porcentaje_ganancia`.
- **cobrar_abono**: template movido a `admin/`, quitar botón del panel vendedor.
- **gestionar_vendedores**: tabla con datos completos.
- **panel_admin**: infracciones_recientes muestra 20 en vez de 5.

### Modal "detalle de infracción" + motivo_anulacion (2026-07-20) ✅
- Campo `motivo_anulacion` en `Infraccion` + migración 0040.
- Modal JS con foto, datos, botones Cobrar/Anular. Panel admin clickeable.

### Geoposición en infracción: watermark GPS ✅
- `_agregar_marca_de_agua_gps`: overlay + texto. Tests: 3 verdes.

### feat: mejoras post-presentación municipal (commit e79eb22, 2026-07-16) ✅
- Nombre + apellido conductor, title case, sanitización patentes, mínimo 1 hora,
  reintegro < 30 min, bug admin saldo, MercadoPago nombre.

### Panel admin sidebar + nuevas vistas ✅
- Layout sidebar 260px. Vistas admin_vehiculos y admin_estacionamientos.

### Cargar saldo: comprobante imprimible ✅
### Inspector UI: múltiples mejoras ✅
### Cobrar abono: fixes (Volver, sin comisión $0) ✅
### Otros ✅ (ticket.html, gestionar_horarios, PDF inspector, Rol Tesorero, 106 tests)
