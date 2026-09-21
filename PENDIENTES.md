# Pendientes — Estacionamiento Proyecto

Última actualización: 2026-09-21 (sesión 14 — continuación)

---

## 🗺️ Estado del deploy

- **Railway** → ambiente de prueba activo. No es producción municipal real.
- **Digital Ocean App Platform** → deploy definitivo antes de entregar a un municipio real.

### Orden recomendado antes del go-live municipal

```
1. Comisiones test end-to-end (🟡 abajo)
2. Migrar a Digital Ocean App Platform (🔴 abajo)
3. Smoke test en DO con URL temporal
4. Corte al municipio real → switch de dominio
```

---

## 🔴 Alta prioridad

### Notificaciones push al conductor (vencimiento de estacionamiento / abono)

El conductor no recibe aviso cuando le queda poco tiempo en el estacionamiento ni cuando le vence el abono. Esta feature es importante para la experiencia de uso diario.

**Tecnología:** la app ya es PWA con `sw.js` registrado. En Android Chrome las notificaciones push funcionan igual que en una app nativa. En iOS desde iOS 16.4 si la PWA está en el homescreen.

**Implementación (cuando se encare):**
1. Generar VAPID keys (`py -m py_webpush generatekeys`).
2. Instalar `pywebpush` + crear modelo `SuscripcionPush(usuario, endpoint, p256dh, auth)`.
3. Endpoint `/push/suscribir/` que guarda la suscripción del navegador.
4. Extender `sw.js` para manejar el evento `push` y mostrar la notificación.
5. Tarea programada (o señal Django) que envía el push X minutos antes del vencimiento — configurable por municipio (`Municipio.minutos_aviso_vencimiento`).
6. Misma infraestructura para abono: aviso N días antes del vencimiento del mes.

**Nota:** no combinar con la sección "Notificaciones internas" (`Notificacion` model) — esas son avisos dentro de la app. Las push son notificaciones del sistema operativo, fuera de la app.

---

### Migración a Digital Ocean App Platform

Railway es el ambiente de prueba actual. DO App Platform es el destino de producción municipal. Hacer en paralelo — no apagar Railway hasta confirmar que DO funciona.

#### Paso 1 — Preparar DO (sin tocar Railway)

1. Crear cuenta DO → **App Platform** → "Create App" → conectar el repo de GitHub (rama `main`).
2. DO detecta Python automáticamente. Configurar:
   - **Run command:** `gunicorn estacionamiento.wsgi --bind 0.0.0.0:$PORT`
   - **Build command:** `pip install -r requirements.txt && python manage.py collectstatic --noinput`
   - **Post-deploy job:** `python manage.py migrate`
3. Agregar base de datos: en el wizard → "Add Resource" → **PostgreSQL** (~$7/mes dev). DO inyecta `DATABASE_URL` automáticamente.

#### Paso 2 — Variables de entorno en DO

En App Platform → Settings → Environment Variables. Copiar de Railway:

| Variable | ¿Cambia? | Acción |
|---|---|---|
| `SECRET_KEY` | No | Copiar igual |
| `DATABASE_URL` | Sí | DO la inyecta automático — no setear manualmente |
| `DEBUG` | No | Debe ser `False` |
| `ALLOWED_HOSTS` | Sí | Agregar URL temporal de DO + dominio final del municipio |
| `CLOUDINARY_*` | No | Copiar igual |
| `MP_ACCESS_TOKEN`, `MP_PUBLIC_KEY` | No | Copiar igual |
| `MP_WEBHOOK_SECRET` | No | Copiar igual |
| `ANYMAIL_*` | No | Copiar igual |
| `SENTRY_DSN` | No | Copiar igual (o nuevo proyecto Sentry para separar prod de prueba) |

#### Paso 3 — Migrar la base de datos

```bash
pg_dump $RAILWAY_DATABASE_URL > backup_railway_$(date +%Y%m%d).sql
psql $DO_DATABASE_URL < backup_railway_YYYYMMDD.sql
python manage.py migrate --check
```

Si los datos de Railway son solo de prueba, se puede saltear el dump y correr solo `python manage.py migrate` sobre la BD vacía de DO.

#### Paso 4 — Cron jobs en DO App Platform

DO App Platform tiene "Jobs" en schedule:
- **Nombre:** `revocar-exenciones`
- **Command:** `python manage.py revocar_exenciones_vencidas`
- **Schedule:** `0 3 * * *` (3am todos los días)

#### Paso 5 — Smoke test (URL temporal, sin cambiar DNS)

Con la app corriendo en `https://app-nombre-xyz.ondigitalocean.app`:
- [ ] Login de cada rol
- [ ] Registrar estacionamiento completo (incluyendo débito de saldo)
- [ ] Registrar infracción y cobrarla
- [ ] Rendición de vendedor → admin certifica → tesorero deposita
- [ ] Verificar emails (Brevo/Resend)
- [ ] Verificar que Cloudinary sirve imágenes

#### Paso 6 — Corte: switch de dominio

1. DO App Platform → Settings → Domains → agregar dominio del municipio. SSL automático.
2. Registrador de dominio → apuntar DNS al valor de DO. Propagación: 5–30 min.
3. **Actualizar webhook de MercadoPago** → Credenciales → Webhooks → nueva URL. Fácil de olvidar.
4. Actualizar UptimeRobot con la nueva URL.
5. Dejar Railway activo 3–5 días como fallback, después apagar.

---

## 🟡 Media prioridad

- **Comisiones de vendedores — test end-to-end** (hacer ANTES de la migración a DO)
  Prueba manual completa según `GUIA_TESTING_ROLES.md` → sección "TEST COMPLETO: Flujo de comisiones de vendedores".

---

## 🟢 Baja prioridad / Futuras versiones

- **OCR de patentes con cámara (mejora)** — actualmente hay un botón básico de escaneo. Mejora real con Google ML Kit o Tesseract.js, especialmente útil para el inspector en campo. Evaluar para después del go-live municipal cuando haya volumen real de uso.
- **Tutorial GIFs en landing pública** — el tutorial por rol ya existe dentro del sistema como `<details>` colapsable. Pendiente: versión con GIFs animados para la landing pública.
- **Pago diario (módulo premium)** — superadmin habilita por municipio, municipio asigna valor. Requiere diseño de modelo antes de implementar.
- **Verificación de dos pasos (2FA)** — para el go-live municipal, especialmente para roles admin y tesorero. Django tiene soporte nativo con `django-otp` o `django-two-factor-auth`. Evaluar después de la migración a DO.
- **`/admin/mapa-infracciones/` — errores de consola**: Los `ChunkLoadError` son de la extensión de Chrome **Excalidraw** (`chrome-extension://lkeokcighogdliiajgbbdjibidaaeang`), NO del código de la app. La traza viene de `content.js:2` (content script de la extensión). La página funciona correctamente con Leaflet/OSM. Verificar desactivando la extensión. El banner "beforeinstallprompt" es del PWA y es intencional.

---

## ✅ Resuelto (sesión 14 — continuación — 2026-09-21)

- **Auditoría de reseteos de contraseña**: modelo `AuditoriaPassword` con ForeignKey a admin, conductor y municipio; campo `tipo` (choices: "dni" / "personalizada"), campo `ip` opcional, `fecha` con `auto_now_add=True`. Migración `0088` creada manualmente. `views_admin.py::detalle_usuario_admin` crea un registro en `cambiar_password` y en `resetear_password_dni`. Historial de los últimos 10 cambios se pasa al template en `historial_passwords` y se muestra dentro de la sección colapsable `🔑 Cambiar contraseña`.

- **`/admin-subcuadras/` habilitado para admin con flag de superadmin**: campo `puede_gestionar_subcuadras` (BooleanField, default=False) en `Municipio`. Migración `0087`. `views_admin.py::gestionar_subcuadras` cambia de `@require_role("superadmin")` a `@require_role("admin", "superadmin")` + gate interno: si no es superadmin y el flag está desactivado → `HttpResponseForbidden` con mensaje explicativo. El superadmin activa el flag desde `editar_municipio.html` (nuevo checkbox, mismo patrón que `modulo_informes_activo`). `views_superadmin.py` guarda el valor del POST.

## ✅ Resuelto (sesión 14 — continuación — 2026-09-20)

- **BLE impresora — duplicado no imprime**: causa raíz: `gatt.connected` puede devolver `true` con la conexión stale; `writeValueWithoutResponse` enviaba bytes al vacío sin lanzar error. Fix en `ticket_infraccion.html`: (a) desconectar explícitamente después de copia 1, (b) reconectar siempre antes de copia 2 con `reconectarSilencioso()` (solo `getDevices()`, sin diálogo — porque el gesto de usuario expiró entre los awaits), (c) si `getDevices()` falla, lanzar error → catch → botón "Reintentar copia 2" que SÍ tiene gesto fresco. Nueva función `reconectarSilencioso()` en `impresora_bluetooth.js`.
- **BLE impresora — vuelve a pedir vinculación**: límite de Chrome — `getDevices()` pierde la sesión al navegar entre páginas (bug conocido, sin fix del lado de la app). El workaround ya existía: Intento 2 en `reconectarImpresora()` usa `requestDevice({filters: [{name}]})` pre-filtrado. Para impresoras sin nombre de hardware (`device.name === null`), el diálogo abre sin filtro (comportamiento esperado). Mejora de UX: cuando se abre el diálogo, `imprimirActa()` ahora muestra el alias guardado ("Seleccioná 'MTP-II' en el diálogo...") para orientar al inspector.

## ✅ Resuelto (sesión 14 — 2026-09-20)

- **10 errores en tests** (2 FAIL + 8 ERROR): (a) `nombre_completo()` con paréntesis en 9 lugares de `views_inspector.py` y `views_admin.py` — es `@property`, no método, se quitaron los `()`. (b) `UnboundLocalError` en `panel_tesorero`: `cierres_admin_sin_certificar` se usaba antes de definirse, se movió la definición del queryset arriba del `.count()`. (c) Tests `test_saldo_se_descuenta_al_estacionar` y `test_conductor_sin_saldo_redirige_a_carga_mp` fallaban porque sin `HorarioEstacionamiento` el costo siempre es $0 — se agrega horario 00:00–23:59 para los 7 días en `BaseRolesTest.setUp()`.

- **Refactor estilos inline → clases CSS**: 5 clases utilitarias en `global.css` (`.page-header`, `.form-narrow`, `.form-narrow-md`, `.card-empty`, `.td-sin-datos`, `.label-sm`). 84 reemplazos automáticos en 58 templates. Correctamente preservados 3 casos con propiedades extra (`flex-shrink`, `background`, `border`). Los tests se corren en local con `python manage.py test app_estacionamiento`.

## ✅ Resuelto (sesión 13 continuación — 2026-09-20)

- **`Municipio.modulo_informes_activo` — flag por municipio para tab Informes**: campo BooleanField agregado a `models.py`. Migración `0086`. `admin_rendiciones` en `views_admin.py` redirige a `cierres` si el flag está desactivado. Tab "📨 Informes" en `rendiciones.html` se muestra solo si el flag es True. Checkbox toggle agregado en `templates/superadmin/editar_municipio.html` (mismo patrón que `admin_puede_editar_plantillas`). `views_superadmin.py` guarda el valor del POST con `== "on"`.
- **Rediseño UX `/admin-rendiciones/`**: banner de flujo de 3 pasos visible en todas las secciones (① Certificar cierres → ② Rendir a tesorería → ③ Tesorería valida), con estado visual dinámico (⏳/✅) según `conteo_pendientes`. Tabs renombrados con números. Tab de cierres muestra botón "② Crear rendición →" cuando no hay pendientes. Notas contextuales en tabs de rendición y comisiones explicando que las comisiones se generan automáticamente al crear la rendición.

## ✅ Resuelto (sesión 13 — 2026-09-20)

- **BilleteraConductor (saldo por municipio)**: modelo `BilleteraConductor(conductor, municipio, saldo)` creado con `UniqueConstraint`. Migración `0085`. `services/saldo.py` → `debitar_saldo_conductor()` y `cargar_saldo_conductor()` usan BilleteraConductor como fuente de verdad. `acreditar_saldo_mp` y `views_mp.py` pasan `municipio_id` en metadata de MP. `views_conductor.py` muestra saldo por municipio. Tests actualizados en `tests.py`, `tests_roles.py` y `tests_servicios.py` (reemplazado `usuario.saldo` por `obtener_saldo_conductor()`). `Usuario.saldo` queda como campo legacy.
- **`/admin-subcuadras/` restringido a superadmin**: `@require_role` cambiado de `("admin", "superadmin")` a `("superadmin")`. Admin municipal recibe 403 hasta que se estabilice la vista. *(Revertido en sesión 14: ahora admin puede acceder si el superadmin activa el flag `puede_gestionar_subcuadras`.)*
- **Mail automático al resetear contraseña al DNI**: `views_admin.py` handler `resetear_password_dni` envía mail con `send_mail(..., fail_silently=True)` dentro de `try/except`. No interrumpe el flujo si el mail falla. Usa nombre del municipio como remitente contextual.
- **`panel_tesorero.html` — UX y bugs**: 3 tarjetas de stat al tope (rendiciones pendientes / comisiones a depositar / cierres sin certificar) con links de ancla a las secciones. Cierres sin certificar aparecen en el resumen de arriba con callout de advertencia en la sección de rendiciones. Nota explicativa en "Comisiones de vendedores" aclarando que se crean al generar rendición, no al certificar cierre. Tutorial movido al pie del panel. `views_tesorero.py` agrega `pendientes_cierres_admin` al contexto.
- **Flujo confirmación depósito tesorero → vendedor**: `panel_vendedor.html` muestra alerta prominente en azul cuando hay comisiones en estado "depositada" esperando confirmación del vendedor. `views_vendedor.py` agrega `comisiones_a_certificar` al contexto. El vendedor puede confirmar desde su panel sin que el tesorero lo avise.

## ✅ Resuelto (sesión 12 — 2026-09-20)

- **`/mp/cargar/` — input de monto solo acepta enteros**: `inputmode="numeric"` + `sanitizarMonto()` que filtra con `/[^0-9]/g`. Sin decimales ni caracteres especiales.
- **`/inicio/` — sección "Mis vehículos"**: muestra cada vehículo del conductor con iconos de estado: 🟢 estacionamiento activo, infracciones pendientes (⚠️ N), exento (🏷️). Links a historial e infracciones filtrados por `?patente=`.
- **Multi-vehículo simultáneo**: la constraint de DB ya era por vehículo, no por conductor. La vista traía solo el primero con `.first()`. Corregido: lista completa con auto-cierre de expirados, anotación Python `tiene_estacionamiento_activo` en O(1).
- **`/abono/` — agregar vehículo inline**: `<details>` expandible en la misma página, `accion=agregar_vehiculo`, pre-selecciona el nuevo vehículo en el select.
- **`/mis-infracciones/` — cards responsive**: tabla reemplazada por cards con `toggleDetalle()`. Icono estado (✅/⚠️/🚫), sin la palabra "Calle" redundante, foto expandible, modal de pago fuera del card (z-index). Filtro por `?patente=` opcional.
- **`/mis_estacionamientos/` — cards clickeables**: mismo patrón expandible. Icono 🟢/⚪ por estado, detalle con tabla y botones si activo.
- **`/admin-usuarios/<id>/` — layout expandible**: secciones `<details>/<summary>`. "Cargar saldo" y "Agregar vehículo" siempre visibles como acciones rápidas. Sección de contraseña colapsada con borde de advertencia. Botón "Resetear al DNI" (usa `accion=resetear_password_dni`). `<section-password>` se abre automáticamente si el conductor tiene cambio pendiente.
- **Resetear contraseña al DNI**: handler en `views_admin.py` (`accion=resetear_password_dni`), valida que el DNI tenga al menos 6 caracteres, activa `cambio_password_requerido=True`. Si no tiene DNI, el botón queda deshabilitado.
