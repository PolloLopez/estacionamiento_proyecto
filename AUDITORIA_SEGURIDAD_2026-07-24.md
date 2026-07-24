# Auditoría de seguridad — Sistema de Estacionamiento
Fecha: 2026-07-24  
Exposición evaluada: **producción activa** (Railway, https://estacionamiento.up.railway.app)  
Stack auditado: Django 5.2 / Python 3.12 / PostgreSQL / Cloudinary / MercadoPago

---

## Resumen ejecutivo

El sistema tiene una base sólida: `require_role` cubre todas las vistas de rol, los checks de ownership (filtrar por `municipio`, `usuario`, etc.) están presentes en todos los endpoints con IDs en la URL, CSRF está activo, los secretos están en variables de entorno y el `.env` no se commitea.

Los cuatro hallazgos más importantes son: el webhook de MercadoPago no verifica la firma que MP envía en el header (cualquier bot puede hacer POST al endpoint), el registro de conductores no requiere verificación de email (riesgo de cuentas masivas falsas), los archivos que sube el conductor no tienen validación de tipo ni tamaño, y el login manual no tiene rate limiting. Ninguno es catastrófico hoy, pero todos merecen atención antes de escalar a más municipios.

---

## Hallazgos

### 🟡 Media prioridad

**1. Webhook de MercadoPago sin verificación de firma**

- **Dónde:** `views_mp.py` → `mp_webhook` (línea 224, `@csrf_exempt`)
- **Qué puede pasar:** Cualquier bot externo puede hacer POST a `/mp/webhook/` con un payload `{"type": "payment", "data": {"id": "123"}}`. El endpoint responde 200 siempre (para no gatillar reintentos de MP) y hace una query a la API de MP por cada request. El riesgo de double-credit está mitigado por la idempotencia en `acreditar_saldo_mp`, pero la idempotencia se basa en `descripcion__contains=f"MP:{payment_id}"` (ver hallazgo 4 en 🟢). Si esa lógica falla, un bot podría gatillar una acreditación duplicada.
- **Fácil de explotar:** Sí, con un simple `curl -X POST`.
- **Fix:** MercadoPago envía un header `x-signature` en cada webhook. Verificarlo antes de procesar:
  ```python
  # En mp_webhook, antes de parsear data:
  import hmac, hashlib
  secret = settings.MP_WEBHOOK_SECRET  # variable de entorno nueva
  xsig   = request.headers.get("x-signature", "")
  xreqid = request.headers.get("x-request-id", "")
  manifest = f"id={data.get('data', {}).get('id', '')};request-id={xreqid};"
  digest = hmac.new(secret.encode(), manifest.encode(), hashlib.sha256).hexdigest()
  if not hmac.compare_digest(digest, xsig.split("ts=")[1].split(",")[0]):
      return HttpResponse(status=400)
  ```
  Requiere agregar `MP_WEBHOOK_SECRET` en Railway y al endpoint de notificación en la configuración de MP.

---

**2. Registro de conductores sin verificación de email**

- **Dónde:** `settings.py` línea 228: `ACCOUNT_EMAIL_VERIFICATION = "none"`; `views_auth.py` → `registro_view`
- **Qué puede pasar:** Cualquiera puede crear cuentas de conductor con cualquier email (incluyendo emails ajenos o inexistentes). Combinado con que las cuentas arrancan sin saldo, el riesgo inmediato es bajo — pero si el municipio decide dar saldo inicial o crédito a conductores nuevos, esto abre la puerta a fraude masivo. También: alguien puede registrar el email de otra persona y empezar a "usar" la cuenta en su nombre.
- **Fácil de explotar:** Sí, con un script básico.
- **Fix:** Activar verificación: `ACCOUNT_EMAIL_VERIFICATION = "mandatory"`. Requiere que el flujo de email funcione (ya está configurado en Railway), y que allauth tenga la plantilla de verificación. El flujo de allauth ya maneja esto automáticamente cuando la verificación está activada. Impacto: los conductores nuevos no pueden hacer nada hasta confirmar su email.

---

**3. Archivos subidos por el conductor sin validación de tipo ni tamaño**

- **Dónde:** `views_conductor.py` → `solicitar_verificacion`, líneas 204-205: `doc1 = request.FILES.get("documento_1")` y `doc2 = request.FILES.get("documento_2")`
- **Qué puede pasar:** Se acepta cualquier tipo de archivo (`.exe`, `.html`, `.php`, etc.) y cualquier tamaño. En producción van a Cloudinary (que tiene sus propias restricciones), pero el código no limita nada antes de pasarlos. En local van al filesystem sin restricción. Un usuario puede subir archivos muy grandes y saturar ancho de banda o almacenamiento.
- **Fácil de explotar:** Sí.
- **Fix:**
  ```python
  TIPOS_PERMITIDOS   = {"image/jpeg", "image/png", "image/webp", "application/pdf"}
  TAMAÑO_MAX_BYTES   = 10 * 1024 * 1024  # 10 MB
  
  def _validar_documento(archivo):
      """Retorna None si es válido, o string con el error."""
      if archivo.content_type not in TIPOS_PERMITIDOS:
          return "Solo se permiten imágenes JPG, PNG, WEBP o PDF."
      if archivo.size > TAMAÑO_MAX_BYTES:
          return "El archivo no puede superar 10 MB."
      return None
  ```
  Llamar antes de guardar en el modelo. Funciona igual en local y Cloudinary.

---

**4. Sin rate limiting en el login manual**

- **Dónde:** `views_auth.py` → `login_view` (usa `authenticate()` de Django directamente, sin ninguna capa de limitación de intentos)
- **Qué puede pasar:** Un atacante puede intentar contraseñas contra cualquier cuenta sin límite. Las contraseñas del sistema siguen las reglas de validación de Django en producción (`MinimumLengthValidator`, etc.), pero las cuentas de inspectores y vendedores las crea el admin y pueden ser débiles.
- **Fácil de explotar:** Sí, con un script de diccionario.
- **Fix más simple:** Usar `django-axes` (2 líneas en `INSTALLED_APPS` y `MIDDLEWARE`, más la migración). Bloquea IPs después de N intentos fallidos:
  ```
  pip install django-axes
  # INSTALLED_APPS += ["axes"]
  # MIDDLEWARE: insertar "axes.middleware.AxesMiddleware" después de SecurityMiddleware
  # AXES_FAILURE_LIMIT = 5
  # AXES_COOLOFF_TIME = 1  # hora
  ```
  Alternativa si no querés más dependencias: usar el campo de allauth que sí tiene rate limiting y redirigir todo el login a allauth.

---

### 🟢 Baja prioridad

**5. Sesiones sin expiración**

- `ACCOUNT_SESSION_REMEMBER = True` sin `SESSION_COOKIE_AGE` configurado → las sesiones duran hasta que Django las limpie de la base (si no se corre `clearsessions`). En un dispositivo compartido (tablet de inspector), una sesión olvidada persiste indefinidamente.
- **Fix:** Agregar en settings: `SESSION_COOKIE_AGE = 43200` (12 horas). No rompe nada; allauth respeta este valor.

---

**6. ALLOWED_HOSTS cae a `["*"]` si la variable de entorno no está**

- `settings.py` línea 27: `ALLOWED_HOSTS = _allowed.split(",") if _allowed else ["*"]`
- Si se despliega en un nuevo entorno sin configurar `ALLOWED_HOSTS`, queda `["*"]`, que permite host spoofing (Django acepta requests con cualquier header `Host:`, lo que puede afectar links generados, CSRF origins, etc.).
- **Fix menor:** Cambiar el fallback de `["*"]` a `["localhost", "127.0.0.1"]` para que en un deploy sin configurar falle ruidosamente en lugar de quedar inseguro silenciosamente:
  ```python
  ALLOWED_HOSTS = _allowed.split(",") if _allowed else (["*"] if DEBUG else ["localhost"])
  ```

---

**7. URL duplicada `ticket-pago-multa` en `urls.py`**

- Aparece definida dos veces: línea 52 (sección INSPECTORES) y línea 125 (sección COMPROBANTES). Django usa la primera definición que matchea; la segunda es ignorada pero puede generar confusión al hacer mantenimiento (ej. alguien modifica la de la línea 125 pensando que tiene efecto).
- **Fix:** Eliminar la segunda definición (línea 125).

---

**8. Idempotencia de acreditación MP basada en texto libre**

- `acreditar_saldo_mp.py` línea 33: `MovimientoCaja.objects.filter(descripcion__contains=f"MP:{payment_id}").exists()` — si el formato del campo `descripcion` cambia en el futuro (ej. alguien lo traduce o reformatea), la idempotencia deja de funcionar y un mismo pago podría acreditarse dos veces.
- **Fix:** Agregar campo `mp_payment_id = models.CharField(max_length=50, null=True, blank=True, unique=True)` a `MovimientoCaja` y usarlo para la verificación de idempotencia en lugar del string. Requiere migración y actualizar `acreditar_saldo_mp.py`.

---

## Qué está bien (no tocar)

- **`require_role` + ownership checks en todas las vistas con IDs:** `pagar_infraccion`, `eliminar_vehiculo`, `marcar_notificacion_leida`, `finalizar_estacionamiento`, `renovar_estacionamiento`, `cargar_saldo`, `editar_inspector`, `editar_vendedor`, `validar_rendicion`, `depositar_comision`, `ticket_infraccion`, `ticket_cobro`, `ticket_pago_multa` — todos filtran correctamente por `usuario` o `municipio` antes de devolver/modificar datos. Sin IDORs detectables.
- **MercadoPago `mp_exitoso` no confía en los parámetros GET** — consulta la API de MP con el `payment_id` y verifica que `usuario_id_mp == request.user.id`. Correcto.
- **CSRF activo con cookies seguras en producción** — `CsrfViewMiddleware` en la cadena, `CSRF_COOKIE_SECURE = True` cuando `DEBUG=False`.
- **HSTS configurado** — `SECURE_HSTS_SECONDS = 31536000` con subdominios y preload. Correcto para Railway.
- **Secretos en variables de entorno** — `SECRET_KEY`, `MP_ACCESS_TOKEN`, credenciales Cloudinary, DB, Google OAuth: todos via `os.getenv()`. El `.env` está en `.gitignore`.
- **ORM Django para todas las queries** — No se encontró SQL crudo concatenado con input del usuario.
- **Logout solo por POST** — Previene logout involuntario por links maliciosos.
- **Django admin en `/sistema-interno/`** — URL no obvia reduce exposición al bruteforce del admin de Django.
- **Dependencias actualizadas** — Django 5.2.8, allauth 65.x, Pillow 12, Cloudinary 1.41. Sin versiones notoriamente vulnerables.

---

## Plan de acción incremental

| # | Hallazgo | Esfuerzo | Riesgo de aplicarlo |
|---|----------|----------|---------------------|
| 1 | Rate limiting en login (`django-axes`) | 30 min | Bajo — configurar AXES_FAILURE_LIMIT para no bloquear al admin |
| 2 | Validación de tipo/tamaño en uploads de verificación | 1 hora | Ninguno |
| 3 | Firma de webhook MP (`x-signature`) | 2 horas | Requiere agregar `MP_WEBHOOK_SECRET` a Railway; testear con sandbox |
| 4 | `SESSION_COOKIE_AGE = 43200` | 5 min | Bajo — usuarios con sesión abierta van a necesitar re-loguear |
| 5 | `ALLOWED_HOSTS` fallback más seguro | 5 min | Ninguno |
| 6 | Eliminar URL duplicada en urls.py | 5 min | Ninguno |
| 7 | Campo `mp_payment_id` único en `MovimientoCaja` | 1 hora | Requiere migración; testear en staging antes de producción |
| 8 | Verificación de email al registrarse | 2-3 horas | Medio — cambiar a `mandatory` requiere revisar las plantillas de allauth y el flujo de alta de usuarios por admin |

Los puntos 4, 5 y 6 son cambios de una línea cada uno — entran en el próximo commit sin riesgo.  
Los puntos 1 y 2 son los de mayor relación esfuerzo/impacto para hacer pronto.  
El punto 3 (firma MP) requiere un `MP_WEBHOOK_SECRET` nuevo en Railway; documentar en `CONTEXT.md` cuando se implemente.  
El punto 8 (verificación de email) afecta el flujo de onboarding — no hacerlo en el mismo commit que el resto; es un feature separado.

---

## Notas

- No se auditó la configuración interna de Cloudinary (permisos de carpeta, signed uploads vs unsigned). Si las fotos de infracciones son sensibles (patentes + datos de conductor), vale la pena revisar que no sean de acceso público sin autenticación de Cloudinary.
- El sistema no tiene frontend React separado — toda la UI es server-rendered con templates Django, por lo que no aplica auditoría de CORS ni de fetch/axios.
- No se auditaron los templates HTML para XSS. Django auto-escapa por defecto en templates; el riesgo es bajo salvo que haya uso de `{{ variable | safe }}`. Una pasada rápida con `grep -r "| safe"` en `/templates/` sería suficiente para confirmar.
