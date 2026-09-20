# Pendientes — Estacionamiento Proyecto

Última actualización: 2026-09-20

---

## 🗺️ Estado del deploy

- **Railway** → ambiente de prueba activo. No es producción municipal real.
- **Digital Ocean App Platform** → deploy definitivo antes de entregar a un municipio real.

### Orden recomendado antes del go-live municipal

```
1. Corregir bugs 🟡 abajo
2. Test end-to-end comisiones (🟡 abajo)
3. Migrar a Digital Ocean App Platform (🔴 abajo)
4. Smoke test en DO con URL temporal
5. Corte al municipio real → switch de dominio
```

---

## 🔴 Alta prioridad

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

- **Inspector — impresora BLE: duplicado no imprime**
  Detectado en testing. El acta de segunda copia no se envía a la impresora. En sesión 10 se mejoró la distinción de fallo (mensaje diferenciado si copia 1 salió o no), pero el duplicado en sí sigue sin funcionar. Revisar `imprimirActa()` segunda pasada en `ticket_infraccion.html`.

- **Inspector — impresora BLE: vuelve a pedir vinculación**
  Workaround actual: reconectar por nombre. Evaluar si Chrome corrigió el bug de `getDevices()` o documentar como límite del navegador. Archivo: `static/.../js/impresora_bluetooth.js` (función `reconectarImpresora`).

- **Div notificaciones del conductor no es responsive en mobile**
  El bloque de preferencias de notificaciones en el panel conductor se rompe en pantalla chica. Revisar `templates/conductores/inicio_usuarios.html` — el `<div>` colapsable de notificaciones en el footer.

- **Abono: mostrar el precio antes del botón de confirmar**
  En el flujo de cobro de abono del vendedor, el precio aparece recién después de hacer clic en "Ver precio y confirmar". Debería mostrarse antes. Archivo: `templates/vendedores/cobrar_abono.html`.

---

## 🟢 Baja prioridad / Futuras versiones

- **Notificación antes de que venza el estacionamiento / abono** — push notification o email con X minutos de antelación, configurable por municipio.
- **Pago diario (módulo premium)** — superadmin habilita por municipio, municipio asigna valor. Requiere diseño de modelo antes de implementar.
c— hoy el saldo del conductor es global. Largo plazo: una billetera por municipio. Requiere diseño arquitectural.
- **OCR de patentes** — botón "📷 Escanear" en `verificar.html` con Google ML Kit o Tesseract.js.
- **Alertas de vencimiento al conductor** — push / WhatsApp.
- **Tutorial GIFs en landing pública** — el tutorial por rol ya existe dentro del sistema. Pendiente: versión con GIF para la landing pública.
- **Auditoría de reseteos de contraseña** — registrar quién reseteó la contraseña de quién. Usar `LogEntry` de Django Admin o modelo propio.
- **Refactor estilos inline** — muchos templates tienen `style=""` repetido. Crear clases `.card-form`, `.section-admin` en `global.css`.

---

## ℹ️ No son bugs del sistema

- **Error `contentscript.js: [object Object] Resetting the streams.`** en `/tesorero/rendicion/`:
  Viene de una extensión del navegador (Grammarly, Loom, etc.). No es un error Django. Solución: desactivar extensiones en esa tab o usar modo incógnito sin extensiones.
