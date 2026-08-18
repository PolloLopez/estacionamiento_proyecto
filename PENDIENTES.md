# Pendientes — Estacionamiento Proyecto

Última actualización: 2026-08-17 (sesión: refactor CSS + fix botón Google + footer theming)

---

## 🗺️ Contexto de deploy

- **Railway** → ambiente de prueba (inspectores + admin testeando). No es producción municipal real.
- **Digital Ocean** → deploy definitivo cuando el sistema vaya a municipios reales pagando.
- El código es el mismo; los cambios son de infraestructura y configuración.

---

## 🔴 Alta prioridad

### 1. PRODUCCIÓN: Verificar restauración del backup
El workflow `.github/workflows/backup.yml` corre `pg_dump` diariamente (03:00 UTC) usando
imagen Docker `postgres:18` (Railway corre PG 18). Artifact de ~52 KB confirmado ✅
**Pendiente**: ejecutar un restore de prueba antes del go-live real para confirmar que el backup
es válido y recuperable. Comando para restaurar localmente:
```bash
gunzip -c backup_YYYY-MM-DD_HH-MM.sql.gz | psql $DATABASE_URL_LOCAL
```


---

## 🟡 Media prioridad

### 3. Test MercadoPago end-to-end en Railway
Probar el flujo completo en Railway:
- Ingresar patente con infracción pendiente → pagar vía MP → verificar que el webhook procesa correctamente.
- Verificar también el flujo de carga de saldo del conductor.

### 4. Activar verificación de email en Railway (1 variable de entorno)
El código está implementado. Solo falta setear en Railway:
```
ACCOUNT_EMAIL_VERIFICATION = mandatory
```
Con eso activo, el registro crea un `EmailAddress` sin verificar, envía el email de confirmación,
y bloquea el login hasta que el conductor haga clic en el link.
Los usuarios creados por admin (sin `EmailAddress` en allauth) y los de Google OAuth no se ven afectados.

⚠️ Activar solo después de verificar que Brevo está entregando correctamente (ya funciona ✅).

⚠️ Riesgo pendiente: combinado con `SOCIALACCOUNT_AUTO_SIGNUP = True`, sigue permitiendo ataque
de pre-registro (registrar el email de otra persona antes que ella vía Google). Para mitigarlo,
evaluar bloquear auto-connect en `SocialAccountAdapter.save_user` (tarea separada).

### 5. 🔐 Hallazgos menores — auditoría de seguridad 2026-08-03
- `registro_view`: no valida que el `municipio_id` recibido por POST tenga `activo=True`.
- `importar_estacionamientos`: sin límite de tamaño antes de `openpyxl.load_workbook()`.
- `mp_webhook`: la firma HMAC no valida que el `ts` del manifest sea reciente (anti-replay).
- `django-axes`: solo bloquea por IP; evaluar umbral combinado IP+usuario.

### 6. 🔐 Límite máximo de monto en MercadoPago
Validar en `mp_iniciar_carga` que el monto no supere un tope (ej. $50.000).

---

## 🟢 Baja prioridad / Futuras versiones

### PWA icons
Diseñar con GPT o Canva → reemplazar los 3 archivos en `static/icons/`:
`icon-192.png`, `icon-512.png`, `apple-touch-icon.png`.

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

**Sesión 2026-08-18** — Backups PostgreSQL funcionales:
- Workflow usa imagen Docker `postgres:18` (fix para version mismatch con Railway).
- URL pública de Railway con `?sslmode=require` como secret `RAILWAY_DATABASE_URL`.
- Backup confirmado: ~52 KB. Corre diariamente a las 03:00 UTC desde `main`. ✅
- Pendiente: restore test antes del go-live real.

**Sesión 2026-08-18** — Verificación de email obligatoria:
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
