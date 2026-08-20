# Pendientes — Estacionamiento Proyecto

Última actualización: 2026-08-20 (sesión: fixes vista previa ticket + tarifas duplicadas)

---

## 🗺️ Contexto de deploy

- **Railway** → ambiente de prueba (inspectores + admin testeando). No es producción municipal real.
- **Digital Ocean** → deploy definitivo cuando el sistema vaya a municipios reales pagando.
- El código es el mismo; los cambios son de infraestructura y configuración.

---

## 🔴 Alta prioridad

### Monto $0 en actas de prueba (aclaración — no es un bug)
Las infracciones creadas cuando `Tarifa.monto_infraccion` estaba en 0 siempre van a mostrar $0,
porque el monto se fotografia al crear el acta (no se lee en tiempo real).
→ Configurar `monto_infraccion` en `admin-tarifas/` y **crear una infracción nueva** para testearlo.
El código es correcto: `crear_infraccion()` lee `tarifa.monto_infraccion` al momento de crear.

---

## 🟡 Media prioridad

### 3. Test MercadoPago end-to-end en Railway
Probar el flujo completo en Railway:
- Ingresar patente con infracción pendiente → pagar vía MP → verificar que el webhook procesa correctamente.
- Verificar también el flujo de carga de saldo del conductor.

### 4. 🔐 Riesgo pre-registro OAuth
Combinado con `SOCIALACCOUNT_AUTO_SIGNUP = True`, un atacante puede registrar el email de otra
persona antes que ella vía Google. Para mitigarlo: bloquear auto-connect en `SocialAccountAdapter.save_user`
cuando el email ya existe en la base sin ser de Google.

### 5. 📹 Tutorial de uso — landing
El tutorial por rol ya está en cada panel (ver ✅ abajo).
Falta: versión visual para la landing (GIF animado o secuencia de capturas con flechas).
Flujos clave a mostrar en la landing:
- Conductor: registrar estacionamiento (patente → duración → confirmar)
- Inspector: verificar + registrar infracción + imprimir acta BLE
- Vendedor: cobrar abono / infracción

---

## 🟢 Baja prioridad / Futuras versiones

### ~~PWA icons~~ → ✅ resuelto (ver abajo)

### GitHub Pages: actualizar landing
`leandrolopezalbini.github.io/estacionar/` — clonar ese repo por separado
y pegar el contenido actualizado de `landing.html`.

### Responsive > 1050px
En pantallas grandes el layout del panel admin queda con mucho espacio vacío.

### Migración a Digital Ocean (producción municipal real)
**Disparador**: cuando el sistema pase de pruebas a municipio real pagando.
Ver checklist: `CHECKLIST_PRODUCCION_2026-07-25.md`.

### Inspector como cobrador (configurable por municipio)
Toggle gestionado por superadmin (via `ModuloMunicipio` o flag en `Municipio`).

### Transferencia de saldo entre usuarios
Nuevo modelo `TransferenciaSaldo` (emisor, receptor, monto, estado, creado_en).
Receptor tiene 24h para aceptar.

### Reconocimiento de patente por cámara (OCR)
Google ML Kit, Tesseract.js o API de OCR. Botón "📷 Escanear" en `verificar.html`.

### Alertas de vencimiento al conductor (push / WhatsApp)
Push via service worker (PWA) o WhatsApp via Twilio/360dialog.

### Mapa de calor de infracciones
Leaflet.js + lat/lon de subcuadras. Requiere coordenadas en Subcuadra (ya implementadas).

### Módulo de impugnaciones
`Impugnacion` (infraccion, conductor, motivo, evidencia, estado). Admin resuelve desde panel.

### Dashboard en TV (pantalla municipal en tiempo real)
Vista sin login con token de solo lectura. Auto-refresh cada 60s.

### Mejoras OAuth y UI
- Pantalla de consentimiento Google: completar logo, descripción, dominio verificado.
- Modo alto contraste / uso en exterior con sol.
- Separar `settings_dev.py` / `settings_prod.py`.

### Toggle estadísticas por municipio (desde Django Admin)
`Municipio.estadisticas_inspectores_activo = BooleanField(default=True)`. 1 migración, 1 chequeo.

---

## ✅ Resuelto recientemente

**Sesión 2026-08-20** — Tutorial por rol + fixes:
- Tutorial colapsable (`<details>`) agregado en los 4 paneles: conductor (`inicio_usuarios.html`), inspector (`panel_inspectores.html`), vendedor (`vendedores/panel.html`), admin (`panel_admin.html`) y tesorero (`panel_tesorero.html`). Pasos numerados con íconos, sin JS ni localStorage. ✅

**Sesión 2026-08-20** — Vista previa ticket + tarifas:
- `ticket_infraccion.html`: agregada vista previa de `leyenda_horarios` y `texto_ordenanza` en HTML (debajo del inspector, antes del QR). ✅
- `gestionar_tarifas` GET path: auto-limpia registros `Tarifa` duplicados (ordena por `-precio_por_hora`, elimina los extras). Evita que el formulario muestre placeholders cuando existen duplicados con defaults. ✅
- `gestionar_tarifas` POST path: usa `filter().update()` en vez de `update_or_create()` para no romper con `MultipleObjectsReturned`. ✅

**Sesión 2026-08-19** — Impresora BLE, superadmin y subcuadras:
- `impresora_bluetooth.js`: persistencia de impresora en `localStorage` (workaround bug `getDevices()` en Chrome Android). Reconexión silenciosa → si falla, `requestDevice()` filtrado por nombre conocido.
- Renombrado de impresoras por alias (inspectores con múltiples impresoras iguales).
- Ticket de infracción: doble copia automática (800ms entre copias). Sin `window.print()` — solo BLE.
- QR nativo ESC/POS via `GS(k)` + URL texto como respaldo.
- Fix patente cortada: `centrar()` acepta `ancho` opcional. En modo doble-ancho (`GS 0x21 0x11`) se usa `ANCHO/2 = 16` para no desbordar. Mismo fix para el monto en grande.
- Superadmin `editar_municipio`: eliminado campo `comision_vendedor` (pertenece solo al admin del municipio).
- Superadmin `editar_municipio`: nuevos campos `leyenda_horarios` y `texto_ordenanza` (migración 0053). Se guardan en `Municipio`.
- Superadmin `editar_municipio`: descripción de cada módulo de pago visible en el panel.
- Fix `modulos_asignados.values_list()` sobre lista: cambiado a comprensión de set (`set(m.modulo for m in modulos)`).
- Admin `gestionar_tarifas`: fix `MultipleObjectsReturned` (usa `filter().first()`). `Tarifa.precio_por_hora` max_digits 6→10.
- Subcuadras GPS: selector cascade Calle → Altura. Botón "Eliminar" más visible.
- PWA icons: `icon-192.png`, `icon-512.png`, `apple-touch-icon.png` reemplazados con íconos reales. `<link rel="icon">` agregado en `base.html`. ✅

**Sesión 2026-08-18** — Límites de carga MercadoPago configurables por municipio:
- `Municipio.monto_minimo_carga` y `monto_maximo_carga` (PositiveIntegerField, defecto 500/50.000). Migración 0052.
- `mp_iniciar_carga` rechaza montos fuera del rango con mensaje claro antes de llamar a la API de MP.
- Superadmin puede configurar los límites en `editar_municipio` (dos inputs numéricos nuevos).
- `mp_cargar_saldo.html` muestra el rango al conductor (min/max dinámicos desde el contexto).
- Helper `_contexto_cargar_saldo(usuario)` centraliza el contexto del formulario. ✅

**Sesión 2026-08-18** — Restore test del backup:
- Restore exitoso con Docker postgres:18: 21 usuarios recuperados, tablas íntegras. ✅
- Comando: `gunzip -c backup.sql.gz | psql -U postgres -d postgres` (dentro del container).

**Sesión 2026-08-18** — Backups PostgreSQL funcionales:
- Workflow usa imagen Docker `postgres:18` (fix para version mismatch con Railway).
- URL pública de Railway con `?sslmode=require` como secret `RAILWAY_DATABASE_URL`.
- Backup confirmado: ~52 KB. Corre diariamente a las 03:00 UTC desde `main`. ✅
- Pendiente: restore test antes del go-live real.

**Sesión 2026-08-18** — Hallazgos de seguridad (4 fixes + 5 tests):
- `registro_view`: valida `municipio activo=True` antes de asignar.
- `importar_estacionamientos`: límite 10 MB antes de `openpyxl.load_workbook()`.
- `mp_webhook`: valida timestamp reciente (anti-replay, tolerancia 5 min).
- `django-axes`: `AXES_USERNAME_FORM_FIELD = "correo"` + lockout combinado IP+usuario.
- Fix adicional: `login()` en registro especifica `backend=` (bug real con múltiples backends).
- 160 tests, todos OK. ✅

**Sesión 2026-08-18** — Verificación de email obligatoria:
- `ACCOUNT_EMAIL_VERIFICATION = mandatory` activado en Railway. ✅
- `views_auth.py`: `registro_view` ahora crea `EmailAddress` y envía confirmación si `ACCOUNT_EMAIL_VERIFICATION = mandatory`.
  `login_view` bloquea acceso si hay un `EmailAddress` sin verificar, re-enviando el link.
- `apps.py`: señal `email_confirmed` de allauth → `messages.success()` → aparece en login post-confirmación.
- Templates nuevos: `account/email_verification_sent.html`, `account/confirm_email.html`.
- `settings.py`: `ACCOUNT_EMAIL_VERIFICATION` ahora lee de env var (default: "none"). `ACCOUNT_LOGIN_ON_EMAIL_CONFIRMATION = True`.
- **Para activar en Railway**: agregar `ACCOUNT_EMAIL_VERIFICATION = mandatory`.

**Sesión 2026-08-18** — Backups PostgreSQL + Email transaccional:
- `.github/workflows/backup.yml`: pg_dump diario (03:00 UTC) → artifact GitHub Actions 30 días.
- Requiere secret `RAILWAY_DATABASE_URL` en GitHub y verificar restore al menos una vez.
- Email (Brevo): sender verificado, BREVO_API_KEY en Railway, adapter con manejo de errores. ✅

**Sesión 2026-08-18** — Email transaccional (recuperación de contraseña):
- Brevo configurado como backend de email (anymail): remitente verificado, API key y `DEFAULT_FROM_EMAIL` en Railway.
- `adapters.py`: `send_mail()` captura excepciones → usuario ve confirmación aunque el email falle, error logueado en Railway.
- Activación de cuenta Brevo desbloqueada verificando teléfono → emails llegando correctamente ✅

**Sesión 2026-08-17** — Refactor CSS + color theming + footer:
- Botón Google: eliminado `::before` pseudo-elemento que duplicaba el logo; colores oficiales Google.
- CSS migrado de templates a `global.css`: `login.html`, `verificar.html`, `registrar_infraccion.html`.
- Color theming: navbar y botones usan `var(--color-primary)` inyectado desde `Municipio.color_primario` en `base.html`.
- Fix responsividad: revertido `var(--color-nav-bg)` → `var(--color-primary)`.
- Footer: `background: var(--color-primary); color: rgba(255,255,255,0.85)` — color del municipio.

**Sesión 2026-08-13** — Pagos públicos + PWA + Branding:
- Modelo `PagoPublico` (migración 0051), use case `procesar_pago_publico.py` (idempotente).
- Webhook MP actualizado: detecta `metadata.pago_publico_id`.
- 4 templates pago público: `buscar.html`, `detalle_patente.html`, `resultado.html`, `error.html`.
- `beforeinstallprompt` → botón "📲 Instalar" en navbar (PWA).
- Superadmin `editar_municipio`: upload logo, colores primario/secundario, nombre_sistema.

**Sesiones anteriores (2026-08-10/11)** — GPS + Seguridad + Exenciones + Rendiciones:
- `Subcuadra.lat/lon` + endpoint GPS + cascade Calle→Altura en `verificar.html`.
- Importación de exenciones desde Excel (preview + confirmación).
- `PlantillaDocumento` (5 tipos de comprobante personalizables).
- `MovimientoCaja.mp_payment_id (unique)` — idempotencia MP.
- Rendiciones: PDF, tesorero valida/observa, LiquidacionComision con factura.
- Logging de seguridad en `require_role()` y `login_view()`.
