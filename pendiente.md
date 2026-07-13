# Pendiente — Estacionamiento Proyecto

Última actualización: 2026-07-13

---

## 🔴 Alta prioridad

### 1. Dividir views.py en módulos por rol (CRÍTICO)
~3462 líneas. El tamaño actual genera corrupción recurrente en el entorno Linux y es deuda técnica crítica.
Dividir en un sprint dedicado — no mezclar con features:
- `views_admin.py`
- `views_conductor.py`
- `views_inspector.py`
- `views_vendedor.py`
- `views_tesorero.py`
- `views_auth.py` (completar_perfil, login helpers)

Mantener `views.py` como punto de entrada que importe todo, para no romper `urls.py`.

### 2. Instalar reportlab localmente
```
pip install reportlab==4.2.5
```
Ya está en `requirements.txt` — Railway lo instala automáticamente. Solo falta en el venv local.

---

## 🟡 Media prioridad

### 3. Corregir tests pre-existentes (fallas anteriores a esta sesión)
Las siguientes fallas existían antes de los cambios de hoy y no están relacionadas:

- `test_flujo_completo` / `test_no_puede_tener_dos_estacionamientos_activos` / `test_saldo_se_descuenta_al_estacionar`
  → Causa: falta `Tarifa` en el setUp del test. El estacionamiento no se crea porque no hay tarifa configurada.
  → Fix: agregar `Tarifa.objects.create(municipio=self.municipio, precio_por_hora=10)` en `BaseRolesTest.setUp()`.

- `test_conductor_no_puede_ver_panel_admin` / `test_conductor_no_puede_verificar_vehiculo`
  → Causa: la view devuelve 302 (redirect al login o panel propio) en vez de 403.
  → Fix: cambiar la aserción a `assertRedirects` o ajustar el decorator `@require_role` para devolver 403 en vez de redirigir.

- `test_renovar_extiende_duracion` / `test_renovar_descuenta_saldo` / `test_renovar_estacionamiento_ajeno_retorna_404`
  → Causa: falta `Tarifa` y falta manejo 404 en la view de renovación.

### 4. Tests faltantes (coverage incompleto)
- Abono mensual (cobro, verificación, conflicto mismo mes)
- Tolerancia multa (pagar antes vs después del período de gracia)
- Comisiones (que `comision_monto` se grabe correctamente)
- Tesorero: depositar → vendedor certifica
- Multi-municipio (datos aislados entre municipios)
- Flujo MP webhook (integración)

---

## 🟢 Baja prioridad / Futuras versiones

### 5. Evaluar migración a Digital Ocean
Railway es conveniente pero tiene limitaciones de costo/control a largo plazo.
Evaluar DigitalOcean App Platform o Droplet + Nginx + Gunicorn.
Considerar: costo mensual, PostgreSQL managed, backups, dominio propio, SSL.
**Disparador**: cuando el sistema tenga usuarios reales pagando.

### 6. Inspector: foto con watermark y GPS
Al labrar acta el inspector saca foto desde el celular con watermark (fecha, hora, GPS, patente).
`Infraccion` ya tiene campo `foto` (ImageField). Dejar para v2.

### 7. Inspector como cobrador (paid feature)
Si se activa: agregar rol "inspector" al decorator de `registrar_estacionamiento_vendedor` y `cobrar_abono`.

### 8. Mejoras OAuth y UI
- Pantalla de consentimiento Google: completar logo, descripción, dominio verificado
- Modo alto contraste / uso en exterior con sol
- Separar `settings_dev.py` / `settings_prod.py`

---

## ✅ Resuelto

- **Validación periodo en cerrar_caja**: si `periodo` llega con valor no válido (request manipulado), la view devuelve error y no crea el cierre. Fix de bug detectado por tests.
- **tests_roles.py conductor sin first_name**: `BaseRolesTest.setUp()` ahora incluye `first_name="Test"` para que el nuevo middleware no redirija los tests a `completar_perfil`.
- Inspector PDF del día: `pdf_infracciones_hoy` con reportlab — descarga PDF con acta/hora/patente/subcuadra/motivo/monto/estado; soporta `?fecha=YYYY-MM-DD`; botón "📄 PDF del día" en panel inspector
- Google OAuth nombre/apellido: middleware detecta `first_name` vacío en conductores y redirige a `completar_perfil`; el form acepta nombre/apellido + municipio de forma independiente según lo que falte
- Timer "calculando…" indefinido: `inicio_usuarios.html` estaba truncado, faltaba `setInterval`. Corregido con el bloque JS completo.
- Subcuadras vacías al registrar infracción: `get_subcuadra_default` usa `get_or_create("Zona Única")` — nunca falla.
- /usuarios/inicio/ rompe con conductor: verificado en código — la view maneja `None` municipio correctamente. Sin reproducción desde 2026-06-10.
- Selector de período al cerrar caja: modal con `<select>` diario/semanal/mensual, field `CierreCaja.periodo`, migration 0038, `generar_cierre_caja(periodo=...)`, historial muestra `get_periodo_display`
- Banner modo desarrollo: naranja sticky en `base.html`, inyectado via `modo_desarrollo = settings.DEBUG` en context processor
- Deprecation warnings allauth 65.x: eliminadas `ACCOUNT_USERNAME_REQUIRED`, `ACCOUNT_EMAIL_REQUIRED`, `ACCOUNT_AUTHENTICATION_METHOD`
- Abono mensual: selector de mes — 4 opciones (2 atrás, actual, siguiente), validación por mes elegido
- Admin-usuarios: editar teléfono, DNI, toggle es_verificado + badge en detalle
- Admin rendición a tesorería: view `crear_rendicion` + URL + template con cálculo en tiempo real
- Doble alert: `cobrar_abono.html`, `resumen_caja.html`, `panel_tesorero.html`, `rendiciones.html`
- `certificar_comision`: restaurada (estaba truncada en working copy)
- Cobrar infracciones por patente: `cobrar_infraccion_vendedor` completo y crea `MovimientoCaja`
- Tesorería rendiciones: `panel_tesorero` ya muestra `Rendicion` — template completo
- `gestionar_infracciones.html` eliminado
- `puede_estacionar_ahora()` con caché de 1 hora
- `duracion_min` → `duracion_horas` (migration 0036)
- `precio_por_hora_moto` → null=True (migration 0037)
- Procfile: `migrate --noinput` antes de `gunicorn`
- Panel inspector: solo "Infracciones hoy" + Verificar + Mis infracciones (sin dinero)
- panel_admin: sin tabla de estacionamientos; stat "Conductores registrados"
- inicio_admin: redirige a panel_admin
- detalle_usuario: doble alert eliminado, infracciones últimas 5 + "Ver todas", responsive + tipo vehículo
- CSRF: `CSRF_TRUSTED_ORIGINS=https://estacionamiento.up.railway.app` en Railway vars
- SITE_ID=2 en Railway vars (confirmado por usuario)
- Google OAuth `redirect_uri_mismatch`: nuevo cliente OAuth + URI autorizada
- Branding por municipio (logo + colores + nombre_sistema)
- Menú hamburguesa, botones sin estilo, 403.html, NoReverseMatch caja_inspector
