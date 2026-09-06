# Pendientes — Estacionamiento Proyecto

Última actualización: 2026-09-06 (sesión 3)

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

- **Inspector — impresora BLE: no volver a pedir vinculación al imprimir**
  `imprimirActa()` hace `reconectarImpresora()` silencioso primero. Si falla (bug conocido de Chrome con `getDevices()`), abre el diálogo de selección igual.
  Workaround actual ya implementado: reconectar por nombre (`requestDevice` pre-filtrado). Evaluar si Chrome corrigió el bug o documentar como límite del navegador.
  Archivos: `static/.../js/impresora_bluetooth.js` (función `reconectarImpresora`).

---

## 🟢 Baja prioridad / Futuras versiones


- **Migración a Digital Ocean** — disparador: cuando el sistema pase a municipio real pagando. Ver `CHECKLIST_PRODUCCION_2026-09-01.md`.
- **OCR de patentes** — Google ML Kit o Tesseract.js. Botón "📷 Escanear" en `verificar.html`.
- **Alertas de vencimiento al conductor** — push / WhatsApp.
- **Tutorial GIFs en landing pública** — el tutorial por rol ya existe dentro del sistema (collapsible `<details>` en cada panel). Pendiente: versión con GIF o screenshots para la landing pública.
- **Auditoría de reseteos de contraseña** — registrar quién reseteó la contraseña de quién (hoy solo queda rastro de `cambio_password_requerido=True`). Usar `LogEntry` de Django Admin o modelo propio.
- **Jerarquía de botones en formularios** — estandarizar: botón principal con `--color-primary`, botón secundario con `.btn-outline`. Hoy hay inconsistencia entre templates.
- **Refactor estilos inline** — muchos templates tienen `style=""` repetido. Crear clases `.card-form`, `.section-admin` en `global.css` para centralizar y facilitar el Dark Mode.
---

## ✅ Resuelto

### Sesión 2026-09-06 (tarde 3) — Logo registro + pausa configurable entre copias

| Ítem | Detalle |
|---|---|
| Logo municipio en registro | `registro.html`: logo/nombre del municipio debajo del ícono. 1 municipio → logo fijo. Varios → JS actualiza el logo al seleccionar en el `<select>`. |
| Pausa configurable entre copias | `Municipio.segundos_pausa_doble_copia` (migración 0071). 0 = el inspector confirma antes de la copia 2. >0 = pausa automática en segundos. Config en `editar_municipio.html` (sección general). JS en `ticket_infraccion.html` reemplaza el 800ms hardcodeado. |

### Sesión 2026-09-06 (tarde 2) — Banner impresora BLE no vinculada

| Ítem | Detalle |
|---|---|
| Banner visible cuando no hay impresora | `panel_inspectores.html`: banner amarillo con botón "Vincular impresora" en lugar del `<span>` pequeño oculto. Se oculta automáticamente al detectar impresora via `getDevices()` o localStorage. El `<details>` de config queda para configuración avanzada. |

### Sesión 2026-09-06 (tarde 1) — 4 ítems 🟡 + UptimeRobot + limpieza Railway

| Ítem | Detalle |
|---|---|
| Alerta JS "cambios sin guardar" en editar_municipio | Script en `editar_municipio.html`: detecta cambios en cada sección y resalta el botón Guardar correspondiente con un outline naranja |
| Tablas desktop ≥ 1050px | `global.css`: `.card` pasa de `overflow-x: visible` a `overflow-x: auto; overflow-y: visible` + regla `table { width:100% }` para aprovechar el espacio |
| UptimeRobot | Endpoint `/health/` verificado: devuelve `{"status":"ok"}` con DB check. Pasos de config en esta sesión (ver más abajo) |
| Limpieza datos prueba Railway | Ya implementada en la UI: superadmin → editar_municipio → Zona de peligro → escribir `CONFIRMAR+NOMBRE` → botón. No requiere comandos de consola |

**UptimeRobot — pasos para configurar (hacerlo en uptimerobot.com):**
1. Crear cuenta gratuita en uptimerobot.com
2. "Add New Monitor" → tipo: HTTP(s)
3. URL: `https://estacionamiento.up.railway.app/health/`
4. Intervalo: 5 minutos
5. Alertas: configurar email o Telegram para notificación de caída

### Sesión 2026-09-06 (mañana) — Mejoras UX/UI (análisis AI Studio)

| Ítem | Archivos |
|---|---|
| Validación de email en backend al crear tesorero | `views_admin.py`: helper `_correo_invalido()` + `validate_email` |
| Toggle 👁 para inputs de contraseña | `templates/admin/gestionar_staff.html`, `editar_staff.html`; script en `base.html` |
| Toasts `position:fixed` para mensajes Django | `global.css` (clases `.toast*`), `base.html` (script + contenedor) |

**Contexto:** las mejoras surgieron del análisis generado con Google AI Studio (`ANALISIS_AI_STUDIO_2026-09-06.md`). Se descartaron por ahora: refactor a Django ModelForms para `editar_municipio`, table stacking CSS, y LogEntry para auditoría de contraseñas.

### Sesión 2026-09-06 — Backlog (4 ítems + SugerenciaMejora + eliminación de cuenta)

| Ítem | Archivos / migración |
|---|---|
| Reseteo de contraseña para admins | `views_admin.py`: `editar_staff` + `gestionar_staff` |
| Sectorizar `editar_municipio` | `views_superadmin.py` (4 ramas POST), `templates/superadmin/editar_municipio.html` (4 forms) |
| Admin puede gestionar tesoreros | `views_admin.py`: `gestionar_staff`, `editar_staff`; templates nuevos |
| Responsive ≥ 1050px | `static/.../global.css`: `@media (min-width: 1050px)` |
| `SugerenciaMejora` — cualquier usuario puede sugerir mejoras | modelo, migración 0070, views_conductor + views_superadmin, 5 templates nuevos |
| `SolicitudEliminacionCuenta` — conductor puede darse de baja (soft-delete) | modelo, migración 0070, views_conductor, 1 template nuevo |

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
