# Pendientes — Estacionamiento Proyecto

Última actualización: 2026-08-07 (sesión: medio_pago en todos los flujos de cobro — servicio, vistas, templates y tests)

---

## 🗺️ Contexto de deploy

- **Railway** → ambiente de prueba (inspectores + admin testeando). No es producción municipal real.
- **Digital Ocean** → deploy definitivo cuando el sistema vaya a municipios reales pagando.
- El código es el mismo; los cambios son de infraestructura y configuración.

---

## 🔴 Alta prioridad

### 🔴 PRODUCCIÓN: Sin backups automáticos del PostgreSQL de Railway Hobby
Railway Hobby no incluye backups automáticos. Opciones:
- **Railway Pro** ($20/mes): habilita backups diarios desde el dashboard.
- **Script `pg_dump`** vía scheduled task o GitHub Actions → sube a S3/Backblaze/GCS.
Verificar que el backup se puede restaurar al menos una vez antes del go-live real.
Ver: `CHECKLIST_PRODUCCION_2026-07-25.md` — item 🔴 #1.

### 🔐 SEGURIDAD: Idempotencia MP basada en texto libre
`acreditar_saldo_mp.py` usa `descripcion__contains="MP:{payment_id}"` para evitar double-credit.
Si el formato de descripción cambia, la idempotencia se rompe silenciosamente.
Fix: agregar campo `mp_payment_id = CharField(max_length=50, null=True, unique=True)` a `MovimientoCaja`.

---

## 🟡 Media prioridad

### ~~1. Vendedor: selección de medio_pago al cobrar~~ ✅ RESUELTO 2026-08-07
~~**Gap crítico post-rediseño financiero.**~~ Ver sección ✅ Resuelto.

### 2. LiquidacionComision: UI de factura pendiente
El modelo ya tiene `factura_presentada (BooleanField)` y `factura_archivo (FileField)` (migración 0046),
pero no hay formulario para usarlos. Pendiente:
- Panel vendedor: form para adjuntar factura (checkbox + file upload). La factura se refiere a la
  comisión que el tesorero ya depositó (`LiquidacionComision.estado = 'depositada'`).
- Panel tesorero: visualizar si el vendedor presentó factura, marcar como validada.
- Panel admin: puede ver el estado (lectura), no necesita acción.

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

Pendiente:
— **Rendiciones**: exportar cierre de caja a PDF para tesorería. `reportlab` ya instalado.

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
- ~~Tests de desglose de `generar_cierre_caja` con múltiples medios de pago~~ ✅ 2026-08-07

---

## 🟢 Baja prioridad / Futuras versiones

### acreditar_saldo_mp: medio_pago incorrecto
`acreditar_saldo_mp.py` crea `MovimientoCaja` sin especificar `medio_pago` (queda en default
`'efectivo'`). Debería ser `'mercadopago'`. No afecta el CierreCaja (los conductores no pasan
por `generar_cierre_caja`), pero distorsiona reportes globales de MovimientoCaja.
Fix: `MovimientoCaja.objects.create(..., medio_pago='mercadopago')` en `acreditar_saldo_mp.py`.

### Rendiciones: balances mensuales + rol Staff
- Resumen mensual de rendiciones a tesorería
- Nuevo rol `Staff`: solo reciben mails
- Implementar envío de mails desde Django (depende de email Railway)

### Panel admin "Sin rendir" — métrica revisada
La métrica fue removida del panel (código muerto). Si se quiere restaurar, el criterio correcto
es `CierreCaja.objects.filter(certificado=True, rendicion__isnull=True)` — cierres que el admin
ya certificó pero todavía no incluyó en ninguna Rendición. El campo `rendicion` FK en CierreCaja
ahora permite calcular esto de forma precisa.

### 🔐 Logging de eventos de seguridad
Agregar logueo en `require_role()` cuando devuelve 403, y en `login_view()` cuando falla.

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

### Inspector como cobrador
Agregar rol "inspector" al decorator de `registrar_estacionamiento_vendedor` y `cobrar_abono`.

### Mejoras OAuth y UI
- Pantalla de consentimiento Google: completar logo, descripción, dominio verificado.
- Modo alto contraste / uso en exterior con sol.
- Separar `settings_dev.py` / `settings_prod.py`.

### Limpiar inicio_admin.html
`templates/admin/inicio_admin.html` existe pero no se usa. Eliminar o redirigir.

---

## 💰 Mejoras para vender (Plan Premium)

### Detección automática de subcuadra por GPS
Inspector ubicado automáticamente. Requiere `Subcuadra.poligono` (JSON) + punto-en-polígono en JS.

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

---

## ✅ Resuelto

### feat: medio_pago en todos los flujos de cobro (2026-08-07) ✅
- `services/infracciones.py::cobrar_infraccion_efectivo()`: acepta param `medio_pago='efectivo'` (default).
  Normaliza valores inválidos a 'efectivo'. Constante `MEDIOS_VALIDOS_COBRO` exportada.
- `views_vendedor.py`: lee `medio_pago` del POST en cobrar_infraccion, cobrar_abono y consultar_deuda.
- `views_admin.py`: lee `medio_pago` del POST en admin_infracciones y lo pasa al service.
- Templates: partial `includes/medio_pago_selector.html` con button-group radio (5 opciones).
  Incluido en: `vendedores/cobrar_infraccion.html` (Paso 2), `admin/cobrar_abono.html`,
  `usuarios/consultar_deuda.html`, `admin/infracciones.html` (modal).
- Tests: 2 tests unitarios al service + 4 tests de integración de vista en `TestMedioPagoCobros`.

### feat: rediseño módulo financiero — rendición vinculada a CierreCaja (2026-08-06) ✅
- `MovimientoCaja.medio_pago`: expandido de 2 a 6 opciones (efectivo, transferencia, débito, crédito, QR, mercadopago).
- `CierreCaja`: nuevos campos `total_efectivo`, `total_transferencia`, `total_digital` calculados
  automáticamente en `generar_cierre_caja()` con una sola query de agregación condicional.
  Nuevo `rendicion FK → Rendicion (SET_NULL)`: permite auditar qué cierres están en cada rendición.
- `Rendicion`: eliminado `total_comisiones` (comisiones son responsabilidad de tesorería, no del admin).
  Nuevo `comprobante_archivo (FileField)`. Totales calculados automáticamente desde los cierres seleccionados.
- `LiquidacionComision`: nuevos `factura_presentada (BooleanField)` + `factura_archivo (FileField)`.
- `crear_rendicion` (view): rediseñada. Admin selecciona CierreCaja certificados con checkboxes,
  totales calculados por el sistema (no entrada manual), cada cierre queda FK a la rendición creada.
- Templates: `crear_rendicion.html` rediseñado con tabla de checkboxes + JS. Columna "Comisiones"
  eliminada de `rendiciones.html` y `panel_tesorero.html`.
- Migración 0046. 135 tests OK.

### fix: sin_rendir — código muerto limpiado (2026-08-06) ✅
- Eliminadas queries muertas de `panel_admin` (sin_rendir, abiertos, en_cierre_sin_certificar).
- Causa raíz del problema original: los reintegros de conductores crean `MovimientoCaja(tipo="ingreso")`
  para el conductor, que nunca se cierra con `generar_cierre_caja` (esa función es solo para
  inspectores/vendedores). Para restaurar la métrica correctamente, usar CierreCaja certificados sin rendicion.

### fix: webhook MP fail-open → fail-closed (2026-08-06) ✅
`_verificar_firma_mp()` retorna `False` cuando `MP_WEBHOOK_SECRET` no está seteada (antes `True`).
⚠️ Pendiente en Railway: agregar variable `MP_WEBHOOK_SECRET` desde MP Dashboard → Webhooks → secreto.

### fix: SECRET_KEY con fallback silencioso inseguro (2026-08-06) ✅
En producción (`DEBUG=False`) sin `SECRET_KEY`, Django falla al arrancar con `ImproperlyConfigured`.
En local (`DEBUG=True`) el fallback de desarrollo sigue funcionando. [`settings.py`]

### fix: HMAC en webhook de MercadoPago (2026-08-03) ✅
`_verificar_firma_mp()` en `views_mp.py` verifica header `x-signature` via HMAC-SHA256.
Firma inválida → se descarta silenciosamente con 200.

### fix: django-axes — rate limiting en login (2026-08-03) ✅
`django-axes==7.0.1`. Bloquea por IP después de 5 intentos fallidos, 1 hora de cooloff.
`requirements.txt`, `settings.py`, `templates/lockout.html`.

### feat: panel admin rediseño (2026-08-06) ✅
Eliminado grid-3 de stats incorrectas. Card "Estacionamientos activos" con tabla en tiempo real.
Columna "Estado" en infracciones recientes con colores. 130 tests OK.

### feat: cambiar contraseña de conductor desde admin (2026-08-06) ✅
Card "Cambiar contraseña" en `/admin-usuarios/<id>/`. Workaround para email aún no funcional.

### feat: Excel estadísticas inspectores (2026-08-06) ✅
`/admin-inspectores/estadisticas/excel/` — `.xlsx` con openpyxl, conserva filtros activos.

### feat: Superadmin + ModuloMunicipio (2026-07-30) ✅
- `Usuario.es_superadmin`, `ModuloMunicipio` (municipio, módulo, activo). Migración 0045.
- `require_modulo()` decorator para feature flags por municipio.
- `views_superadmin.py`: panel, CRUD municipios, asignar admins, toggle módulos.
- Importación Excel de estacionamientos históricos (openpyxl).
- 130 tests OK.

### fix: contraseñas débiles — validate_password (2026-08-06) ✅
`_error_password()` centralizada en `views_admin.py`. `len < 6` + validadores del framework.
Aplicada en `gestionar_inspectores`, `gestionar_vendedores`, `crear_conductor`, `crear_admin`.

### fix: anymail en INSTALLED_APPS (2026-08-06) ✅
`anymail` estaba en `EMAIL_BACKEND` pero no en `INSTALLED_APPS` → 500 al resetear contraseña.

### fix: es_superadmin en Django Admin fieldsets (2026-08-06) ✅
Agregado al fieldset "Roles" en `app_estacionamiento/admin.py`.

### fix: duracion_horas — IntegerField → DecimalField (2026-07-25) ✅
Migración 0044. Django truncaba silenciosamente `1.5h → 1h`. Fix: `DecimalField(max_digits=4, decimal_places=1)`.

### docs: checklist de producción (2026-07-25) ✅
`CHECKLIST_PRODUCCION_2026-07-25.md`. 3 bloqueantes, 4 recomendados, plan de go-live.

### fix: auditoría de rendimiento (2026-07-24) ✅
6 hallazgos implementados. Informe: `AUDITORIA_RENDIMIENTO_2026-07-24.md`.

### fix: auditoría UX/UI (2026-07-24) ✅
Top 3 fricciones + mejoras opcionales. Informe: `AUDITORIA_UX_2026-07-24.md`.

### fix: auditoría de seguridad — hardening (2026-07-24) ✅
SESSION_COOKIE_AGE, ALLOWED_HOSTS seguro, URL duplicada, validación uploads.
Informe: `AUDITORIA_SEGURIDAD_2026-07-24.md`.

### refactor: auditoría DB — constraints e integridad referencial (2026-07-24) ✅
Migración 0042. on_delete=PROTECT en historial contable, Subcuadra.unique_together con municipio,
campos muertos removidos. Informe: `AUDITORIA_DB_2026-07-24.md`.

### feat: foto en infracción — Cloudinary + watermark (2026-07-22) ✅
Cloudinary activo en Railway. Watermark con GPS, nombre inspector, subcuadra. Foto en ticket.

### feat: informes mensuales + PDF juzgado + impagas (2026-07-20) ✅
`DestinatarioInforme`, tab "📨 Informes" en rendiciones, PDF infracciones con reportlab.

### feat: estadísticas de inspectores (2026-07-20) ✅
`/admin-inspectores/estadisticas/` con filtros, comparativa y detalle por inspector.

### feat: inspector — subcuadra + exento parcial + watermark (2026-07-20) ✅
Selector de subcuadra en verificar.html. EXENTO_PARCIAL fuera de zona. Subcuadra en watermark.

### feat: mejoras UI admin (exenciones, rendiciones, historial) (2026-07-20) ✅
Crear vehículo desde exenciones. Rendiciones con 3 tabs. Historial vendedor. Alta conductor desde admin.

### feat: mejoras post-presentación municipal (2026-07-16) ✅
Nombre + apellido, title case, sanitización patentes, mínimo 1 hora, reintegro < 30 min.

### Otros ✅ (panel admin sidebar, Cloudinary, Sentry, Rol Tesorero, 106 tests base)
