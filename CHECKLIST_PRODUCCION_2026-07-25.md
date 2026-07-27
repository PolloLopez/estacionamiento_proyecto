# Checklist de paso a producción — Estacionamiento Medido
Fecha: 2026-07-25
Destino: municipio real (conductores, inspectores, vendedores, admin, tesorero).
Maneja datos personales de ciudadanos: correo, patente, historial de infracciones y pagos.
Criticidad: alta — es un sistema con impacto legal (infracciones municipales) y financiero (cobros reales con MercadoPago).

Auditorías previas completadas: seguridad ✅ · rendimiento ✅ · base de datos ✅ · trazabilidad ✅

---

## Resumen ejecutivo

El sistema está en buena forma para seguir en su fase de pruebas en Railway, pero tiene **3 bloqueantes reales** antes de que un municipio lo use con datos reales: no hay backups automáticos del PostgreSQL (pérdida de datos irrecuperable si Railway falla), el webhook de MercadoPago acepta POSTs sin verificar firma (riesgo de créditos falsos), y el login no tiene rate limiting (brute force ilimitado). Además, hay 4 items recomendados que marcan la diferencia entre "el sistema funciona" y "el sistema es confiable en producción": error tracking, email SMTP, uptime monitoring, y plan documentado de limpieza de datos de prueba. Ninguno de estos toma más de un día de trabajo.

---

## Pendientes

### 🔴 Bloqueante

**1. Sin backups automáticos del PostgreSQL de Railway Hobby**
Railway Hobby ($5/mes) no incluye backups automáticos de la base de datos. Si Railway tiene un incidente o se borra el add-on de PostgreSQL accidentalmente, los datos del municipio se pierden para siempre. Esta es la brecha más crítica del sistema en producción real.

Opciones:
- **Opción A (más simple):** Actualizar a Railway Pro ($20/mes) → habilita backups diarios automáticos desde el dashboard de Railway.
- **Opción B (más control):** Script `pg_dump` en un scheduled task de Railway o GitHub Actions que corra diariamente y suba el .dump a un bucket S3/Backblaze B2/Google Cloud Storage.
- **Mínimo aceptable antes del go-live:** tener al menos 1 backup manual reciente y un proceso automático diario funcionando. Verificar que el backup se puede restaurar al menos una vez antes del corte.

**2. Webhook de MercadoPago sin verificación de firma HMAC**
El endpoint `/mp/webhook/` acepta cualquier POST sin verificar el header `x-signature` de MercadoPago. La mitigación actual (re-consultar la API de MP con el `payment_id`) reduce el riesgo pero no lo elimina — un atacante puede enviar un payment_id real de otra cuenta.

Fix: verificar `x-signature` via HMAC-SHA256 con `MP_WEBHOOK_SECRET`. Agregar la variable en Railway.
Docs: https://www.mercadopago.com.ar/developers/es/docs/your-integrations/notifications/webhooks

Código de referencia:
```python
import hashlib, hmac

def verificar_firma_mp(request, webhook_secret):
    signature = request.headers.get("x-signature", "")
    # MP envía "ts=...;v1=..." — extraer el valor v1
    partes = dict(p.split("=", 1) for p in signature.split(";") if "=" in p)
    ts = partes.get("ts", "")
    v1_recibido = partes.get("v1", "")
    data_id = request.GET.get("data.id") or request.POST.get("data.id", "")
    # Template de MP para generar la firma
    manifest = f"id:{data_id};request-id:{request.headers.get('x-request-id','')};ts:{ts};"
    firma = hmac.new(webhook_secret.encode(), manifest.encode(), hashlib.sha256).hexdigest()
    return hmac.compare_digest(firma, v1_recibido)
```

**3. Sin rate limiting en login**
El `login_view` manual no tiene protección contra fuerza bruta. Con los datos personales y financieros que maneja el sistema, esto es un riesgo inaceptable en producción real.

Fix documentado en PENDIENTES.md: instalar `django-axes` (5 intentos → bloqueo 1 hora):
```
pip install django-axes
# INSTALLED_APPS += ["axes"]
# MIDDLEWARE: "axes.middleware.AxesMiddleware" después de SecurityMiddleware
# AXES_FAILURE_LIMIT = 5 / AXES_COOLOFF_TIME = 1
# python manage.py migrate
```

---

### 🟡 Recomendado antes del go-live

**4. Sin error tracking activo**
Si el sistema da un 500 en producción, hoy no hay alerta — solo se entera si alguien se queja. Los logs de Railway son accesibles pero requieren entrar al dashboard proactivamente.

Fix: Sentry (plan free alcanza para este volumen). Setup en ~15 minutos:
```
pip install sentry-sdk
```
```python
# settings.py
import sentry_sdk
if not DEBUG:
    sentry_sdk.init(
        dsn=os.getenv("SENTRY_DSN", ""),
        traces_sample_rate=0.1,
    )
```
Agregar `SENTRY_DSN` como variable de entorno en Railway. Sentry notifica por email cuando hay un error nuevo.

**5. Sin uptime monitoring**
No hay forma de saber si Railway se cae sin que alguien lo reporte. UptimeRobot (free) hace ping cada 5 minutos y avisa por email/Telegram si hay caída. Configuración: 5 minutos en https://uptimerobot.com.

**6. Email SMTP no configurado en Railway**
`EMAIL_BACKEND` cae en `console.EmailBackend` cuando no hay `EMAIL_HOST_USER`. Esto significa que la recuperación de contraseña no funciona para usuarios reales. Es un bloqueante operativo apenas el primer inspector olvide su contraseña.

Variables a configurar en Railway (documentadas en `settings.py`):
```
EMAIL_HOST=smtp.gmail.com
EMAIL_PORT=587
EMAIL_HOST_USER=tumail@gmail.com
EMAIL_HOST_PASSWORD=xxxx xxxx xxxx xxxx   ← contraseña de app de Google
DEFAULT_FROM_EMAIL=Sistema Estacionamiento <tumail@gmail.com>
```

**7. `ACCOUNT_EMAIL_VERIFICATION = "none"` — sin verificación de correo**
Cualquiera puede registrarse con un email falso. Depende de que el email SMTP esté configurado primero (item 6), pero una vez configurado: `ACCOUNT_EMAIL_VERIFICATION = "optional"` como mínimo antes del go-live.

**8. Sin dominio propio**
La URL actual `estacionamiento.up.railway.app` es una URL técnica de Railway. Para un municipio que va a usar esto como sistema oficial, necesita una URL propia (ej. `estacionamiento.munidemo.gob.ar` o similar). Implica:
- Dominio propio (registro o subdominio del municipio)
- Apuntar CNAME a Railway (o Digital Ocean si se migra)
- Actualizar `ALLOWED_HOSTS` y `CSRF_TRUSTED_ORIGINS` en Railway con el nuevo dominio

**9. Plan documentado de limpieza de datos de prueba**
Antes de que el municipio empiece a cargar datos reales, hay que definir exactamente qué se borra y en qué orden (las FK con PROTECT impiden borrar en orden incorrecto). Orden sugerido para borrar datos de prueba:

```sql
-- En el orden correcto por FK:
DELETE FROM app_estacionamiento_movimientocaja;
DELETE FROM app_estacionamiento_cierrecaja;
DELETE FROM app_estacionamiento_abonoasual;
DELETE FROM app_estacionamiento_infraccion;
DELETE FROM app_estacionamiento_estacionamiento;
DELETE FROM app_estacionamiento_vehiculausuario;
DELETE FROM app_estacionamiento_verificacioninspector;
-- Vehículos sin historial:
DELETE FROM app_estacionamiento_vehiculo WHERE id NOT IN (
    SELECT vehiculo_id FROM app_estacionamiento_infraccion
);
-- Usuarios conductores de prueba (NO tocar admin/inspector/vendedor si se reusan):
DELETE FROM app_estacionamiento_usuario WHERE es_conductor=True AND correo LIKE '%test%';
```

Hacer un backup manual ANTES de limpiar, por las dudas.

**10. `VerificacionInspector` — CASCADE en inspector y vehiculo**
Identificado en auditoría de base de datos (Fix 2 pendiente). Si se borra un inspector, sus verificaciones desaparecen — perdiendo el historial de auditoría. Cambiar a `PROTECT` como ya se hizo en `Infraccion`. Requiere migración 0045.

**11. Idempotencia MP: `mp_payment_id` sin campo único**
`acreditar_saldo_mp.py` usa `descripcion__contains="MP:{payment_id}"` para evitar doble acreditación. Si el formato de descripción cambia, la idempotencia se rompe silenciosamente. Agregar `mp_payment_id = CharField(max_length=50, null=True, unique=True)` a `MovimientoCaja` (migración pendiente, documentado en PENDIENTES.md).

---

### 🟢 Puede esperar

**12. `VehiculoUsuario` — `unique_together` faltante**
Verificar primero si hay duplicados en producción (`SELECT usuario_id, vehiculo_id, COUNT(*) FROM ... GROUP BY ... HAVING COUNT(*) > 1`), luego agregar el constraint. Si hay duplicados, resolverlos antes de migrar.

**13. CONTEXT.md desactualizado**
El campo de tests en CONTEXT.md dice "89 tests" — son 130. Actualizar para que la referencia sea correcta.

**14. Campos con nombres inconsistentes**
`Vehiculo.fecha_creacion` → `creado_en`, `VerificacionInspector.fecha` → `creado_en`. Mejora cosmética, sin urgencia operativa.

**15. Plan de rollback documentado**
Railway permite volver al deploy anterior desde el dashboard en ~30 segundos. Documentar el proceso exacto en CLAUDE.md para no tener que buscarlo bajo presión. Conecta con la skill `trazabilidad-versionado`.

**16. CSP headers (`django-csp`)**
Reduce la superficie de ataque XSS. No bloqueante mientras no haya contenido generado por usuarios que se inyecte sin escapar (Django templates escapan por defecto).

---

## Plan de go-live

### Antes del corte (1-2 semanas previas)

1. **Resolver los 3 bloqueantes** (items 1, 2, 3): backups, HMAC MP, rate limiting. Son independientes entre sí, se pueden hacer en paralelo.
2. **Email SMTP** (item 6): configurar en Railway y verificar que recuperación de contraseña funciona enviando un mail real.
3. **Sentry + UptimeRobot** (items 4, 5): configuración de ~20 minutos cada uno.
4. **Dominio propio** (item 8): coordinar con el municipio. Si usan un subdominio propio, tiempo de propagación DNS puede ser 24-48hs.
5. **`VerificacionInspector` PROTECT** (item 10): migración 0045 — bajo riesgo, aplica en Railway al deployar.
6. **`mp_payment_id` único** (item 11): migración 0046 con `null=True, unique=True` — safe migration.
7. **Correr `python manage.py test app_estacionamiento --verbosity=2`** en local → confirmar 130 tests OK.
8. **Backup manual** del PostgreSQL de Railway actual (antes de limpiar datos de prueba).
9. **Limpiar datos de prueba** (item 9): ejecutar en orden usando el script de arriba.
10. **Tag de versión**: `git tag -a v1.0.0 -m "go-live municipal — [nombre municipio]"` + `git push origin v1.0.0`.

### El corte en sí

1. Avisar a inspectores/admin: "A partir del [fecha], el sistema trabaja con datos reales. Los datos de prueba fueron borrados."
2. Si hay cambios en `develop` listos: `git checkout main && git merge develop && git push` → Railway deploya automáticamente.
3. Verificar en Railway que las migraciones corrieron sin error (logs del deploy).
4. **Smoke test** — 5 acciones críticas a probar manualmente antes de dar por cerrado el go-live:

| # | Acción | Resultado esperado |
|---|--------|--------------------|
| 1 | Login como admin | Ve panel con el municipio correcto, datos en cero |
| 2 | Inspector verifica una patente real | Resultado coherente (sin datos basura de prueba) |
| 3 | Conductor carga saldo via MercadoPago | Saldo acreditado correctamente, MovimientoCaja creado |
| 4 | Inspector labra infracción con foto | Foto aparece en Cloudinary, ticket visible |
| 5 | Vendedor cobra infracción en efectivo | Movimiento en caja, cierre disponible para admin |

### Primeros días

- Revisar logs de Railway y Sentry diariamente (primeros 3 días).
- Verificar cantidad de operaciones reales vs. esperado (si el municipio dijo "esperamos X infracciones por día", confirmar que se están cargando).
- Pedir feedback directo del inspector y admin sobre lo que usaron.
- Después del primer cierre de caja real: verificar que los montos cuadran (caja vs. movimientos).

### Si algo sale mal

- **Bug sin datos comprometidos:** Railway "Rollback" en el dashboard → vuelve al deploy anterior en ~30 segundos.
- **Bug con datos ya cargados:** restaurar backup del PostgreSQL + volver al deploy anterior.
- **Migración rota:** `git revert` del commit de la migración rota + `python manage.py migrate app_estacionamiento <migration_anterior>` en Railway (via Railway CLI o `railway run`).
- **Quién decide el rollback:** Leandro. Criterio: si el smoke test falla en más de 1 de los 5 pasos, hacer rollback y corregir antes de volver a intentar.

---

## Notas

- **Railway Hobby vs. Digital Ocean**: el sistema puede quedarse en Railway si el municipio acepta el SLA de Railway Hobby (no tiene SLA formal). Para un municipio grande o con exigencia de SLA, Digital Ocean App Platform o un Droplet con Nginx + Gunicorn + PostgreSQL gestionado es más robusto. El PENDIENTES.md ya tiene el checklist de migración a DO.
- **MP en sandbox vs. producción**: verificar que `MP_SANDBOX=False` en Railway (o que la variable no esté seteada, ya que sigue a `DEBUG`) antes del go-live. Con `DEBUG=False` en Railway, `MP_SANDBOX=False` por defecto — OK.
- **Cloudinary en producción**: ya está activo en Railway y testeado con watermark GPS. Las fotos de infracciones van a Cloudinary correctamente. ✅
- **Multi-municipio**: el sistema soporta múltiples municipios en la misma instancia. El primer go-live será con 1 municipio; agregar el segundo no requiere cambios de código.
- **HSTS activado**: `SECURE_HSTS_SECONDS = 31536000` con `PRELOAD = True`. Una vez que el dominio propio esté configurado con HTTPS, el navegador lo cachea por 1 año. Verificar que HTTPS funciona antes de que HSTS empiece a cachearse.
- Items de la auditoría de DB **no** cubiertos en este checklist (ya estaban en AUDITORIA_DB_2026-07-25.md): Fix 4 (remover `Estacionamiento.creado_en`), Fix 5 (índices compuestos adicionales), Fix 7 (choices en CierreCaja y SolicitudVerificacion) — baja prioridad, no bloquean go-live.
