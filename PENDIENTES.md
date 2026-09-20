# Pendientes — Estacionamiento Proyecto

Última actualización: 2026-09-19 (sesión 10 — continuación 3)

---

## 🗺️ Contexto de deploy

- **Railway** → ambiente de prueba activo. No es producción municipal real.
- **Digital Ocean App Platform** → deploy definitivo antes de entregar a un municipio real.
- El código es el mismo; los cambios son de infraestructura y configuración.

### Orden recomendado antes del go-live municipal

```
1. Corregir bug rendiciones (🔴 abajo)
2. Test end-to-end comisiones (🟡 abajo)  
3. Migrar a Digital Ocean App Platform (🔴 abajo)
4. Smoke test en DO con URL temporal (sin tocar DNS)
5. Corte al municipio real → switch de dominio
```

No migrar a DO con bugs conocidos: si algo falla en producción, no sabrás si es el bug o la migración.

---

## 🔴 Alta prioridad

### Bug: admin puede certificar su propio cierre en `/admin-rendiciones/`

El flujo correcto es:
1. Vendedores rinden sus cierres → **admin los certifica** ✓
2. Admin consolida esos cierres + su propia caja → hace la rendición a tesorería
3. **Tesorero certifica la rendición del admin** ✓

El problema: la validación bloquea el paso 3. Leer `views_admin.py` y `templates/admin/rendiciones.html` → ajustar para que:
- Admin **no** pueda certificar su propio cierre de caja.
- Tesorero **sí** pueda certificar el cierre/rendición del admin.

---

### Migración a Digital Ocean App Platform

**Contexto:** Railway es el ambiente de prueba actual. DO App Platform es el destino de producción municipal. Hacer en paralelo — no apagar Railway hasta confirmar que DO funciona.

#### Paso 1 — Preparar DO (sin tocar Railway)

1. Crear cuenta DO → **App Platform** → "Create App" → conectar el repo de GitHub (rama `main`).
2. DO detecta Python automáticamente. Configurar:
   - **Run command:** `gunicorn estacionamiento.wsgi --bind 0.0.0.0:$PORT`
   - **Build command:** `pip install -r requirements.txt && python manage.py collectstatic --noinput`
   - **Post-deploy job:** `python manage.py migrate`
3. Agregar base de datos: en el wizard de App Platform → "Add Resource" → **PostgreSQL** (el managed de DO, ~$7/mes dev o $15/mes básico). DO inyecta `DATABASE_URL` automáticamente.

#### Paso 2 — Variables de entorno en DO

En App Platform → Settings → Environment Variables. Copiar de Railway cambiando solo lo que aplique:

| Variable | ¿Cambia? | Acción |
|---|---|---|
| `SECRET_KEY` | No | Copiar igual |
| `DATABASE_URL` | Sí | DO la inyecta automático — no setear manualmente |
| `DEBUG` | No | Debe ser `False` |
| `ALLOWED_HOSTS` | Sí | Agregar URL temporal de DO (`app-nombre-xyz.ondigitalocean.app`) + dominio final del municipio |
| `CLOUDINARY_*` | No | Copiar igual |
| `MP_ACCESS_TOKEN`, `MP_PUBLIC_KEY` | No | Copiar igual |
| `MP_WEBHOOK_SECRET` | No | Copiar igual (el valor lo define MP, no el hosting) |
| `ANYMAIL_*` (Brevo/Resend) | No | Copiar igual |
| `SENTRY_DSN` | No | Copiar igual (o crear nuevo proyecto en Sentry para separar prod de prueba) |

#### Paso 3 — Migrar la base de datos

```bash
# En Railway (o desde local con la URL de Railway):
pg_dump $RAILWAY_DATABASE_URL > backup_railway_$(date +%Y%m%d).sql

# En DO (con la URL del managed PostgreSQL de DO):
psql $DO_DATABASE_URL < backup_railway_YYYYMMDD.sql

# Verificar migraciones aplicadas:
python manage.py migrate --check
```

Si los datos de Railway son solo de prueba y el municipio va a arrancar desde cero, se puede saltear la migración de datos (solo correr `python manage.py migrate` sobre la BD vacía de DO).

#### Paso 4 — Cron jobs en DO App Platform

DO App Platform tiene "Jobs" que corren en schedule. Crear:
- **Nombre:** `revocar-exenciones`
- **Command:** `python manage.py revocar_exenciones_vencidas`
- **Schedule:** `0 3 * * *` (3am todos los días)

Esto reemplaza el pendiente de Railway del cron de SIA.

#### Paso 5 — Smoke test en DO (con URL temporal, sin cambiar DNS)

Con la app corriendo en `https://app-nombre-xyz.ondigitalocean.app`:
- [ ] Login de cada rol (conductor, inspector, vendedor, admin, tesorero, superadmin)
- [ ] Registrar estacionamiento completo (incluyendo débito de saldo)
- [ ] Registrar infracción y cobrarla
- [ ] Hacer rendición de vendedor → admin la certifica → tesorero deposita
- [ ] Verificar que los emails (Brevo/Resend) salen correctamente
- [ ] Verificar que Cloudinary sirve imágenes si hay logos de municipio cargados

#### Paso 6 — Corte: switch de dominio

1. En DO App Platform → Settings → Domains → agregar el dominio del municipio. DO gestiona SSL automáticamente (Let's Encrypt).
2. En el registrador de dominio → apuntar DNS al valor que da DO (CNAME o A record). Propagación: 5–30 min.
3. **Actualizar el webhook de MercadoPago** en el panel de MP: Credenciales → Webhooks → cambiar URL a `https://dominio-municipio.com/mp/webhook/`. Este es el paso más fácil de olvidar.
4. Actualizar UptimeRobot con la nueva URL.
5. En Railway: dejar activo 3–5 días más como fallback. Después, apagar.

---

## 🟡 Media prioridad

- **Comisiones de vendedores — test end-to-end** (hacer ANTES de la migración a DO)
  Prueba manual completa: rendición del vendedor → tesorero deposita → vendedor certifica. Confirmar que los montos coinciden con lo registrado en `LiquidacionComision`.
- **Inspector — impresora BLE: no volver a pedir vinculación al imprimir**
  Workaround actual: reconectar por nombre. Evaluar si Chrome corrigió el bug de `getDevices()` o documentar como límite del navegador.
  Archivo: `static/.../js/impresora_bluetooth.js` (función `reconectarImpresora`).

---

## 🟢 Baja prioridad / Futuras versiones

- **Migración a Digital Ocean** — disparador: cuando el sistema pase a municipio real pagando. Ver `CHECKLIST_PRODUCCION_2026-09-01.md`.
- **OCR de patentes** — Google ML Kit o Tesseract.js. Botón "📷 Escanear" en `verificar.html`.
- **Alertas de vencimiento al conductor** — push / WhatsApp.
- **Tutorial GIFs en landing pública** — el tutorial por rol ya existe dentro del sistema (collapsible `<details>` en cada panel). Pendiente: versión con GIF para la landing pública.
- **Auditoría de reseteos de contraseña** — registrar quién reseteó la contraseña de quién. Usar `LogEntry` de Django Admin o modelo propio.
- **Jerarquía de botones en formularios** — estandarizar: botón principal con `--color-primary`, botón secundario con `.btn-outline`. Hay inconsistencias entre templates.
- **Refactor estilos inline** — muchos templates tienen `style=""` repetido. Crear clases `.card-form`, `.section-admin` en `global.css`.

---

## ℹ️ No son bugs del sistema

- **Error `contentscript.js: [object Object] Resetting the streams.`** en `/tesorero/rendicion`:
  Este error viene de una extensión del navegador (Grammarly, Loom, u otra extensión de Chrome que inyecta scripts). No es un error del sistema Django. Solución: desactivar extensiones en esa tab o usar modo incógnito sin extensiones.

---

## ✅ Resuelto

### Sesión 2026-09-19 (sesión 10 cont. 2) — Descuento para conductores verificados

| Ítem | Detalle |
|---|---|
| Descuento para conductores verificados | `Municipio.descuento_verificados_pct` (DecimalField, null=sin módulo) + `Municipio.descuento_solo_vecinos` (BooleanField). Migración 0082. Nuevo service `services/descuentos_verificados.py` con `calcular_descuento_conductor()` + `aplicar_descuento_conductor()`. Aplicado en `use_cases/estacionar_vehiculo.py` antes del débito de saldo. En el GET de estacionar: tarifa efectiva ya incluye el descuento → las opciones de duración muestran el precio real. Badge verde "X% de descuento" visible en el form si aplica. Config superadmin en `editar_municipio.html`. |

### Sesión 2026-09-19 (sesión 10 cont.) — GPS en Infraccion + preferencias de notificaciones + SIA

| Ítem | Detalle |
|---|---|
| Geolocalización inspector guardada en BD | `Infraccion.gps_lat/gps_lon/gps_acc` (migración 0080). `crear_infraccion()` los persiste. Panel admin de infracciones: modal muestra "📍 Ver en mapa" (OpenStreetMap) cuando hay coordenadas. |
| Preferencias de notificaciones del conductor | `Notificacion.tipo` CharField (migración 0081). `Usuario.notif_verificacion/exencion/sugerencia` BooleanFields. Nuevo service `services/notificaciones.py` con `enviar_notificacion()` que respeta las preferencias. Vistas admin y superadmin migradas al helper. View `guardar_preferencias_notificaciones`. UI colapsable en footer del panel conductor. |
| SIA revalidación 6 meses | Auto-fecha `vigencia_exencion = hoy + 180 días` al aprobar exención discapacitado (admin panel). Management command `revocar_exenciones_vencidas` con `--dry-run`. Alertas en `exenciones.html`: rojo (ya vencidas), amarillo (próximas 30 días). Pendiente: activar como cron job en Railway. |

### Sesión 2026-09-19 (sesión 10) — admin_puede_editar_plantillas + BLE segunda copia + landing/testing

| Ítem | Detalle |
|---|---|
| Bug #1 — Admin puede editar plantillas de comprobantes | `Municipio.admin_puede_editar_plantillas` BooleanField (migración 0079). Toggle en `editar_municipio.html`. Guardado en `views_superadmin.py`. Nueva view `gestionar_plantillas_admin` en `views_admin.py` (chequea el flag, reutiliza template de superadmin con `modo_admin=True`). URL `admin-plantillas/` en `urls.py`. Sidebar en panel_admin condicional. Link "← Panel admin" en template de plantillas. |
| BLE segunda copia — distinción de fallo | `ticket_infraccion.html`: variable `copia1Enviada` rastreada. Reconexión preventiva antes de copia 2 si `!gatt.connected`. En catch: si `copia1Enviada=true` → mensaje "✅ Copia 1 enviada. ❌ Copia 2 no se pudo enviar" + botón "🔄 Reintentar copia 2" que solo envía la 2da. Si `copia1Enviada=false` → error total como antes. |
| Guía de testing (digital + imprimible) | `GUIA_TESTING_ROLES.md` y `TESTING_IMPRIMIR.html` creados con coverage de los 6 roles + casos borde. |
| Landing actualizada | Zona libre + mapa interactivo de subcuadras cards. Contador de modelos: 18→25+. |
| Tutorial "Cómo usar la app" movido al footer | Conductor panel: bloque `<details>` movido de arriba al pie (colapsable). |
| Conflicto merge subcuadras.html resuelto | `crearIcono()` + iconoPagado/iconoLibre/iconoNaranja preservados. Deploy Railway OK (migración 0078). |

### Sesión 2026-09-17 (sesión 9) — Dos 500 de Railway + archivos de audio

| Ítem | Detalle |
|---|---|
| Fix `/admin/impugnaciones/` Error 500 | `templates/admin/impugnaciones.html` línea 13: `{% for key, label in "..."\|make_list %}` era código muerto (sin cuerpo, `{% endfor %}` inmediato). `make_list` convierte el string en caracteres individuales → `ValueError: Need 2 values to unpack in for loop; got 1`. Fix: eliminar esa línea. Los botones de filtro ya estaban hardcodeados en las líneas siguientes. |
| Fix `/pagar/subcuadra-cercana/` Error 500 | `views_pago_publico.py subcuadra_cercana_publica`: `s.lat` y `s.lon` son `Decimal` (campo Django) pero `lat` y `lon` son `float` (del `request.GET`). Python lanza `TypeError` al mezclarlos en aritmética. Fix: `float(s.lat)` y `float(s.lon)` en el `min()`. |
| Archivos de audio 404 | Creados `app_estacionamiento/static/sounds/ok.mp3`, `warning.mp3`, `error.mp3` con frames MP3 silenciosos válidos (MPEG1 Layer3, 32kbps, 44100Hz). Usados en `templates/inspectores/verificar.html` para feedback auditivo del scanner. |

**Pendiente sin código fix**: El error `mp_webhook: x-signature mal formado` en los logs de Railway es un problema de configuración: verificar que la variable de entorno `MP_WEBHOOK_SECRET` en Railway tenga el valor correcto del panel de MercadoPago (Credenciales → Producción → Clave secreta webhook). No es un bug de código.

### Sesión 2026-09-16 (sesión 8) — Tests post-deploy, correcciones horario/abono/tesorero

| Ítem | Detalle |
|---|---|
| Fix horario estacionamiento vendedor (crítico) | `views_vendedor.py`: `puede_estacionar_ahora()` llamado sin `bloquear_sin_horario=True`. Días sin horario (ej: domingo) devolvían `(True, None)` → vendedor podía registrar. Fix: `bloquear_sin_horario=True` en `registrar_estacionamiento_manual` y `registrar_estacionamiento_vendedor`. |
| Fix: patente-input habilitado fuera de horario | `registrar_estacionamiento.html`: aviso de fuera de horario ahora aparece ANTES del input de patente. Input deshabilitado (`disabled` + `opacity:0.45`) cuando no hay opciones de duración. |
| Fix abono — selector tipo auto/moto | `cobrar_abono.html`: radio auto/moto en el form de búsqueda. `views_vendedor.py`: captura `tipo_vehiculo` del POST, lo aplica al vehículo al crearlo o si el tipo difiere del registrado. |
| Fix: admin_rendiciones 403 para tesorero | `views_admin.py`: `@require_role("admin")` → `@require_role("admin", "tesorero")`. El tesorero ahora puede acceder a `/admin-rendiciones/?seccion=comisiones` para ver y gestionar comisiones. |
| Fix: tesorero card "Comisiones" es clickable | `panel_tesorero.html`: card "Comisiones a depositar" como `<a>` apuntando a `admin_rendiciones?seccion=comisiones`. |
| Fix: modal cierre al imprimir infracción | `admin/infracciones.html`: `window.cerrarModal = cerrarModal` + `onclick="cerrarModal()"` en link del comprobante. |
| Fix: certificar comisión — variable liq→liquidacion | `certificar_comision.html`: todas las referencias `liq.` → `liquidacion.`. |
| Fix: botón Depositar en tab comisiones admin | `admin/rendiciones.html`: columna de acción con `<a>` a `depositar_comision` para liquidaciones pendientes. |
| Fix: comprobante de depósito (número + archivo) | `models.py`: `numero_comprobante` + `comprobante_archivo` en `LiquidacionComision`. Migración `0075`. Template y view actualizados. |
| Fix: vendedor — comisiones_pendientes | `views_vendedor.py panel_vendedor`: cambiado de `MovimientoCaja` (suma histórica confusa) a `LiquidacionComision.filter(estado__in=["pendiente","depositada"])`. |
| Fix: superadmin toggle — inspector ve infracciones | `models.py`: `Municipio.inspector_ve_sus_infracciones` BooleanField. Migración `0076`. `views_inspector.py`: resumen_infracciones filtra según el toggle. `views_superadmin.py`: guarda el campo desde el POST. Template y editar_municipio actualizados. |

### Sesión 2026-09-13 (sesión 7) — Crashes 500, depositar comisiones, horario abonos

| Ítem | Detalle |
|---|---|
| Fix raíz `medio_pago_selector.html` (Error 500 múltiple) | Django 5.x/Python 3.12 no atrapa `ValueError` de `int('medio_pago_inicial')` al resolver variables de template. Reescrito con `{% if %}` en lugar de `\|default:variable`. Creado `_medio_pago_radios.html` como fragmento compartido. Afectaba `/vendedores/abono/`, `/admin-infracciones/?detalle=N` y cualquier template que incluya el selector sin pasar `medio_pago_inicial`. |
| Fix `depositar_comision.html` (Error 500) | Template usaba `liq` en todos lados; la vista pasaba `liquidacion`. Renombrado. También: `name="notas"` → `name="notas_tesorero"` para que las notas no se pierdan silenciosamente en el POST. |
| Fix `depositar_comision` view: admin también puede depositar | Cambiado `@require_role("tesorero")` → `@require_role("tesorero", "admin")`. Redirect y `volver_url` dinámicos según rol. |
| Fix `caja_inspector`: modal-cierre sin período | La vista no pasaba `periodos` al contexto. Agregado `"periodos": CierreCaja.PERIODOS`. |
| Abonos sin restricción horaria | Se intentó agregar chequeo de horario a `cobrar_abono` (incorrecto). Revertido: los abonos se pueden cobrar en cualquier momento. Solo el estacionamiento por hora tiene restricción de franja horaria. |

### Sesión 2026-09-10 (tarde) — Modal, 500, columnas, vendedores

| Ítem | Detalle |
|---|---|
| panel_admin.html: reordenar infracciones_recientes | Nuevo orden: Patente, Monto, Estado, Fecha, Inspector. |
| infracciones.html: modal no cierra tras anulación | `views_admin.py`: redirect post-anulación ahora va a `reverse("admin_infracciones")` (sin `?detalle=ID`), así el modal no reabre. |
| Error 500: no hereda colores del municipio | Custom `handler500 = server_error` en `views.py` + `urls.py`. `500.html` ahora extiende `base.html` → tiene acceso a `--color-primary` del municipio. |
| Vendedor: btn-cobrar blur cuando horario en breve | `registrar_estacionamiento.html`: botón tiene `opacity:0.35;cursor:not-allowed` cuando `not opciones_duracion`. |
| Vendedor: botón "Cobrar abono" faltante en panel | `panel.html`: agregado con guard `{% if puede_vender_abono %}`. Abonos disponibles fuera de horario (la vista no valida horario). |
| Vendedor: permiso `puede_cobrar_infraccion` | `models.py`: nuevo campo `BooleanField(default=True)`. Migración `0073`. `editar_vendedor.html`: checkbox. `views_admin.py`: guarda el campo. `views_vendedor.py`: check en `cobrar_infraccion_vendedor`. `panel.html`: botón infracciones visible solo si `puede_cobrar_infraccion`. |

### Sesión 2026-09-10 — Bugs UI, navbar, tesorero/liquidaciones, medio_pago_selector

| Ítem | Detalle |
|---|---|
| Bug #6 navbar color claro → fondo negro en dark mode | `global.css`: regla `[data-theme="dark"] .nav-items { background: var(--color-surface) }` tenía mayor especificidad que el override de desktop. Fix: override dentro de `@media (min-width: 1050px)` con misma especificidad + orden posterior → `background: transparent`. |
| Navbar texto adaptativo según luminancia | `global.css`: variables `--color-nav-text`, `--color-nav-text-hover`, `--color-nav-hover-bg`. Script en `base.html`: calcula luminancia relativa del color primario (WCAG 2.x) y, si L > 0.35 (primario claro), setea texto oscuro. Sin flash porque el script corre en `<head>` antes del paint. |
| Bug #7 responsive /registro/ y /cambiar-password/ | `global.css`: `.auth-panel` sin `max-width: 100%` en mobile. Templates: `form-row` → `form-group` para layout columna. |
| Bug #8 crash tesorero /tesorero/rendicion/4/ | `views_tesorero.py`: `.order_by("vendedor__apellido")` → `.order_by("vendedor__last_name")` (`apellido` es `@property`, no columna DB). |
| Conductor nuevo puede estacionar sin verificación | `views_conductor.py`: mensaje warning al redirigir a MP. `inicio_usuarios.html`: banner verificación → texto sutil opcional. `mis_infracciones`: elimina redirect a verificación. |
| Nombres usuarios en mayúsculas | `views_admin.py`: `.title()` en `editar_inspector` y `editar_vendedor`. |
| Tesorero: notas + solicitar factura en liquidaciones | `views_tesorero.py`: acciones `actualizar_notas` y `solicitar_factura`. Template: formulario de notas + botón "Solicitar factura" cuando no hay factura subida. |
| Superadmin: solicitar comprobante al tesorero | `views_superadmin.py`: acción `solicitar_comprobante`. Template superadmin: botón cuando no hay comprobante. |
| Fix `medio_pago_selector.html` | Comentario reescrito. Preserva selección en redisplay de formulario con `request.POST.medio_pago` + soporte `medio_pago_inicial`. |

### Sesión 2026-09-06 (tarde 5) — Rendiciones: 3 mejoras

| Ítem | Detalle |
|---|---|
| Notas obligatorias al observar rendición | `views_tesorero.py`: backend rechaza si `accion=observar` y `notas_tesorero` vacío. JS en `panel_tesorero.html`: botón "Observar" no hace submit si el campo está vacío (borde rojo + focus). |
| Detalle de rendición | Nueva vista `detalle_rendicion(rendicion_id)` con `@require_role("tesorero", "admin")`. Muestra encabezado, totales, cierres incluidos y liquidaciones de comisión. Botón "Ver detalle" en historial del tesorero y en tabla de rendiciones del admin. Template `tesorero/detalle_rendicion.html`. URL `/tesorero/rendicion/<id>/`. |
| Comisiones de vendedores vacías (bug) | `crear_rendicion()` en `views_admin.py` creaba la `Rendicion` pero nunca generaba `LiquidacionComision`. Fix: al crear la rendición, agrupa `CierreCaja.ganancia_usuario` por vendedor y crea una liquidación por cada vendedor con comisión > 0. |

### Sesión 2026-09-06 (tarde 4) — Auto-impresión, sugerencias por rol, bug horario inspector, alias impresora

| Ítem | Detalle |
|---|---|
| Bug: inspector actúa sin horario configurado | `services/horarios.py`: `puede_estacionar_ahora()` ganó parámetro `bloquear_sin_horario`. Cuando es `True` y no hay horario para hoy (ej: domingo), devuelve `False` sin cachear. Usado en `verificar_vehiculo` y `registrar_infraccion`. |
| Auto-impresión al cargar ticket | `ticket_infraccion.html`: `imprimirActa()` se llama en `DOMContentLoaded`. Vista previa del acta oculta. Botón "Reintentar" solo aparece si hay error. |
| Sugerencias filtradas por rol | `views_conductor.py`: `AREAS_POR_ROL` filtra las áreas del select por rol. Conductor ve solo "conductor"+"general"; inspector solo "inspector"+"general", etc. |
| Alias impresora más visible | `panel_inspectores.html`: al vincular impresora, el `<details>` de config se abre solo. Nuevo placeholder "Ej: Mi impresora". |

### Sesión 2026-09-06 (tarde 3) — Logo en registro + pausa configurable entre copias

| Ítem | Detalle |
|---|---|
| Logo municipio en registro | `registro.html`: logo/nombre debajo del ícono. 1 municipio → fijo. Varios → JS actualiza al seleccionar. |
| Pausa configurable entre copias | `Municipio.segundos_pausa_doble_copia` (migración 0071). 0=el inspector confirma. >0=pausa automática. Config en `editar_municipio.html`. JS en `ticket_infraccion.html`. |

### Sesión 2026-09-06 (tarde 2) — Banner impresora BLE

| Ítem | Detalle |
|---|---|
| Banner visible sin impresora | `panel_inspectores.html`: banner con botón "Vincular impresora" en lugar del `<span>` oculto. Se oculta al detectar impresora. |

### Sesión 2026-09-06 (tarde 1) — Tablas, UptimeRobot, alerta cambios sin guardar, limpieza Railway

| Ítem | Detalle |
|---|---|
| Alerta JS "cambios sin guardar" | `editar_municipio.html`: detecta cambios en cada sección, resalta el botón Guardar con outline naranja. |
| Tablas desktop ≥ 1050px | `global.css`: `.card` con `overflow-x: auto` + `table { width:100% }`. |
| UptimeRobot | Endpoint `/health/` verificado. Config: uptimerobot.com → HTTP(s) → `https://estacionamiento.up.railway.app/health/` → 5 min. |
| Limpieza datos prueba Railway | UI en superadmin → editar_municipio → Zona de peligro → escribir `CONFIRMAR+NOMBRE` → botón. |

### Sesión 2026-09-06 (mañana) — Mejoras UX/UI

| Ítem | Detalle |
|---|---|
| Validación de email backend al crear tesorero | `views_admin.py`: `_correo_invalido()` + `validate_email` |
| Toggle 👁 para inputs de contraseña | `gestionar_staff.html`, `editar_staff.html`; script en `base.html` |
| Toasts `position:fixed` | `global.css` (clases `.toast*`), `base.html` (script + contenedor) |
| Fix: comentario Django multilinea visible en producción | `base.html`: `{# ... #}` de Django solo funciona en 1 línea. Comentario multilinea se eliminó. |

### Sesión 2026-09-06 (backlog) — SugerenciaMejora, SolicitudEliminacionCuenta, staff

| Ítem | Detalle |
|---|---|
| Reseteo de contraseña para admins | `views_admin.py`: `editar_staff` + `gestionar_staff` |
| Sectorizar `editar_municipio` | `views_superadmin.py` (4 ramas POST), `editar_municipio.html` (4 forms) |
| Admin puede gestionar tesoreros | `views_admin.py`: `gestionar_staff`, `editar_staff` |
| Responsive ≥ 1050px | `global.css`: `@media (min-width: 1050px)` |
| `SugerenciaMejora` | modelo, migración 0070, `views_conductor` + `views_superadmin`, 5 templates |
| `SolicitudEliminacionCuenta` | modelo, migración 0070, `views_conductor`, 1 template |

### Sesión 2026-09-04 — Bugs pre-demo

| Ítem | Detalle |
|---|---|
| Bug conductor: fuera de horario en GET | `views_conductor.py`: `puede_estacionar_ahora()` evaluado en GET. Botón deshabilitado con mensaje. |
| Bug dark mode: btn-outline y tarjeta-vehiculo | `global.css`: overrides dark mode para `.btn-outline` y `.tarjeta-vehiculo.seleccionada`. |
| Bug horario conductor ≠ inspector | `services/horarios.py`: todas las funciones usan `.order_by("-id").first()` para consistencia. |

### Sesiones 2026-08-13 al 2026-09-03 — Base del sistema

| Bloque | Resumen |
|---|---|
| Templates conductor faltantes | `crear_impugnacion.html`, `transferir_saldo.html`, `transferencias_saldo.html` |
| Token TV | `editar_municipio.html`: sección "Dashboard TV" con URL y botón regenerar. |
| Badge impugnaciones en admin | `views_admin.py`: count + badge en sidebar. |
| Vendedores — permiso individual para abonos | `models.py`, `views_admin.py` |
| Perfil extendido conductor/vendedor | migraciones 0064 (`domicilio`, `ubicacion_lat/lon`) |
| Admin panel responsive | `panel_admin.html` con desplegables |
| Ícono PWA dinámico | `views_conductor.py`, `manifest.json` |
| `ForzarCambioPasswordMiddleware` | `middleware.py` + `settings.py` |
| `dashboard_admin` con filtro de fechas | `views_admin.py`, `/admin-dashboard/` |
| `Infraccion.subcuadra → SET_NULL` | migración 0061 |
| `VerificacionInspector FK → SET_NULL` | migración 0062 |
| Descuentos voluntarios de infracciones | migración 0063, `services/infracciones.py` |
| Cierre de caja por período | migración 0064, `caja_vendedores`, `forzar_cierre_vendedor` |
| GPS subcuadra | endpoint `subcuadra_cercana`, JS en `estacionar_vehiculo.html` |
| Tesorero certifica cierres de admin | `views_admin.py`, `panel_tesorero.html` |
| Panel auditoría superadmin | `views_superadmin.py auditoria_superadmin` |
| Reportes de subcuadras | `views_admin.py reportes_subcuadras` |
| Módulo reintegro residentes | migración 0065, `services/reintegro.py` |
| Toggle estadísticas inspectores | `Municipio.estadisticas_inspectores_activo`, migración 0066 |
| Inspector cobrador (módulo premium) | `ModuloMunicipio cobrador_inspector` |
| Dashboard TV | `Municipio.token_tv`, migración 0066, vista pública |
| Mapa de calor de infracciones | Leaflet.js, círculos por subcuadra |
| Módulo de impugnaciones | modelo `Impugnacion`, migración 0067 |
| Transferencia de saldo | modelo `TransferenciaSaldo`, migración 0067 |
| GitHub Pages landing | `landing_github_pages.html` |
| Auditorías (seguridad, rendimiento, BD) | informes `AUDITORIA_*_2026-09-01.md` |
| Checklist de producción | `CHECKLIST_PRODUCCION_2026-09-01.md` |
| Impresora BLE base | persistencia `localStorage`, doble copia, QR nativo ESC/POS |
| Rendiciones base | PDF, tesorero valida/observa, `LiquidacionComision` |
| Dark mode + colores municipio | `global.css`, `Municipio.color_acento` (migración 0055) |
| Responsive completo | grid admin colapsable |
| `auditoria_staff` | vista unificada admin |
| OAuth bloqueo account takeover | `adapters.py` |
| SIA ANDIS | `services/sia_verificacion.py`, campos en `Infraccion` (migración 0054) |
| Bloqueo inspector fuera de horario | `views_inspector.py`, `verificar.html` |
| MercadoPago + backups + email + axes | sesiones 2026-08-18/20 |
| SIA parser v2 + titular + sidebar agrupado | sesión 2026-08-24 |
| Tarifas click-to-edit + login UX + lockout | sesión 2026-08-24 |
