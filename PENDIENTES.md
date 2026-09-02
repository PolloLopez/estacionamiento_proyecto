# Pendientes — Estacionamiento Proyecto

Última actualización: 2026-09-01 (todos los ítems 🟢 implementados)

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

> Todo el backlog de sesiones anteriores está resuelto. Solo quedan dos ítems de infraestructura:

- **Limpieza de datos de prueba** de Railway antes del go-live con un municipio real. Ver `CHECKLIST_PRODUCCION_2026-09-01.md`.
- **UptimeRobot**: configurar monitoreo de uptime si no está activo todavía.

---

### ✅ Resuelto en sesiones anteriores (referencia rápida)

| Ítem | Migración / archivo | Sesión |
|---|---|---|
| ForzarCambioPasswordMiddleware | `middleware.py` + `settings.py` | 2026-09-01 |
| Validación foto infracción | `views_inspector.py` | 2026-09-01 |
| `SECURE_REFERRER_POLICY` | `settings.py` | 2026-09-01 |
| `dashboard_admin` con filtro fechas | `views_admin.py`, URL `/admin-dashboard/` | 2026-09-01 |
| Cap `[:50]` estacionamientos activos | `views_admin.py` | 2026-09-01 |
| `Infraccion.subcuadra → SET_NULL` | migración 0061 | 2026-09-01 |
| `VerificacionInspector` FK → SET_NULL | migración 0062 | 2026-09-01 |
| Reseteo de contraseña desde admin | `views_admin.py detalle_usuario_admin` + middleware | 2026-09-01 |
| Descuentos voluntarios de infracciones | migración 0063, `services/infracciones.py`, `pagar_infraccion.py` | 2026-09-01 |
| Comisión vendedor como módulo premium | `MODULOS` + `gestionar_tarifas.html` condicional | 2026-09-01 |
| Perfil extendido vendedor | migración 0064: `domicilio_comercial`, `ubicacion_lat/lon` | 2026-09-01 |
| Cierre de caja configurable por período | migración 0064: `frecuencia_cierre_caja`, vistas `caja_vendedores` + `forzar_cierre_vendedor` | 2026-09-01 |
| GPS de subcuadra al estacionar | endpoint `subcuadra_cercana`, JS en `estacionar_vehiculo.html` | 2026-09-01 |
| Tesorero certifica cierres de admin | `views_admin.py`, `panel_tesorero.html` | 2026-09-01 |
| Panel auditoría superadmin | `views_superadmin.py auditoria_superadmin`, `/superadmin/auditoria/` | 2026-09-01 |
| Reportes de subcuadras (cobertura) | `views_admin.py reportes_subcuadras`, `/admin-subcuadras/reportes/` | 2026-09-01 |
| Módulo reintegro residentes | migración 0065, `services/reintegro.py`, `Reintegro` model, config en superadmin + verificación en detalle conductor | 2026-09-01 |

---

## 🟢 Baja prioridad / Futuras versiones

### ~~Módulo: Reintegro para residentes verificados~~ → ✅ resuelto (sesión 2026-09-01)
### ~~Toggle estadísticas de inspectores por municipio~~ → ✅ resuelto (sesión 2026-09-01)
`Municipio.estadisticas_inspectores_activo`. Migración 0066. Check en `panel_inspectores`.
### ~~Inspector como cobrador (módulo premium)~~ → ✅ resuelto (sesión 2026-09-01)
`ModuloMunicipio` `cobrador_inspector`. Vista `cobrar_infraccion_inspector`. Template `cobrar_infraccion.html`.
### ~~Dashboard en TV (token + auto-refresh)~~ → ✅ resuelto (sesión 2026-09-01)
`Municipio.token_tv`. Migración 0066. Vista pública `dashboard_tv`. Template standalone `publico/dashboard_tv.html`. Superadmin genera token en `editar_municipio`.
### ~~Mapa de calor de infracciones~~ → ✅ resuelto (sesión 2026-09-01)
Vista `mapa_calor_infracciones`. Template con Leaflet.js. Círculos proporcionales por subcuadra. Enlace en sidebar admin.
### ~~Módulo de impugnaciones~~ → ✅ resuelto (sesión 2026-09-01)
Modelo `Impugnacion`. Migración 0067. Conductor impugna desde `historial_infracciones`. Admin resuelve (acepta/rechaza). Badge de pendientes en sidebar. Botón "Impugnar" en cada infracción.
### ~~Transferencia de saldo entre conductores~~ → ✅ resuelto (sesión 2026-09-01)
Modelo `TransferenciaSaldo`. Migración 0067. Use case `transferir_saldo.py`. Vistas conductor para enviar/responder/cancelar. Saldo reservado hasta respuesta (24h expira).

### Responsive > 1050px
En pantallas grandes el layout del panel admin queda con mucho espacio vacío.

### Migración a Digital Ocean (producción municipal real)
**Disparador**: cuando el sistema pase de pruebas a municipio real pagando.
Ver checklist: `CHECKLIST_PRODUCCION_2026-09-01.md`.

### Reconocimiento de patente por cámara (OCR)
Google ML Kit o Tesseract.js. Botón "📷 Escanear" en `verificar.html`.

### Alertas de vencimiento al conductor (push / WhatsApp)

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
