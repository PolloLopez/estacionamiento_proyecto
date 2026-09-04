# Pendientes — Estacionamiento Proyecto

Última actualización: 2026-09-04

---

## 🗺️ Contexto de deploy

- **Railway** → ambiente de prueba (inspectores + admin testeando). No es producción municipal real.
- **Digital Ocean** → deploy definitivo cuando el sistema vaya a municipios reales pagando.
- El código es el mismo; los cambios son de infraestructura y configuración.

---

## 🔴 Alta prioridad

_Sin ítems pendientes._

---

## 🟡 Media prioridad

- **Limpieza de datos de prueba en Railway** antes del go-live con un municipio real. Ver `CHECKLIST_PRODUCCION_2026-09-01.md`.
- **UptimeRobot**: configurar monitoreo de uptime si no está activo todavía.

---

## 🟢 Baja prioridad / Futuras versiones

- **Responsive > 1050px** — en pantallas grandes el panel admin queda con mucho espacio vacío.
- **Migración a Digital Ocean** — disparador: cuando el sistema pase a municipio real pagando. Ver `CHECKLIST_PRODUCCION_2026-09-01.md`.
- **OCR de patentes** — Google ML Kit o Tesseract.js. Botón "📷 Escanear" en `verificar.html`.
- **Alertas de vencimiento al conductor** — push / WhatsApp.
- **Tutorial GIFs en landing pública** — el tutorial por rol ya existe dentro del sistema (collapsible `<details>` en cada panel). Pendiente: versión con GIF o screenshots para la landing pública.

---

## ✅ Resuelto

### Sesión 2026-09-04 — Bugs pre-demo

- **Bug conductor: fuera de horario en GET** — `views_conductor.py`: `puede_estacionar_ahora()` evaluado también en el GET de `estacionar_vehiculo`. `inicio_usuarios.html`: botón Estacionar deshabilitado con mensaje cuando está fuera de horario. `estacionar_vehiculo.html`: banner + form bloqueado con `pointer-events:none` cuando no se puede estacionar. ✅
- **Bug dark mode: btn-outline y tarjeta-vehiculo** — `global.css`: override dark mode para `.btn-outline` (fondo semitransparente, borde primario) y `.tarjeta-vehiculo.seleccionada` (verde oscuro semitransparente en lugar del #f0fff4 hardcodeado). ✅
- **Bug horario conductor ≠ inspector** — `services/horarios.py`: las tres funciones (`puede_estacionar_ahora`, `calcular_opciones_duracion`, `cerrar_estacionamientos_vencidos_por_horario`) ahora usan siempre `.order_by("-id").first()` para tomar el mismo registro de `HorarioEstacionamiento`. Si hay duplicados, todas ven el más reciente y quedan sincronizadas. ✅

### Sesión 2026-09-03 — Templates conductor + superadmin

- **Templates conductor faltantes** — `crear_impugnacion.html`, `transferir_saldo.html`, `transferencias_saldo.html` creados. ✅
- **Token TV en superadmin** — `editar_municipio.html`: sección "Dashboard TV" con URL y botón para generar/regenerar token. `views_superadmin.py`: acción `generar_token_tv` con `secrets.token_urlsafe(32)`. ✅
- **Badge impugnaciones en admin** — `views_admin.py`: count de impugnaciones pendientes del municipio. Sidebar muestra badge numérico en "⚖️ Impugnaciones". ✅
- **Botón Impugnar en historial** — `historial_infracciones.html`: botón "📋 Impugnar" en infracciones con estado `pendiente` o `pagada`. ✅

### Sesión 2026-09-01 — Ítems 🟡 y 🟢 del backlog

| Ítem | Archivo / migración |
|---|---|
| Vendedores — permiso individual para abonos | `models.py`, `views_admin.py` |
| Perfil extendido conductor — campo domicilio | migración 0064 |
| Admin panel responsive con desplegables | `views_admin.py`, `panel_admin.html` |
| Ícono PWA dinámico con logo del municipio | `views_conductor.py`, `manifest.json` |
| Reseteo de contraseña desde panel admin | `views_admin.py detalle_usuario_admin` |
| ForzarCambioPasswordMiddleware | `middleware.py` + `settings.py` |
| Validación foto infracción | `views_inspector.py` |
| `SECURE_REFERRER_POLICY` | `settings.py` |
| `dashboard_admin` con filtro de fechas | `views_admin.py`, `/admin-dashboard/` |
| Cap `[:50]` estacionamientos activos | `views_admin.py` |
| `Infraccion.subcuadra → SET_NULL` | migración 0061 |
| `VerificacionInspector` FK → SET_NULL | migración 0062 |
| Descuentos voluntarios de infracciones | migración 0063, `services/infracciones.py`, `pagar_infraccion.py` |
| Comisión vendedor como módulo premium | `MODULOS`, `gestionar_tarifas.html` |
| Perfil extendido vendedor | migración 0064: `domicilio_comercial`, `ubicacion_lat/lon` |
| Cierre de caja configurable por período | migración 0064, `caja_vendedores`, `forzar_cierre_vendedor` |
| GPS subcuadra al estacionar | endpoint `subcuadra_cercana`, JS en `estacionar_vehiculo.html` |
| Tesorero certifica cierres de admin | `views_admin.py`, `panel_tesorero.html` |
| Panel auditoría superadmin | `views_superadmin.py auditoria_superadmin`, `/superadmin/auditoria/` |
| Reportes de subcuadras | `views_admin.py reportes_subcuadras`, `/admin-subcuadras/reportes/` |
| Módulo reintegro residentes | migración 0065, `services/reintegro.py`, modelo `Reintegro` |
| Toggle estadísticas inspectores | `Municipio.estadisticas_inspectores_activo`, migración 0066 |
| Inspector como cobrador (módulo premium) | `ModuloMunicipio cobrador_inspector`, `cobrar_infraccion_inspector` |
| Dashboard en TV (token + auto-refresh) | `Municipio.token_tv`, migración 0066, vista pública `dashboard_tv` |
| Mapa de calor de infracciones | Vista `mapa_calor_infracciones`, Leaflet.js, círculos por subcuadra |
| Módulo de impugnaciones | modelo `Impugnacion`, migración 0067 |
| Transferencia de saldo entre conductores | modelo `TransferenciaSaldo`, migración 0067, use case `transferir_saldo.py` |
| GitHub Pages landing | archivo `landing_github_pages.html` |
| Auditorías de seguridad, rendimiento y BD | informes `AUDITORIA_*_2026-09-01.md` |
| Checklist de producción | `CHECKLIST_PRODUCCION_2026-09-01.md` |

### Sesión 2026-08-25 — SIA titular + bloqueo inspector fuera de horario

- Migración `sia_titular_fields_vehiculo` generada y aplicada. ✅
- `verificar_vehiculo` view: `puede_estacionar_ahora()` evaluado antes del POST del inspector. ✅
- `verificar.html`: form oculto fuera de horario, banner ⏰ con `mensaje_horario`. ✅

### Sesión 2026-08-24 — Tarifas click-to-edit, login UX, lockout

- Login con tipo de error por campo (correo no encontrado, password incorrecta, cuenta inactiva). Pre-carga correo. ✅
- Lockout: botón "🔑 Restablecer contraseña". ✅
- Tarifas refactorizadas a 7 secciones individuales con click-to-edit. Partial `admin/_campo_tarifa.html`. ✅
- Tests actualizados. ✅

### Sesión 2026-08-24 (mañana) — SIA parser v2, titular, sidebar agrupado

- SIA parser: fix raíz — ANDIS usa `<th>` en encabezados → Strategy B. 38 tests OK. ✅
- `ResultadoSia` con `nombre`, `apellido`, `documento` separados. ✅
- `Vehiculo`: campos `sia_titular_nombre`, `sia_titular_apellido`, `sia_titular_dni`, `sia_nci`. ✅
- Sidebar admin agrupado en 4 rubros: Personal · Vehículos · Configuración · Caja y rendiciones. ✅
- Exenciones unificadas: badge "♿ SIA · ANDIS" con nombre, DNI, vigencia. ✅

### Sesión 2026-08-23 — Dark mode, responsive, cierre de caja admin

- Dark mode toggle en navbar (persiste en `localStorage`). FOUC prevention. `--color-acento`. ✅
- `Municipio.color_acento` (migración 0055). Superadmin configura 3 colores. ✅
- Responsive completo: grid admin colapsable, tablas con overflow-x. ✅
- `auditoria_staff`: vista unificada admin. ✅
- Cierre de caja para rol admin. ✅

### Sesión 2026-08-21 — OAuth, SIA ANDIS, bloqueo fuera de horario

- `adapters.py`: bloqueo OAuth account takeover. ✅
- `services/sia_verificacion.py`: verificación SIA contra ANDIS. 8 estados. ✅
- `models.py`: campos `sia_*` en `Infraccion` (migración 0054). ✅
- `views_inspector.py`: bloqueo infraccionamiento fuera del horario de cobro. ✅

### Sesiones 2026-08-18/20 — MercadoPago, backups, seguridad, email

- Pago público sin registro: `PagoPublico` (migración 0051), webhook. ✅
- Backups PostgreSQL: GitHub Actions diario → artifact 30 días. ✅
- Email transaccional (Brevo/anymail): recuperación de contraseña. ✅
- `django-axes`: lockout IP+usuario, 5 intentos, 1h cooloff. ✅
- Verificación de email obligatoria en Railway. ✅
- Límites de carga MercadoPago por municipio (migración 0052). ✅
- 160 tests, todos OK. ✅

### Sesiones 2026-08-13/19 — GPS, superadmin, impresora BLE, rendiciones

- `Subcuadra.lat/lon` + endpoint GPS. ✅
- Superadmin `editar_municipio`: logo, colores, `leyenda_horarios`, `texto_ordenanza` (migración 0053). ✅
- Importación de exenciones desde Excel. ✅
- `PlantillaDocumento` (5 tipos de comprobante personalizables). ✅
- Impresora BLE: persistencia en `localStorage`, doble copia, QR nativo ESC/POS. ✅
- Rendiciones: PDF, tesorero valida/observa, `LiquidacionComision` con factura. ✅
- PWA icons (192, 512, apple-touch). ✅
