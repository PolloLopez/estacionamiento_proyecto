# Pendiente — Estacionamiento Proyecto

Última actualización: 2026-08-03 (hallazgos de auditoría de seguridad registrados)

---

## 🗺️ Contexto de deploy

- **Railway** → ambiente de prueba (inspectores + admin testeando). No es producción municipal real.
- **Digital Ocean** → deploy definitivo cuando el sistema vaya a municipios reales pagando.
- El código es el mismo; los cambios son de infraestructura y configuración.

---

## 🔴 Alta prioridad

### 🔐 SEGURIDAD: URL del Django Admin ✅
Contraseña cambiada ✅. URL movida a `/sistema-interno/` ✅.

### 🔴 PRODUCCIÓN: Sin backups automáticos del PostgreSQL de Railway Hobby
Railway Hobby no incluye backups automáticos. Opciones:
- **Railway Pro** ($20/mes): habilita backups diarios desde el dashboard.
- **Script `pg_dump`** vía scheduled task o GitHub Actions → sube a S3/Backblaze/GCS.
Verificar que el backup se puede restaurar al menos una vez antes del go-live real.
Ver: `CHECKLIST_PRODUCCION_2026-07-25.md` — item 🔴 #1.

### 🔐 SEGURIDAD: Webhook de MercadoPago sin verificación de firma ✅
Implementado en `views_mp.py`: función `_verificar_firma_mp()` verifica el header `x-signature`
via HMAC-SHA256. Si `MP_WEBHOOK_SECRET` no está seteada, loguea warning y pasa (modo permisivo
para pruebas). Firma inválida → se descarta silenciosamente con 200 (MP no reintenta, no revela detección).
⚠️ Pendiente en Railway: agregar variable `MP_WEBHOOK_SECRET` desde MP Dashboard → Webhooks → secreto.
- Docs MP: https://www.mercadopago.com.ar/developers/es/docs/your-integrations/notifications/webhooks#editor_1

### 🔐 SEGURIDAD: Rate limiting en login ✅
Implementado con `django-axes==7.0.1`. Bloquea por IP después de 5 intentos fallidos, 1 hora de cooloff.
Archivos modificados: `requirements.txt`, `settings.py` (INSTALLED_APPS + MIDDLEWARE + AUTHENTICATION_BACKENDS + AXES_*), `templates/lockout.html`.
⚠️ Pendiente localmente: `pip install django-axes && python manage.py migrate`

### 🔐 SEGURIDAD: Idempotencia MP basada en texto libre
`acreditar_saldo_mp.py` usa `descripcion__contains="MP:{payment_id}"` para evitar double-credit.
Si el formato de descripción cambia, la idempotencia se rompe silenciosamente.
Fix: agregar campo `mp_payment_id = CharField(max_length=50, null=True, unique=True)` a `MovimientoCaja`.


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

### 3. Exportación de reportes a Excel/PDF (parcial)
Implementado:
— **Infracciones impagas → PDF juzgado**: `/admin-infracciones/pdf-juzgado/` (usa reportlab).
  Tabla con Acta#, Fecha, Patente, Inspector, Subcuadra, Monto, Días vencida.
  También se adjunta al email del informe mensual.

Pendiente:
— **Inspectores**: botón "Descargar Excel" en `/admin-inspectores/estadisticas/` con las métricas del período.
— **Rendiciones**: exportar cierre de caja a PDF para tesorería.
— Implementable con `openpyxl` (instalar) y `reportlab` (ya instalado).

### 4. 🔐 SEGURIDAD: Verificación de email al registrarse
`ACCOUNT_EMAIL_VERIFICATION = "none"` permite registrarse con cualquier email sin verificar.
Activar cuando email SMTP esté configurado en Railway:
```python
ACCOUNT_EMAIL_VERIFICATION = "mandatory"
```
Depende de: Email configurado en Railway (ver punto 2).

⚠️ **Actualización auditoría 2026-08-03**: el riesgo es mayor de lo que parece a simple vista —
combinado con `SOCIALACCOUNT_AUTO_SIGNUP = True`, permite un ataque de pre-registro: alguien se
registra con el correo de otra persona (sin verificarlo) y, cuando la víctima real más adelante
entra con "Iniciar sesión con Google" usando ese mismo correo, allauth puede vincular el login
social a la cuenta ya existente — dejándola bajo control de quien puso la contraseña original.
Mientras no se active la verificación mandatoria, evaluar bloquear el auto-connect en
`SocialAccountAdapter.save_user` cuando ya exista un `Usuario` con ese correo creado por
password. [`views_auth.py:110-139`, `forms.py` (`RegistroUsuarioForm`), `adapters.py`]

### 5. 🔐 SEGURIDAD: Contraseñas débiles — los validadores de Django nunca se ejecutan
`AUTH_PASSWORD_VALIDATORS` está bien configurado en `settings.py` para producción, pero ningún
flujo de creación de usuario lo invoca: todos llaman `create_user()`/`make_password()`
directamente sin pasar por `validate_password()`. Único chequeo manual existente:
`len(password) < 6` en `crear_conductor` — los demás (`crear_admin`, `gestionar_inspectores`,
`gestionar_vendedores`, autorregistro) no tienen ningún mínimo.
Fix sugerido: llamar `validate_password(password)` (con `try/except ValidationError`) en los
4 puntos de creación, o centralizarlo en una función de `services/`.
[`views_superadmin.py:150-165`, `views_admin.py:331-339,489-497,568-583`, `forms.py:26-28`]

### 6. 🔐 SEGURIDAD: Webhook de MercadoPago "fail-open" si falta `MP_WEBHOOK_SECRET`
Distinto del punto ya resuelto de verificación de firma: acá el riesgo es que, si la variable
de entorno no está seteada en producción, `_verificar_firma_mp()` devuelve `True` (omite la
verificación) en vez de rechazar. Riesgo acotado en la práctica (se re-consulta el pago contra
la API de MP y la acreditación es idempotente), pero conviene fallar cerrado como ya se hace
con `ALLOWED_HOSTS`. [`views_mp.py:242-247`]

### 7. 🔐 SEGURIDAD: `SECRET_KEY`/`DEBUG` con fallback silencioso inseguro
Mismo patrón de riesgo que se resolvió para `ALLOWED_HOSTS` (falla ruidoso si falta la
variable), pero acá no está aplicado: si se olvida `DEBUG=False` en un nuevo entorno, el
default es `"True"` (páginas de error con stack trace completo); si se olvida `SECRET_KEY`,
cae en un valor hardcodeado y público (`"dev-key-insegura-cambiar-en-produccion"`).
[`settings.py:12,16`]

### 8. Tests faltantes
- Flujo MP webhook (integración)
- `TestWatermarkGPS` pasando en Railway (verificar con Cloudinary activo)

---

## 🟢 Baja prioridad / Futuras versiones

### Rendiciones: balances mensuales + rol Staff
- Resumen mensual de rendiciones a tesorería
- Nuevo rol `Staff`: solo reciben mails
- Implementar envío de mails desde Django (depende de email Railway)

### 🔐 Logging de eventos de seguridad
Agregar logueo en `require_role()` cuando devuelve 403, y en `login_view()` cuando falla.
(Baja urgencia en etapa de pruebas — más importante en producción municipal.)

### 🔐 Límite máximo de monto en MercadoPago
Validar en `mp_iniciar_carga` que el monto no supere un tope (ej. $50.000).

### 🔐 Hallazgos menores — auditoría de seguridad 2026-08-03
- `registro_view`: no valida que el `municipio_id` recibido por POST tenga `activo=True`
  (el `<select>` del template sí filtra, pero se puede manipular el form). [`views_auth.py:122-127`]
- `importar_estacionamientos`: sin límite de tamaño en el archivo Excel antes de
  `openpyxl.load_workbook()` — riesgo bajo (solo superadmin), pero conviene poner un tope
  (ej. 10 MB). [`views_superadmin.py:308-323`]
- `mp_webhook`: la firma HMAC no valida que el `ts` del manifest sea reciente (ventana
  anti-replay). Mitigado en la práctica por la idempotencia de `acreditar_saldo_mp`, pero es
  defensa en profundidad. [`views_mp.py:226-288`]
- `django-axes`: bloqueo solo por IP (`AXES_LOCKOUT_PARAMETERS = ["ip_address"]`), decisión ya
  documentada y razonable. Como mejora opcional: evaluar un segundo umbral combinando IP+usuario
  para mitigar credential stuffing distribuido. [`settings.py:175`]

### 🔐 Verificación de email al registrarse
Incluida en el checklist de migración a DO. Requiere email SMTP funcionando primero.

### Flujo tesorería → vendedor: verificar UI completa
El modelo `LiquidacionComision` ya tiene el flujo modelado.
Verificar que la UI del vendedor sea clara para certificar que recibió su comisión.

### Responsive > 1050px
En pantallas grandes el layout del panel admin queda con mucho espacio vacío.

### PWA / App móvil sin Play Store
`manifest.json` + service worker básico (offline fallback).

### Migración a Digital Ocean (producción municipal real)
**Disparador**: cuando el sistema pase de pruebas a municipio real pagando.

Checklist para el deploy en DO:
- Gunicorn: `--workers $((2 * CPU + 1))` (ej: 3 workers con 1 vCPU)
- Remover pandas/numpy de requirements (solo se usan en análisis offline, pesan 80MB por worker)
- Configurar Nginx como proxy reverso (DO Droplet o App Platform)
- Verificar firma de webhook de MercadoPago (`x-signature`)
- Rate limiting en login (`django-ratelimit`)
- CSP headers (`django-csp`)
- Verificación de email al registrarse (`ACCOUNT_EMAIL_VERIFICATION = "optional"`)
- Cloudinary con signed URLs para fotos de infracciones
- Backups automáticos de PostgreSQL configurados y testeados

### Inspector como cobrador
Agregar rol "inspector" al decorator de `registrar_estacionamiento_vendedor` y `cobrar_abono`.

### Mejoras OAuth y UI
- Pantalla de consentimiento Google: completar logo, descripción, dominio verificado
- Modo alto contraste / uso en exterior con sol
- Separar `settings_dev.py` / `settings_prod.py`

### Limpiar inicio_admin.html
`templates/admin/inicio_admin.html` existe pero no se usa. Eliminar o redirigir.

---

## 💰 Mejoras para vender (Plan Premium)

Funcionalidades que no son necesarias para el funcionamiento base pero agregan valor
diferencial y se pueden cobrar como módulos adicionales o tier superior.

### Detección automática de subcuadra por GPS
El teléfono del inspector ubica automáticamente en qué subcuadra está patrullando,
sin que tenga que seleccionarla manualmente.
— Cada subcuadra necesita un polígono geográfico (lat/lon de los vértices) o un punto central + radio.
— Al abrir la pantalla de verificación, se llama a la Geolocation API y se compara contra los polígonos.
— Si la coincidencia es clara (1 zona), se auto-selecciona y se muestra en verde.
— Si hay ambigüedad (borde entre zonas), se muestran las opciones candidatas.
— Requiere: nuevo campo `Subcuadra.poligono` (JSON) + lógica de punto-en-polígono en JS o en backend.

### Toggle de estadísticas por municipio (desde Django Admin)
Nuevo campo `Municipio.estadisticas_inspectores_activo = BooleanField(default=True)`.
Permite al superadmin ocultar la vista de estadísticas para municipios que no pagaron el módulo.
— 1 migración, 1 chequeo en `estadisticas_inspectores`, registrar en `admin.py`.

### Reconocimiento de patente por cámara (OCR)
El inspector apunta la cámara del teléfono y el sistema lee la patente automáticamente,
sin necesidad de tipear. Reduce errores y acelera la verificación.
— Opciones: Google ML Kit (on-device, gratis), Tesseract.js (client-side), o API de OCR en backend.
— Integrar en `verificar.html`: botón "📷 Escanear" que abre la cámara y rellena el campo patente.

### Alertas de vencimiento al conductor (notificaciones push / WhatsApp)
El sistema avisa al conductor X minutos antes de que venza su estacionamiento.
— Push notifications vía service worker (PWA) si el conductor tiene la web abierta.
— WhatsApp via Twilio/360dialog como canal alternativo más efectivo.
— El conductor puede renovar directamente desde el link de la notificación.

### Mapa de calor de infracciones
Visualización geográfica de dónde se concentran las infracciones y verificaciones.
— Herramienta útil para que la municipalidad decida dónde reforzar la presencia de inspectores.
— Implementable con Leaflet.js + datos de lat/lon de las subcuadras.
— Requiere que las subcuadras tengan coordenadas (ver "Detección automática por GPS").

### Módulo de impugnaciones
El conductor puede impugnar una infracción desde la app, adjuntando evidencia (foto, descripción).
— Nuevo modelo `Impugnacion` (infraccion, conductor, motivo, evidencia, estado, resuelto_en).
— El admin recibe la impugnación y puede anular o confirmar la infracción.
— Notificación al conductor con la resolución.

### Exportación de reportes a Excel/PDF
_(movida a 🟡 Media prioridad — funcionalidad base, no premium)_

### Dashboard en TV (pantalla municipal en tiempo real)
Vista de solo lectura sin login, pensada para una pantalla grande en la municipalidad.
Muestra: infracciones del día, recaudación, inspectores activos, vehículos verificados.
— Token de acceso de solo lectura, sin autenticación de Google.
— Auto-refresh cada 60 segundos con htmx o JS.

---

## ✅ Resuelto

### fix: duracion_horas bug — IntegerField → DecimalField (2026-07-25) ✅
Migración 0044. `Estacionamiento.duracion_horas` era `IntegerField` pero el sistema genera
duraciones en múltiplos de 0.5h. Django truncaba silenciosamente `Decimal("1.5")` → 1,
haciendo que el estacionamiento expirara 30 min antes de lo pagado.
Fix: `DecimalField(max_digits=4, decimal_places=1)`. Actualizados `views_conductor.py`,
`views_inspector.py` y `services/horarios.py` para usar `float()` en `timedelta(hours=...)`.
Los datos existentes eran todos enteros (ya estaban truncados) — migración segura sin backfill.

### docs: checklist de producción (2026-07-25) ✅
Informe completo: `CHECKLIST_PRODUCCION_2026-07-25.md`.
3 bloqueantes: backups automáticos, HMAC MP webhook, rate limiting login.
4 recomendados: Sentry, UptimeRobot, email SMTP, limpieza datos prueba.
Plan de go-live con smoke test de 5 pasos y procedimiento de rollback.

### fix: auditoría de rendimiento — completa (2026-07-24) ✅
Informe completo: `AUDITORIA_RENDIMIENTO_2026-07-24.md`.
6 hallazgos, todos implementados:
1. `historial_estacionamientos`: Paginator (20/pág) + `select_related("vehiculo", "subcuadra")`
2. `gestionar_usuarios`: Paginator (50/pág) + orden por nombre
3. `cerrar_estacionamientos_vencidos_por_horario`: caché "ya cerrado hoy" hasta las 05:00 del día siguiente
4. `VerificacionInspector`: índice compuesto `(vehiculo_id, fecha DESC)` — migración 0043
5. `admin_infracciones`: Paginator (50/pág) reemplaza el slice `[:200]`
6. `MovimientoCaja.save()`: `values_list("cerrado", flat=True)` en vez de `get()`
Controles de paginación agregados en 3 templates: `historial_estacionamientos.html`, `gestionar_usuarios.html`, `infracciones.html`.

### fix: auditoría UX/UI — completa (2026-07-24) ✅
Informe completo: `AUDITORIA_UX_2026-07-24.md`.
Top 3 fricciones resueltas:
- `login.html`: campo correo pierde el valor al fallar login → `value="{{ request.POST.correo|default:'' }}"`. Labels con `for`/`id`.
- `base.html`: sin feedback de carga → listener global en `submit` que muestra "Enviando…" y bloquea doble submit.
- `estacionar_vehiculo.html`: aviso inline `#aviso-saldo-insuficiente` + botón bloqueado si `costo > SALDO_CONDUCTOR`.
Mejoras opcionales implementadas:
- `base.html`: mensajes hardcodeados → clases `.alert-success/warning/danger/info` (usan CSS variables del municipio).
- `vendedores/panel.html`: 4 tarjetas con `grid-3` → `grid-2` (layout 2x2 balanceado).
- `registro.html`: "Apellido" marcado como `(opcional)`.
- `views_inspector.py` + `panel_inspectores.html`: inspector ve sus cierres sin certificar en el panel.

### fix: auditoría de seguridad — hardening inmediato (2026-07-24) ✅
Informe completo: `AUDITORIA_SEGURIDAD_2026-07-24.md`.
Cambios aplicados:
- `settings.py`: `SESSION_COOKIE_AGE = 43200` (sesiones expiran a las 12hs, antes nunca expiraban).
- `settings.py`: `ALLOWED_HOSTS` fallback seguro — `["*"]` solo si `DEBUG=True`, en producción sin la variable falla en lugar de quedar abierto.
- `urls.py`: eliminada URL duplicada `ticket-pago-multa` (sección COMPROBANTES que Django ignoraba).
- `views_conductor.py`: `_validar_documento()` — valida tipo (JPG/PNG/WEBP/PDF) y tamaño máximo (10MB) antes de guardar archivos de verificación.
- `services/infracciones.py`: `getattr` defensivo en `inspector.first_name/last_name` (watermark no falla con objetos livianos de tests).
- `tests.py:685`: fix `__import__("django.utils.timezone")` roto → `from django.utils import timezone`.
- `settings.py`: `STORAGES["default"]` siempre presente (Django 5.x — faltaba cuando Cloudinary no está configurado).
Pendientes de seguridad restantes: firma MP webhook, rate limiting login, idempotencia MP, verificación email → ver 🔴 arriba.

### refactor: auditoría DB — constraints e integridad referencial (2026-07-24) ✅
Migración 0042. Cambios en `models.py`:
- `Subcuadra.unique_together`: ahora incluye `municipio` → fix multi-tenancy (dos municipios pueden tener la misma calle+altura).
- `on_delete=PROTECT` en: `Infraccion.inspector`, `Infraccion.vehiculo`, `MovimientoCaja.usuario`, `CierreCaja.usuario`, `Usuario.municipio` → borrar esos objetos ya no destruye silenciosamente el historial contable.
- `Infraccion.municipio`: `CASCADE → SET_NULL` (el municipio puede borrarse, la infracción queda sin municipio).
- Removidos campos muertos: `Municipio.apellido` (desde migración 0003) e `Infraccion.qr_code` (desde migración 0008).
- `MovimientoCaja.tipo`: agregado `choices=[("ingreso","Ingreso"),("egreso","Egreso")]`.
- `VerificacionInspector.resultado`: agregado `choices` + `default="verificado"`.
Informe completo: `AUDITORIA_DB_2026-07-24.md`.

### feat: foto en infracción — Cloudinary + watermark + ticket (2026-07-22) ✅
- Cloudinary activo en Railway (`CLOUDINARY_CLOUD_NAME`, `CLOUDINARY_API_KEY`, `CLOUDINARY_API_SECRET`).
- `STORAGES["default"]` con `MediaCloudinaryStorage` (Django 5.x — reemplaza `DEFAULT_FILE_STORAGE`).
- `MEDIA_URL = ""` con Cloudinary activo para evitar URL duplicada.
- Watermark siempre aplicado (antes solo si había GPS). GPS opcional → muestra "sin señal".
- Nombre del inspector en watermark (`first_name last_name` o `correo` como fallback).
- Foto visible en ticket de infracción (pantalla, no imprime). Inspector revisa y confirma print.
- Auto-print eliminado: el inspector hace clic en "Imprimir acta" él mismo.
- Fallback en `crear_infraccion()`: si Cloudinary falla, guarda sin foto (no bloquea el acta).

### feat: Cloudinary como media storage (2026-07-21) ✅
- `requirements.txt`: `cloudinary==1.41.0` + `django-cloudinary-storage==0.3.0`
- `settings.py`: configuración condicional — activo solo si `CLOUDINARY_CLOUD_NAME` está seteado.
  En local sigue usando filesystem. En Railway usa CDN de Cloudinary.
- `urls.py`: guard `if settings.MEDIA_ROOT:` para no servir archivos locales cuando Cloudinary está activo.
- Variables en Railway: `CLOUDINARY_CLOUD_NAME=braigulp`, `CLOUDINARY_API_KEY`, `CLOUDINARY_API_SECRET`.
- Verificación pendiente end-to-end (ver 🔴 arriba).

### refactor: quitar prefijo /usuarios/ + URL admin (2026-07-21) ✅
- Todas las URLs pasaron a la raíz: `/login/`, `/inspectores/`, `/admin-infracciones/`, etc.
- Admin Django movido a `/sistema-interno/` (URL no obvia).
- Callbacks de MercadoPago via `reverse()` + `build_absolute_uri()` (no más hardcodeo).
- `LOGIN_URL`, middleware y `export_pdf_url` actualizados en consecuencia.

### feat: informes mensuales en rendiciones + PDF juzgado + impagas (2026-07-20) ✅
- **DestinatarioInforme**: nuevo modelo (municipio, nombre, correo, activo). Migración 0041.
- **rendiciones.html**: 4º tab "📨 Informes". Gestión de destinatarios (agregar/toggle/quitar).
  Formulario de envío: período, secciones seleccionables (rendiciones / vendedores / infracciones),
  destinatarios activos pre-marcados.
- **admin_rendiciones** (view): maneja POST actions `agregar_destinatario`, `quitar_destinatario`,
  `toggle_destinatario`, `enviar_informe`. Email con `EmailMessage` + adjunto PDF impagas.
- **PDF juzgado de faltas**: helper `_generar_pdf_infracciones_juzgado()` (reportlab).
  Vista `/admin-infracciones/pdf-juzgado/` para descarga directa. Filtros: desde/hasta.
- **admin_infracciones**: badge contador de impagas + botón "📄 PDF juzgado" con filtros actuales.

### feat: estadísticas de inspectores (2026-07-20) ✅
- Nueva vista `/admin-inspectores/estadisticas/` solo para admin.
- Filtros: inspector (opcional) + rango de fechas libre (default: mes actual).
- Modo comparativa: tabla con verificaciones / infracciones / tasa / anuladas por inspector.
- Modo detalle (inspector seleccionado): distribución horaria con barra, subcuadras patrulladas, actividad diaria.
- Botón "📊 Stats" por inspector en `gestionar_inspectores` + link general en el header.
- TODO: `Municipio.estadisticas_activo` para ocultar por municipio desde Django Admin (mejora paga).

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
