# Checklist de paso a producción — Estacionamiento Medido (actualizado)
Fecha: 2026-09-01
Destino: municipio real con datos reales (conductores, inspectores, vendedores, admin, tesorero).
Contexto actual: Railway (demo activa con inspectores y admin reales de prueba). Deploy definitivo a Digital Ocean cuando haya un municipio pagando.

Auditorías corridas en esta sesión: seguridad ✅ · rendimiento ✅ · base de datos ✅

---

## Resumen ejecutivo

El sistema mejoró significativamente desde el checklist de julio. Los 3 bloqueantes de entonces ya están resueltos (backups GitHub Actions, HMAC MP, django-axes). Sentry, email SMTP y `mp_payment_id` único también quedaron. Lo que falta antes de un go-live real es más chico: 2 correcciones de modelo de datos (`CASCADE → SET_NULL`), 1 middleware de seguridad (contraseña forzada), limpieza de datos de prueba, y un dominio propio si el municipio lo requiere. Ninguno es complejo; el más importante es la limpieza de datos.

---

## ✅ Ya resuelto (desde checklist julio 2026)

- **Backups automáticos**: GitHub Actions corre `pg_dump` diariamente → artifact 30 días. Testeado ✅
- **HMAC-SHA256 en webhook MP**: verificación de firma activa en `views_mp.py` ✅
- **Rate limiting**: django-axes (5 intentos / 1 hora) activo ✅
- **Sentry**: activo en producción, `send_default_pii=False` ✅
- **Email SMTP**: Brevo/anymail configurado, recuperación de contraseña funciona ✅
- **`mp_payment_id` único**: `unique=True` en `MovimientoCaja` ✅
- **`VerificacionInspector` CASCADE → PROTECT**: resuelto en migración 0045 ✅ *(era item 10 del checklist anterior — confirmar si ya se aplicó)*
- **HSTS / HTTPS**: activo en producción con Railway ✅
- **Verificación de email obligatoria** (`ACCOUNT_EMAIL_VERIFICATION=mandatory` en Railway) ✅
- **Cloudinary**: fotos de infracciones en Cloudinary, testeado ✅

---

## Pendientes

### 🔴 Bloqueante (sin esto no se puede hacer go-live con datos reales)

#### 1. Limpieza de datos de prueba

El sistema tiene datos de prueba (conductores ficticios, patentes de prueba, infracciones de demo). Antes de que el municipio cargue datos reales, hay que limpiar en orden correcto por FK.

Orden exacto (las PROTECT bloquean si se intenta en otro orden):

```sql
-- Ejecutar en Railway vía `railway run python manage.py shell` o Railway DB console
DELETE FROM app_estacionamiento_notificacion;
DELETE FROM app_estacionamiento_movimientocaja;
DELETE FROM app_estacionamiento_cierrecaja;
DELETE FROM app_estacionamiento_abonoasual;
DELETE FROM app_estacionamiento_pagopublico;
DELETE FROM app_estacionamiento_infraccion;
DELETE FROM app_estacionamiento_estacionamiento;
DELETE FROM app_estacionamiento_verificacioninspector;
DELETE FROM app_estacionamiento_vehiculausuario;
DELETE FROM app_estacionamiento_vehiculo;
-- Usuarios conductores de prueba (no tocar admin/inspector/vendedor):
DELETE FROM app_estacionamiento_usuario WHERE es_conductor=True;
```

**CRÍTICO:** hacer un backup manual de Railway antes de limpiar. Después de limpiar, hacer otro backup limpio como punto de partida de producción.

---

### 🟡 Recomendado antes del go-live

#### 2. `Infraccion.subcuadra → SET_NULL` (hallazgo auditoría DB 2026-09-01)

Actualmente `CASCADE`: si se borra una subcuadra, se borran sus infracciones. Cambiar a `SET_NULL` preserva el historial contable.

Fix en `models.py`:
```python
subcuadra = models.ForeignKey(Subcuadra, on_delete=models.SET_NULL, null=True, blank=True)
```
Seguido de `python manage.py makemigrations` + `python manage.py migrate`.

---

#### 3. Middleware `ForzarCambioPasswordMiddleware` (hallazgo auditoría seguridad 2026-09-01)

El flag `cambio_password_requerido` redirige al usuario al formulario de cambio en el login, pero si el usuario escribe otra URL directamente después del login, puede saltear el cambio. Agregar middleware para bloquear cualquier URL hasta que el usuario cambie la contraseña.

Código en `app_estacionamiento/middleware.py`:
```python
from django.shortcuts import redirect

URLS_EXCLUIDAS = {"/cambiar-password/", "/logout/"}

class ForzarCambioPasswordMiddleware:
    def __init__(self, get_response):
        self.get_response = get_response

    def __call__(self, request):
        if (
            request.user.is_authenticated
            and getattr(request.user, "cambio_password_requerido", False)
            and request.path not in URLS_EXCLUIDAS
        ):
            return redirect("forzar_cambio_password")
        return self.get_response(request)
```

En `settings.py`, agregar después de `AuthenticationMiddleware`:
```python
"app_estacionamiento.middleware.ForzarCambioPasswordMiddleware",
```

---

#### 4. Validación de tamaño en foto de infracción (hallazgo auditoría seguridad 2026-09-01)

En `views_inspector.py`, `registrar_infraccion` pasa la foto sin validar tamaño ni content-type. El `ImageField` valida que sea una imagen (Pillow), pero no el tamaño. Un inspector podría subir archivos muy grandes.

Fix: antes del `crear_infraccion()`:
```python
foto = request.FILES.get("foto")
if foto:
    TIPOS_FOTO = {"image/jpeg", "image/png", "image/webp"}
    if foto.content_type not in TIPOS_FOTO:
        messages.error(request, "La foto debe ser JPG, PNG o WEBP.")
        return redirect("inspectores_verificar_vehiculo")
    if foto.size > 15 * 1024 * 1024:  # 15 MB
        messages.error(request, f"La foto pesa demasiado (máximo 15 MB).")
        return redirect("inspectores_verificar_vehiculo")
```

---

#### 5. Filtro de fechas en `dashboard_admin` (hallazgo auditoría rendimiento 2026-09-01)

Las queries de estadísticas del panel admin agregan todos los datos históricos sin filtro. Con 2+ años de datos de un municipio, serán lentas. Agregar un filtro de últimos 30 días como default (ver AUDITORIA_RENDIMIENTO_2026-09-01.md para el detalle).

---

#### 6. UptimeRobot

Si no está configurado todavía: crear una cuenta en https://uptimerobot.com (gratuito), agregar el dominio de Railway, activar notificación por email. 5 minutos de setup. Permite saber si el sistema se cae sin esperar a que alguien lo reporte.

---

### 🟢 Puede esperar (post go-live)

#### 7. `SECURE_REFERRER_POLICY`

Una línea en `settings.py`:
```python
SECURE_REFERRER_POLICY = "same-origin"
```
Sin efectos secundarios visibles. Aplicar cuando haya oportunidad.

---

#### 8. Índices compuestos en `Infraccion` y `MovimientoCaja`

Ver AUDITORIA_RENDIMIENTO_2026-09-01.md, punto 3. Aplicar antes del primer año de datos reales, no urgente en el arranque.

---

#### 9. Plan de rollback en `CLAUDE.md`

Agregar una sección en `CLAUDE.md`:
> Railway permite volver al deploy anterior desde el dashboard (Deploy → Rollbacks) en ~30 segundos. Para rollback completo (incluye BD): restaurar backup del PostgreSQL vía `railway db import`.

---

#### 10. Dominio propio (si el municipio lo requiere)

URL `estacionamiento.up.railway.app` es válida técnicamente pero no da imagen institucional. Coordinar con el municipio si necesitan subdominio propio (ej. `estacionamiento.munidemo.gob.ar`). Requiere:
- Registro de dominio o subdominio del municipio
- CNAME apuntando a Railway
- Actualizar `ALLOWED_HOSTS` y `CSRF_TRUSTED_ORIGINS` en Railway

---

## Plan de go-live

### Antes del corte (hacer en este orden)

1. Correr tests: `python manage.py test app_estacionamiento --verbosity=2` → confirmar 130+ OK.
2. Aplicar migración de `Infraccion.subcuadra → SET_NULL` + `ForzarCambioPasswordMiddleware` + validación de foto.
3. Subir a `develop` → merge a `main` → push → confirmar que Railway deploya sin error.
4. Configurar UptimeRobot si no está.
5. Backup manual de la BD de Railway antes de limpiar.
6. Limpiar datos de prueba (item 1) en orden exacto.
7. Backup manual del estado limpio (punto de partida de producción real).
8. Tag de versión: `git tag -a v1.0.0 -m "go-live — [nombre municipio]"` + `git push origin v1.0.0`.

### Smoke test (5 acciones críticas antes de abrir al municipio)

| # | Acción | Resultado esperado |
|---|--------|--------------------|
| 1 | Login como admin | Panel correcto, sin datos de prueba |
| 2 | Inspector verifica patente real | Resultado coherente |
| 3 | Conductor carga saldo via MercadoPago | Saldo acreditado, `MovimientoCaja` creado |
| 4 | Inspector labra infracción con foto | Foto en Cloudinary, ticket visible |
| 5 | Vendedor cobra infracción en efectivo | Movimiento en caja, cierre disponible |

### Si algo sale mal

- Bug sin datos comprometidos → Railway "Rollback" (~30 segundos).
- Bug con datos cargados → restaurar backup PostgreSQL + rollback del deploy.
- Criterio: si 2 o más acciones del smoke test fallan → rollback antes de abrir al municipio.

---

## Notas

- **Railway vs. Digital Ocean**: Railway Hobby (actual) no tiene SLA formal. Para un municipio con exigencia de disponibilidad o volumen alto, Digital Ocean con Droplet + Nginx + Gunicorn + PostgreSQL gestionado es más robusto. El código no cambia, solo la infraestructura.
- **Multi-municipio**: el sistema soporta múltiples municipios en la misma instancia. El primer go-live con 1 municipio no afecta la capacidad de agregar el segundo después.
- **MP sandbox → producción**: con `DEBUG=False` en Railway, `MP_SANDBOX=False` por defecto. Verificar en los logs del smoke test que los cobros van al entorno real de MP (no sandbox).
