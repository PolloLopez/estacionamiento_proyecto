# Auditoría de seguridad — Estacionamiento Proyecto
Fecha: 2026-09-01
Exposición evaluada: Railway (demo activa con inspectores y admin). No es producción municipal real todavía.

---

## Resumen ejecutivo

El sistema está en buen estado de seguridad para ser un sistema en demo. La configuración de producción (secretos en variables de entorno, CSRF, HSTS, rate limiting con django-axes, aislamiento por municipio) es sólida. No se encontraron vulnerabilidades críticas ni credenciales expuestas. Los dos hallazgos más relevantes son menores: la feature de "contraseña temporal forzada" puede ser salteada navegando directamente a otra URL post-login, y las fotos de infracción que sube el inspector no tienen límite de tamaño. Ambos son corregibles con cambios pequeños y de bajo riesgo.

---

## Lo que está bien ✅

Esto no es cortesía — es parte del informe, para saber qué no tocar:

- **SECRET_KEY, DATABASE_URL y claves MP/Cloudinary**: todas vía variables de entorno. Si faltan en producción, el sistema falla en el arranque con `ImproperlyConfigured` (no silencia el error).
- **DEBUG**: controlado por env var, default `True` solo localmente. En Railway se setea `False` explícitamente.
- **ALLOWED_HOSTS**: `["*"]` solo cuando `DEBUG=True`. En prod requiere env var.
- **CSRF**: activo en todo el sistema. `@csrf_exempt` aparece únicamente en `mp_webhook`, que es correcto (MercadoPago no puede enviar tokens CSRF) y está compensado con verificación HMAC-SHA256.
- **Tenant isolation**: todas las queries del panel admin filtran por `municipio=request.user.municipio`. Revisado en `views_admin.py` y `views_inspector.py` — todos los `get_object_or_404` incluyen el filtro de municipio.
- **Autorización**: el decorador `require_role()` chequea autenticación y rol en un solo paso, y devuelve 403 sin exponer información. Todas las vistas tienen el decorador correcto.
- **Rate limiting**: django-axes configurado (5 intentos fallidos por IP+correo, lockout 1 hora).
- **Sesión**: 12 horas de expiración. Cookies con `Secure` y `HttpOnly` en producción.
- **HSTS**: 1 año + subdominios + preload en producción.
- **No hay SQL crudo**: ORM usado en todo el sistema. Grep de `cursor.execute` y `raw(` sin resultados.
- **Sentry**: activo solo en producción, `send_default_pii=False`.
- **Admin Django**: movido a `/sistema-interno/` (URL no obvia, reduce bruteforce de bots).
- **Documentos de verificación/exención**: `_validar_documento()` en `views_conductor.py` valida content-type (whitelist: JPEG, PNG, WEBP, PDF) y tamaño (máx 10 MB) antes de guardar.

---

## Hallazgos

### 🟡 Media prioridad

#### 1. `forzar_cambio_password` se puede saltear

**Qué es:** cuando el admin establece una contraseña temporal para un conductor, activa el flag `cambio_password_requerido=True`. En el `login_view`, si el flag está activo, se redirige al usuario a `/cambiar-password/`. Pero el usuario ya está autenticado en ese punto. Si navega directamente a `/inicio/` u otra URL, accede a su panel sin cambiar la contraseña.

**Qué puede hacer alguien con eso:** un conductor puede evitar indefinidamente el cambio de contraseña temporal. El admin que la asignó conoce esa contraseña temporal — hay un "secreto compartido" que debería ser transitorio pero no lo es mientras el usuario no cambie. En un municipio real, esto es un problema de compliance menor pero real.

**Qué tan fácil es:** trivial. Alcanza con escribir cualquier URL del sistema después del redirect.

**Fix propuesto:** agregar un middleware o un decorador `@require_password_change` que, para cualquier vista que no sea `forzar_cambio_password` o `logout`, redirija al usuario si tiene el flag activo. El middleware es más robusto porque cubre todas las vistas sin tener que acordarse de decorar cada una.

Ejemplo de middleware (en `middleware.py`, 15 líneas):
```python
from django.shortcuts import redirect
from django.urls import reverse

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

Agregar en `settings.py` (dentro de `MIDDLEWARE`, después de `AuthenticationMiddleware`):
```python
"app_estacionamiento.middleware.ForzarCambioPasswordMiddleware",
```

**Costo:** bajo. No afecta sesiones activas existentes ni requiere migración.

---

#### 2. Foto de infracción sin validación de tamaño

**Qué es:** en `views_inspector.py`, la foto que sube el inspector al registrar una infracción pasa directamente a `crear_infraccion()` sin validar content-type ni tamaño:
```python
foto=request.FILES.get("foto"),  # ← sin validación
```

El `ImageField` de Django valida (vía Pillow) que el archivo sea una imagen real, pero no limita el tamaño. Un inspector podría subir una imagen de 50 MB sin que el sistema lo rechace.

**Qué puede hacer alguien con eso:** un inspector malicioso (o un celular que genera imágenes muy grandes) puede llenar el storage de Cloudinary más rápido de lo esperado. No es un vector de acceso a datos ajenos, pero puede generar costos o degradar el servicio.

**Qué tan fácil es:** requiere ser inspector autenticado. La surface es chica.

**Fix propuesto:** agregar la misma validación que ya existe para documentos de exención. En `views_inspector.py`, antes de llamar a `crear_infraccion`:
```python
from .views_conductor import _validar_documento  # reusar la función existente

foto = request.FILES.get("foto")
if foto:
    # Sobreescribir tipos permitidos: solo imágenes (no PDF) para fotos de infracción
    TIPOS_FOTO = {"image/jpeg", "image/png", "image/webp"}
    TAMAÑO_MAX = 15 * 1024 * 1024  # 15 MB (más generoso para fotos de cámara)
    if foto.content_type not in TIPOS_FOTO:
        messages.error(request, "La foto debe ser JPG, PNG o WEBP.")
        return redirect("inspectores_verificar_vehiculo")
    if foto.size > TAMAÑO_MAX:
        messages.error(request, f"La foto pesa {foto.size/1024/1024:.1f} MB; máximo 15 MB.")
        return redirect("inspectores_verificar_vehiculo")
```

Nota: si se prefiere evitar el import cruzado entre módulos, mover `_validar_documento` a `services/archivos.py` o similar y que ambas vistas la importen desde ahí.

**Costo:** bajo.

---

### 🟢 Baja prioridad

#### 3. Django admin sin segundo factor de autenticación

**Qué es:** `/sistema-interno/` usa la URL no obvia, que es buena práctica. Pero si alguien obtiene las credenciales de un superadmin, accede directo sin segundo factor.

**Qué puede hacer alguien con eso:** acceso completo a todos los datos del sistema vía el admin de Django.

**Por qué no es urgente ahora:** django-axes ya limita bruteforce. La surface de ataque es pequeña (solo superadmins conocen la URL y tienen credenciales). En demo Railway, el riesgo es bajo.

**Para producción municipal real:** considerar `django-otp` o `django-two-factor-auth` para agregar TOTP al admin de Django. O directamente restringir el admin a IPs de oficina con `INTERNAL_IPS` o un firewall de Railway.

---

#### 4. Sin header `Referrer-Policy`

**Qué es:** Django no configura `Referrer-Policy` por defecto. El browser envía la URL completa de la página anterior en el header `Referer` de cada request, incluyendo URLs internas del sistema.

**Qué puede hacer alguien con eso:** en un sistema con datos sensibles, una URL interna podría filtrar info (ej. `/admin-usuarios/42/` revela que hay un usuario con ID 42). Para el sistema actual, el riesgo concreto es bajo.

**Fix:** una línea en `settings.py`:
```python
SECURE_REFERRER_POLICY = "same-origin"
```

**Costo:** mínimo. Django 4.0+ lo soporta de fábrica.

---

#### 5. Sin Content Security Policy (CSP)

**Qué es:** no hay header `Content-Security-Policy`. El riesgo real de XSS es bajo en este sistema porque usa templates de Django (que auto-escapan) y no ejecuta JS de fuentes externas no confiables. Pero si en el futuro se agrega integración de terceros (Google Analytics, chat, etc.), la ausencia de CSP amplía la superficie.

**Por qué no es urgente ahora:** el sistema no tiene contenido generado por usuarios que se renderice como HTML sin escapar. Django templates hacen `{{ variable }}` → escape automático.

**Para producción municipal:** considerar agregar `django-csp` con una política básica cuando llegue el momento. No es prioritario para la demo actual.

---

## Plan de acción incremental

En orden de prioridad, riesgo de aplicar cada uno y esfuerzo estimado:

1. **Middleware `ForzarCambioPasswordMiddleware`** — 20 líneas de código + 1 línea en `settings.py`. Sin migración. Bajo riesgo. Hacerlo antes del próximo go-live real.

2. **Validación de foto en inspector** — 8 líneas adicionales en `views_inspector.py`. Bajo riesgo. Hacerlo antes del próximo go-live real.

3. **`SECURE_REFERRER_POLICY = "same-origin"`** — 1 línea en `settings.py`. Sin efectos secundarios visibles. Se puede aplicar en cualquier momento.

4. **2FA en admin Django** — requiere instalar una dependencia (`django-otp` o similar) y configurar el flujo. Hacerlo en el momento de migración a Digital Ocean, antes del go-live con municipio real pagando.

5. **CSP** — post go-live, cuando el sistema esté estable y se conozca la lista definitiva de recursos externos usados.

---

## Notas

- No se tuvo acceso directo al entorno de Railway en producción para revisar variables de entorno reales, logs o configuración de la instancia. Se auditó el código y la configuración en el repo.
- La feature de pago público (`/pagar/`) es intencionalmente sin autenticación — no es un hallazgo, es parte del diseño para que ciudadanos sin cuenta puedan pagar infracciones.
- La verificación de SIA (ANDIS) incluye validación SSRF en `services/sia_verificacion.py` — no se profundizó en esa lógica, pero el sistema ya tenía ese punto en la checklist de la auditoría anterior.
