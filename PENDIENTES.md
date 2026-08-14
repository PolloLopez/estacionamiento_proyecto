# Pendientes — Estacionamiento Proyecto

Última actualización: 2026-08-13 (sesión: pagos públicos sin registro + mejoras PWA + branding superadmin)

---

## 🗺️ Contexto de deploy

- **Railway** → ambiente de prueba (inspectores + admin testeando). No es producción municipal real.
- **Digital Ocean** → deploy definitivo cuando el sistema vaya a municipios reales pagando.
- El código es el mismo; los cambios son de infraestructura y configuración.

---

### ~~🔴 Importación de exenciones desde Excel~~ ✅ RESUELTO 2026-08-11
Planilla real: `Patente | Nombre y Apellido | Direccion | Telefono | Fecha | Condicion | Vencimiento`.
Sin emails → no se crean usuarios. Todos los registros quedan `exencion_verificada=False` para que el admin
contacte a cada titular por teléfono y complete los datos.
- `Vehiculo.vigencia_exencion (DateField)` + `exencion_verificada (BooleanField, default=True)` → migración 0050.
- Vista `importar_exenciones`: preview fila x fila (✅/⚠️/❌) con datos en sesión; confirmación guarda.
  Dirección → coincidencia parcial de calle en Subcuadra del municipio. Datos en `notas_exencion`.
- `panel_exenciones`: acción `verificar`; lista separada en pendientes (con badge naranja) y verificados.
- URL `/admin-exenciones/importar/`, botón 📥 en `exenciones.html`.

### ~~🔴 Plantillas de documentos por municipio (desde superadmin)~~ ✅ RESUELTO 2026-08-11
Modelo `PlantillaDocumento` (municipio, tipo, encabezado, cuerpo, pie) + migración 0049.
5 tipos: `acta`, `cobro_hora`, `abono`, `cobro_infraccion`, `anulacion`.
Helper `obtener_plantilla()` en utils.py. View `gestionar_plantillas(municipio_id)` en views_superadmin.py.
Template `superadmin/plantillas.html`: tabs por tipo, textareas, referencia de variables disponibles.
URL `/superadmin/municipio/<id>/plantillas/` + botón en `editar_municipio.html`.
Integrado en los 5 tickets con `texto_plantilla.encabezado/cuerpo/pie` — degradación elegante: sin plantilla → texto hardcodeado.

### ~~🔴 Pagos públicos sin registro (MercadoPago)~~ ✅ RESUELTO 2026-08-13
Modelo `PagoPublico` (migración 0051) — FK nullable a Infraccion/Estacionamiento/AbonoMensual.
Use case `procesar_pago_publico.py` — idempotente, con `select_for_update()`.
Webhook MP actualizado: detecta `metadata.pago_publico_id` antes del flujo de saldo.
4 templates nuevos: `buscar.html`, `detalle_patente.html`, `resultado.html`, `error.html`.
QR en ticket de infracción: apunta a `/pagar/<patente>/` via `api.qrserver.com`.
URLs en `/pagar/...`. Inspector GPS público en `subcuadra_cercana_publica`.

### ~~PWA: botón instalar + hamburguesa + branding superadmin~~ ✅ RESUELTO 2026-08-13
`beforeinstallprompt` capturado en `base.html` → botón "📲 Instalar" en navbar.
Hamburguesa: `background:none; border:none` en `.menu-toggle` (global.css).
Superadmin `editar_municipio`: upload logo, colores primario/secundario, nombre_sistema.

### 🔴 PRODUCCIÓN: Sin backups automáticos del PostgreSQL de Railway Hobby
Railway Hobby no incluye backups automáticos. Opciones:
- **Railway Pro** ($20/mes): habilita backups diarios desde el dashboard.
- **Script `pg_dump`** vía scheduled task o GitHub Actions → sube a S3/Backblaze/GCS.
Verificar que el backup se puede restaurar al menos una vez antes del go-live real.
Ver: `CHECKLIST_PRODUCCION_2026-07-25.md` — item 🔴 #1.

### ~~🔐 SEGURIDAD: Idempotencia MP basada en texto libre~~ ✅ RESUELTO 2026-08-10
`MovimientoCaja.mp_payment_id (CharField unique)` — migración 0047. Verifica por campo exacto en lugar de `descripcion__contains`. 6 tests en `TestAcreditarSaldoMp`.

---

## 🟡 Media prioridad

### 3. Configurar email en Railway (recuperación de contraseña)
SMTP bloqueado en Railway (puertos 587/465 no disponibles). Se migró a API transaccional:
- **Backend**: `django-anymail[brevo,resend]` instalado, `anymail` en INSTALLED_APPS ✅
- **Brevo** (primera opción): cuenta creada, pero verificación del remitente incompleta.
  Completar desde Brevo → Senders & Domains → verificar `leandrolopezalbini@gmail.com`.
  Luego agregar en Railway: `BREVO_API_KEY=...` + `DEFAULT_FROM_EMAIL=leandrolopezalbini@gmail.com`
- **Resend** (segunda opción): requiere dominio propio verificado — no viable por ahora.
  ⚠️ La API key `re_95PPXHDZ_...` quedó expuesta en chat — **regenerar urgente** en resend.com
- **Workaround activo**: admin puede cambiar contraseña de cualquier conductor desde `/admin-usuarios/` ✅

Mientras tanto, `ACCOUNT_EMAIL_VERIFICATION = "none"` + recuperación de contraseña desactivada en Railway.

### 4. Exportación de reportes a Excel/PDF (parcial)
Implementado:
— **Infracciones impagas → PDF juzgado**: `/admin-infracciones/pdf-juzgado/` (usa reportlab).
— **Inspectores → Excel**: `/admin-inspectores/estadisticas/excel/` ✅

Pendiente: ~~**Rendiciones**: exportar cierre de caja a PDF para tesorería~~ ✅ RESUELTO 2026-08-10 — `pdf_rendicion` view + botón 📄 en tabla admin y panel tesorero.

### 5. 🔐 SEGURIDAD: Verificación de email al registrarse
`ACCOUNT_EMAIL_VERIFICATION = "none"` permite registrarse con cualquier email sin verificar.
Activar cuando email SMTP esté configurado en Railway.
Depende de: Email configurado en Railway (ver punto 3).

⚠️ **Actualización auditoría 2026-08-03**: combinado con `SOCIALACCOUNT_AUTO_SIGNUP = True`,
permite un ataque de pre-registro: alguien se registra con el correo de otra persona (sin
verificarlo) y, cuando la víctima entra con Google OAuth, allauth puede vincular el login social
a la cuenta ya existente. Mientras no se active la verificación mandatoria, evaluar bloquear
el auto-connect en `SocialAccountAdapter.save_user`.
[`views_auth.py:110-139`, `forms.py`, `adapters.py`]

### 6. Transferencia de saldo entre usuarios
El conductor puede transferir saldo a otro conductor. El receptor tiene **24 horas** para aceptar.
Pendiente de diseño:
- Nuevo modelo `TransferenciaSaldo` (emisor, receptor, monto, estado, creado_en).
- Vista de envío (buscar receptor por correo o DNI).
- Vista de recepción/rechazo (notificación en panel del receptor).
- Lógica de expiración: verificar en login o con tarea periódica.

### 7. Tests faltantes
- Flujo MP webhook (integración)
- `TestWatermarkGPS` pasando en Railway (verificar con Cloudinary activo)

---

## 🟢 Baja prioridad / Futuras versiones

### Rendiciones: balances mensuales + rol Staff
- Resumen mensual de rendiciones a tesorería
- Nuevo rol `Staff`: solo reciben mails
- Implementar envío de mails desde Django (depende de email Railway)

### Panel admin "Sin rendir" — métrica revisada
La métrica fue removida del panel (código muerto). Si se quiere restaurar, el criterio correcto
es `CierreCaja.objects.filter(certificado=True, rendicion__isnull=True)` — cierres que el admin
ya certificó pero todavía no incluyó en ninguna Rendición. El campo `rendicion` FK en CierreCaja
ahora permite calcular esto de forma precisa.

### ~~🔐 Logging de eventos de seguridad~~ ✅ RESUELTO 2026-08-10
`require_role()` loguea WARNING en 403 (correo, path, roles, IP). `login_view()` loguea WARNING en fallo de autenticación (correo, IP). Visible en Sentry y logs Railway.

### 🔐 Límite máximo de monto en MercadoPago
Validar en `mp_iniciar_carga` que el monto no supere un tope (ej. $50.000).

### 🔐 Hallazgos menores — auditoría de seguridad 2026-08-03
- `registro_view`: no valida que el `municipio_id` recibido por POST tenga `activo=True`.
- `importar_estacionamientos`: sin límite de tamaño antes de `openpyxl.load_workbook()`.
- `mp_webhook`: la firma HMAC no valida que el `ts` del manifest sea reciente (anti-replay).
- `django-axes`: solo bloquea por IP; como mejora evaluar umbral combinado IP+usuario.

### Responsive > 1050px
En pantallas grandes el layout del panel admin queda con mucho espacio vacío.

### PWA / App móvil sin Play Store
`manifest.json` + service worker básico (offline fallback).

### Migración a Digital Ocean (producción municipal real)
**Disparador**: cuando el sistema pase de pruebas a municipio real pagando.
Ver checklist: `CHECKLIST_PRODUCCION_2026-07-25.md`.

### Inspector como cobrador (configurable por municipio)
No todos los municipios usan al inspector como cobrador. Debe ser un toggle
gestionado por el superadmin (via `ModuloMunicipio` o flag en `Municipio`).
Cuando está activo: habilitar inspector en `registrar_estacionamiento_vendedor` y `cobrar_abono`.
Cuando está inactivo: inspector solo verifica y labra actas (comportamiento actual).

### Mejoras OAuth y UI
- Pantalla de consentimiento Google: completar logo, descripción, dominio verificado.
- Modo alto contraste / uso en exterior con sol.
- Separar `settings_dev.py` / `settings_prod.py`.

### ~~Limpiar inicio_admin.html~~ ✅ RESUELTO 2026-08-10
Template eliminado. La vista `inicio_admin` solo redirige a `panel_admin`, nunca lo renderizaba.

---

## 💰 Mejoras para vender (Plan Premium)

### ~~Detección automática de subcuadra por GPS (con lógica de exenciones)~~ ✅ RESUELTO 2026-08-10
`Subcuadra.lat/lon` (migración 0048) + endpoint `subcuadra_cercana` (distancia euclidiana) +
JS en `verificar.html`: geolocalización silenciosa → preselección automática → indicador "✅ GPS".
Admin carga coordenadas desde `/admin-subcuadras/` con mapa Leaflet/OSM: click en mapa → asignar subcuadra → guardar.
Degradación elegante: municipios sin coordenadas siguen con selección manual.

### Toggle de estadísticas por municipio (desde Django Admin)
`Municipio.estadisticas_inspectores_activo = BooleanField(default=True)`. 1 migración, 1 chequeo.

### Reconocimiento de patente por cámara (OCR)
Google ML Kit, Tesseract.js o API de OCR. Botón "📷 Escanear" en `verificar.html`.

### Alertas de vencimiento al conductor (push / WhatsApp)
Push via service worker (PWA) o WhatsApp via Twilio/360dialog. Link para renovar directamente.

### Mapa de calor de infracciones
Leaflet.js + lat/lon de subcuadras. Requiere coordenadas en Subcuadra (ver GPS arriba).

### Módulo de impugnaciones
`Impugnacion` (infraccion, conductor, motivo, evidencia, estado). Admin resuelve desde panel.

### Dashboard en TV (pantalla municipal en tiempo real)
Vista sin login con token de solo lectura. Auto-refresh cada 60s con htmx o JS.


Ícono PWA — cuando tengas el PNG listo, reemplazá los 3 archivos en static/icons/: icon-192.png, icon-512.png y apple-touch-icon.png. Con 192×192 y 512×512 es suficiente.