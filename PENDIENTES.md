# Pendientes — Estacionamiento Proyecto

Última actualización: 2026-09-01 (auditorías completas)

---

## 🗺️ Contexto de deploy

- **Railway** → ambiente de prueba (inspectores + admin testeando). No es producción municipal real.
- **Digital Ocean** → deploy definitivo cuando el sistema vaya a municipios reales pagando.
- El código es el mismo; los cambios son de infraestructura y configuración.

---

## 🔴 Alta prioridad

### ~~Inspector — bloquear todo fuera de horario~~ → ✅ resuelto (sesión 2026-08-25)
### ~~Vendedores — permiso individual para vender abonos~~ → ✅ resuelto (sesión 2026-09-01)
### ~~Perfil extendido conductor — campo domicilio~~ → ✅ resuelto (sesión 2026-09-01)
### ~~Admin panel responsive con secciones desplegables~~ → ✅ resuelto (sesión 2026-09-01)
### ~~Ícono PWA dinámico con logo del municipio~~ → ✅ resuelto (sesión 2026-09-01)
### ~~Reseteo de contraseña desde panel admin~~ → ✅ resuelto (sesión 2026-09-01)
### ~~GitHub Pages landing~~ → ✅ resuelto (sesión 2026-09-01) — archivo `landing_github_pages.html` generado

### ~~Auditorías — correr todas antes del próximo municipio real~~ → ✅ resuelto (sesión 2026-09-01)
Ver informes:
- `AUDITORIA_SEGURIDAD_2026-09-01.md`
- `AUDITORIA_RENDIMIENTO_2026-09-01.md`
- `AUDITORIA_BASE_DATOS_2026-09-01.md`
- `CHECKLIST_PRODUCCION_2026-09-01.md`

Pendientes derivados de las auditorías (ver 🟡 abajo):

---

## 🟡 Media prioridad

### Pendientes derivados de auditorías 2026-09-01

**Seguridad:**
- ~~`ForzarCambioPasswordMiddleware`~~ → ✅ resuelto (sesión 2026-09-01) — `middleware.py` + `settings.py`
- ~~Validación de tamaño/tipo en foto de infracción~~ → ✅ resuelto (sesión 2026-09-01) — `views_inspector.py`
- ~~`SECURE_REFERRER_POLICY = "same-origin"`~~ → ✅ resuelto (sesión 2026-09-01) — `settings.py`

**Rendimiento:**
- ~~`dashboard_admin`~~ → ✅ resuelto (sesión 2026-09-01) — vista implementada con template propio, URL `/admin-dashboard/`, filtro de fechas (default últimos 30 días), link en sidebar.
- ~~`estacionamientos_activos` en `panel_admin`: agregar `[:50]` como cap~~ → ✅ resuelto (sesión 2026-09-01) — `views_admin.py`

**Base de datos:**
- ~~`Infraccion.subcuadra → SET_NULL`~~ → ✅ resuelto (sesión 2026-09-01) — migración 0061
- ~~`VerificacionInspector.inspector/vehiculo/subcuadra → SET_NULL`~~ → ✅ resuelto (sesión 2026-09-01) — migración 0062, `null=True` en los 3 FK.

**Go-live:**
- Limpieza de datos de prueba de Railway antes de go-live real. Ver `CHECKLIST_PRODUCCION_2026-09-01.md` para el orden correcto.
- UptimeRobot si no está configurado todavía.

### Descuentos por pago voluntario de infracciones (feature premium por municipio)
El superadmin habilita el módulo por municipio. El admin del municipio configura:

- **Descuento por horas**: si el conductor paga dentro de X horas desde el acta → Y% de descuento
  (ej: pago en menos de 2 hs → 40% off)
- **Descuento por días**: si paga dentro de X días → Z% de descuento
  (ej: pago en menos de 5 días → 20% off)
- Fuera del plazo → monto completo

Requiere:
- Nuevos campos en `Tarifa` o tabla `ConfigDescuento`: `descuento_horas_plazo`, `descuento_horas_pct`,
  `descuento_dias_plazo`, `descuento_dias_pct` + migración
- `pagar_infraccion` use case: al calcular el monto a pagar, consulta los plazos y aplica el descuento
- `MovimientoCaja` o `Infraccion`: registrar el monto original + descuento aplicado + motivo (trazabilidad)
- Panel admin: sección "Descuentos" visible solo si el módulo está habilitado
- Panel conductor: mostrar al ver una infracción pendiente si hay descuento disponible y cuánto tiempo falta


### Reseteo de contraseña desde el panel admin
Admin hace clic en "Resetear contraseña" en la ficha del usuario → envía link de reset por email
→ el usuario debe cambiar al primer login.
Requiere:
- `cambio_password_requerido = BooleanField(default=False)` en `Usuario` + migración
- Acción en la vista de detalle de usuario (admin)
- Check en `login_view` que redirija al formulario de cambio si el flag está activo

### Comisión vendedor como feature premium
- Hoy `comision_vendedor` aplica a todos los municipios. Debería ser un módulo que el superadmin activa.
- Admin solo ve la sección "Comisiones" en tarifas si el módulo está habilitado para su municipio.
- Toggle por vendedor individual (algunos vendedores no cobran comisión).

### Perfil extendido — Vendedor
Campos nuevos en `Usuario` (requieren migración):
- `telefono_particular`, `telefono_comercial`, `domicilio_comercial` (CharField)
- `horarios_atencion` (JSONField) — días y franjas horarias de atención
- `ubicacion_lat`, `ubicacion_lon` (DecimalField) — para mapa y búsqueda del más cercano

### ~~Detección GPS de subcuadra al estacionar (conductor)~~ → ✅ resuelto (sesión 2026-09-01)
Hoy el conductor estaciona y el sistema le asigna la subcuadra default del municipio (`get_subcuadra_default()`).
Mejorar el flujo:
1. Al abrir "Estacionar vehículo" → pedir permiso de geolocalización del browser
2. Si acepta → endpoint `GET /api/subcuadra-cercana/?lat=X&lon=Y` busca la Subcuadra con menor distancia a esas coordenadas (lat/lon ya existen en el modelo) → pre-selecciona en un `<select>`
3. Si deniega o cierra el diálogo → `<select>` de subcuadras disponible para elección manual
4. "Estacionar sin indicar zona" → usa la subcuadra default (comportamiento actual)

Cambios necesarios:
- Nuevo endpoint `subcuadra_cercana` (view + URL) — distancia sin dependencias externas
- `views_conductor.estacionar_vehiculo` acepta `subcuadra_id` del POST (hoy ignora y usa default)
- JS en `estacionar_vehiculo.html`: `navigator.geolocation`, fetch al endpoint, poblar select
- Tres estados de UI: detectando / selección manual / sin informar


### ~~Tesorero como fallback para certificar cierres de admin~~ → ✅ resuelto (sesión 2026-09-01)
`certificar_cierre` ahora acepta `@require_role("admin", "tesorero")`. Guard: tesorero solo certifica cierres de admins (`es_admin=True`). Redirect dinámico por rol. Sección nueva en `panel_tesorero.html` mostrando los cierres pendientes con botón "Certificar".

### Cierre de caja configurable por período
- Frecuencia esperada configurable (diaria/semanal/mensual) por municipio o por vendedor.
- Semáforo en panel admin: vendedores atrasados en cerrar caja.
- Admin puede forzar el cierre de un vendedor (ausencia o imprevisto).

### Panel de auditoría del superadmin
Vista global: total recaudado/rendido/pendiente por municipio.
(El panel de auditoría interno del admin ya está: `auditoria_staff`)


### Reportes de subcuadras (dashboard de cobertura)
Dashboard por subcuadra: verificaciones / infracciones / vehículos exentos en el período.
Datos ya existen: `VerificacionInspector` + `Infraccion` + `Vehiculo.subcuadras_exentas`.

---

## 🟢 Baja prioridad / Futuras versiones

### Módulo: Reintegro para residentes verificados (feature premium por municipio)

**Concepto:** el conductor registra su domicilio, el admin lo verifica como residente del municipio,
y a partir de entonces los primeros X minutos de cada estacionamiento se acreditan como saldo.
Es un beneficio que el municipio ofrece a sus vecinos para incentivar el uso del sistema.
Se implementa como módulo premium que el superadmin activa por municipio — cualquier municipio puede ofrecerlo.

**Modelo de datos** (requieren migración):
- `Usuario.domicilio` ✅ ya existe (migración 0059, 2026-09-01)
- `Usuario.es_residente_verificado` (BooleanField, default=False) — admin lo activa/desactiva
- `Usuario.fecha_verificacion_residencia` (DateField, null=True) — cuándo se verificó
- Configuración del módulo (en la entrada `ModuloMunicipio` o en `Municipio`):
  - `reintegro_minutos` — minutos a reintegrar por estacionamiento (ej: 30)
  - `reintegro_max_por_dia` — límite de reintegros por conductor por día (ej: 1, para evitar abuso)

**Lógica** en `ejecutar_estacionamiento` (use case), al final, post-creación:
```python
if conductor.es_residente_verificado and modulo_activo("reintegro_residentes", municipio):
    reintegros_hoy = contar_reintegros_hoy(conductor)
    if reintegros_hoy < municipio.reintegro_max_por_dia:
        monto = (tarifa.precio_por_hora / 60) * municipio.reintegro_minutos
        acreditar_saldo(conductor, monto, concepto="reintegro_residencia")
        # Crea MovimientoCaja tipo='reintegro_residencia' con monto positivo
```

**Contabilidad:**
- `MovimientoCaja.tipo` nuevo valor: `'reintegro_residencia'`
- Es un egreso para el municipio (reduce recaudación neta) → visible en reportes del tesorero
- Aparece en el historial del conductor como "Reintegro vecino verificado"

**Admin UX:**
- Ficha del conductor: campo domicilio + botón "Verificar como residente" + fecha de verificación
- Lista de residentes verificados en panel admin
- Panel superadmin: activar módulo + configurar minutos y límite diario por municipio

**Landing y marketing:**
- Sección "Beneficios para vecinos": destacar reintegro como diferenciador
- Requisito: domicilio registrado y verificado por el municipio (domicilio electrónico)
- Otros beneficios a destacar: pago desde celular, historial, sin efectivo, notificaciones


### Responsive > 1050px
En pantallas grandes el layout del panel admin queda con mucho espacio vacío.

### Migración a Digital Ocean (producción municipal real)
**Disparador**: cuando el sistema pase de pruebas a municipio real pagando.
Ver checklist: `CHECKLIST_PRODUCCION_2026-07-25.md`.

### Inspector como cobrador (configurable por municipio)
Toggle por superadmin via `ModuloMunicipio`.

### Transferencia de saldo entre usuarios
`TransferenciaSaldo` (emisor, receptor, monto, estado). Receptor tiene 24h para aceptar.

### Reconocimiento de patente por cámara (OCR)
Google ML Kit o Tesseract.js. Botón "📷 Escanear" en `verificar.html`.

### Alertas de vencimiento al conductor (push / WhatsApp)

### Mapa de calor de infracciones
Leaflet.js + lat/lon de subcuadras (coordenadas ya en el modelo).

### Módulo de impugnaciones
`Impugnacion` (infraccion, conductor, motivo, evidencia, estado). Admin resuelve desde panel.

### Dashboard en TV (pantalla municipal en tiempo real)
Vista sin login con token de solo lectura. Auto-refresh cada 60s.

### Toggle estadísticas de inspectores por municipio
`Municipio.estadisticas_inspectores_activo = BooleanField(default=True)`. 1 migración, 1 chequeo.

### Tutorial de uso — GIFs en landing pública
El tutorial por rol ya está dentro del sistema (collapsible `<details>` en cada panel).
Pendiente: versión con GIF animado o screenshots para la landing pública.

---

## ✅ Resuelto recientemente

**Sesión 2026-08-25** — Migración SIA titular + bloqueo inspector fuera de horario:
- Migración `sia_titular_fields_vehiculo` generada y aplicada localmente. Railway la aplica en el próximo deploy a main. ✅


- `verificar_vehiculo` view: `puede_estacionar_ahora()` se evalúa ANTES del POST. Si está fuera de horario, el POST se ignora y se devuelve el template con banner. ✅
- `verificar.html`: form y selector de patente no se renderizan fuera de horario. Banner ⏰ con `mensaje_horario`. JS con guard `if (form && input)` para no fallar cuando los elementos no existen. Historial oculto fuera de horario. ✅

**Sesión 2026-08-24 (tarde)** — Tarifas click-to-edit, login UX, lockout reset link:
- Login: `login_view` detecta tipo de error y lo pasa al template (`correo_no_encontrado`, `password_incorrecta`, `cuenta_inactiva`, `campos_vacios`). `<details>` se abre automáticamente. Input borde rojo en campo fallido. Correo se pre-carga. ✅
- Lockout: botón "🔑 Restablecer contraseña" → `/accounts/password/reset/`. ✅
- Tarifas refactorizadas a 7 secciones individuales (una por campo). Cada POST actualiza un solo valor. ✅
- Tarifas click-to-edit: modo lectura por defecto, ✏️ Editar abre input inline, confirmación muestra solo ese campo (valor viejo → nuevo). Dialog centrado correctamente con `position:fixed + transform`. ✅
- Partial `admin/_campo_tarifa.html` reutilizable. ✅
- Test actualizado: secciones individuales + verificación de aislamiento entre campos. ✅

**Sesión 2026-08-24 (mañana)** — SIA parser v2, titular SIA, sidebar agrupado, exenciones unificadas:
- SIA parser: fix raíz — ANDIS usa `<th>` en encabezados. Si hay `<th>` → Strategy B. 38 tests OK. ✅
- `ResultadoSia` con `nombre`, `apellido`, `documento` separados. Parser extrae DNI del titular. ✅
- `Vehiculo`: campos `sia_titular_nombre`, `sia_titular_apellido`, `sia_titular_dni`, `sia_nci`. Migración pendiente. ✅
- `views_inspector.verificar_sia`: guarda nombre, apellido, DNI y NCI al verificar SIA válido. ✅
- Modal inspector: botón "↩ Verificar otro" + auto-reset a los 5s si SIA fue exitoso. ✅
- Sidebar admin agrupado en 4 rubros: Personal · Vehículos · Configuración · Caja y rendiciones. ✅
- Exenciones unificadas: badge "♿ SIA · ANDIS" en búsqueda y lista global con nombre, DNI, vigencia coloreada. ✅

**Sesión 2026-08-23** — Dark mode, responsive, SIA parser fix inicial, auditoría staff, cierre de caja admin:
- Dark mode toggle en navbar (persiste en `localStorage`). FOUC prevention. `--color-acento`. ✅
- `Municipio.color_acento` (migración 0055). Superadmin configura 3 colores. ✅
- Responsive completo: doble padding fix, grid admin colapsable, tablas con overflow-x. ✅
- `auditoria_staff`: vista unificada admin con vendedores e inspectores. URL `admin-staff/`. ✅
- Cierre de caja para rol admin: URL `admin/cerrar-caja/`. ✅

**Sesión 2026-08-21** — OAuth account takeover + SIA ANDIS + bloqueo fuera de horario:
- `adapters.py`: `pre_social_login()` bloquea auto-connect si el email ya existe sin cuenta Google. ✅
- `services/sia_verificacion.py`: verificación SIA contra ANDIS. Validación SSRF, parseo HTML, 8 estados. ✅
- `models.py`: campos `sia_*` en `Infraccion` (migración 0054). ✅
- `views_inspector.py`: bloquea infraccionamiento fuera del horario de cobro. ✅

**Sesión 2026-08-18/20** — MercadoPago, backups, seguridad, email, tarifas:
- Pago público sin registro: `PagoPublico` (migración 0051), webhook, 4 templates. ✅
- Backups PostgreSQL: workflow GitHub Actions diario → artifact 30 días. Restore testado. ✅
- Email transaccional (Brevo/anymail): recuperación de contraseña funcionando. ✅
- `django-axes`: lockout combinado IP+usuario, 5 intentos, 1h cooloff. ✅
- Verificación de email obligatoria en Railway (`ACCOUNT_EMAIL_VERIFICATION=mandatory`). ✅
- Límites de carga MercadoPago configurables por municipio (migración 0052). ✅
- `gestionar_tarifas`: fix `MultipleObjectsReturned`, auto-limpia duplicados. ✅
- 160 tests, todos OK. ✅

**Sesiones 2026-08-13/19** — GPS, subcuadras, superadmin, impresora BLE, rendiciones:
- `Subcuadra.lat/lon` + endpoint GPS. ✅
- Superadmin `editar_municipio`: logo, colores, `leyenda_horarios`, `texto_ordenanza` (migraciones 0053). ✅
- Importación de exenciones desde Excel. ✅
- `PlantillaDocumento` (5 tipos de comprobante personalizables). ✅
- Impresora BLE: persistencia en `localStorage`, doble copia automática, QR nativo ESC/POS. ✅
- Rendiciones: PDF, tesorero valida/observa, `LiquidacionComision` con factura. ✅
- PWA icons reales (192, 512, apple-touch). ✅
