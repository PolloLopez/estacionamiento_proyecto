# Pendientes — Estacionamiento Proyecto

Última actualización: 2026-09-06 (sesión 5)

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
  Workaround actual implementado: reconectar por nombre (`requestDevice` pre-filtrado). Evaluar si Chrome corrigió el bug o documentar como límite del navegador.
  Archivo: `static/.../js/impresora_bluetooth.js` (función `reconectarImpresora`).

---

## 🟢 Baja prioridad / Futuras versiones

- **Migración a Digital Ocean** — disparador: cuando el sistema pase a municipio real pagando. Ver `CHECKLIST_PRODUCCION_2026-09-01.md`.
- **OCR de patentes** — Google ML Kit o Tesseract.js. Botón "📷 Escanear" en `verificar.html`.
- **Alertas de vencimiento al conductor** — push / WhatsApp.
- **Tutorial GIFs en landing pública** — el tutorial por rol ya existe dentro del sistema (collapsible `<details>` en cada panel). Pendiente: versión con GIF para la landing pública.
- **Auditoría de reseteos de contraseña** — registrar quién reseteó la contraseña de quién. Usar `LogEntry` de Django Admin o modelo propio.
- **Jerarquía de botones en formularios** — estandarizar: botón principal con `--color-primary`, botón secundario con `.btn-outline`. Hay inconsistencias entre templates.
- **Refactor estilos inline** — muchos templates tienen `style=""` repetido. Crear clases `.card-form`, `.section-admin` en `global.css`.

---

## ✅ Resuelto

### Sesión 2026-09-06 (tarde 5) — Rendiciones: 3 mejoras

| Ítem | Detalle |
|---|---|
| Notas obligatorias al observar rendición | `views_tesorero.py`: backend rechaza si `accion=observar` y `notas_tesorero` vacío. JS en `panel_tesorero.html`: botón "Observar" no hace submit si el campo está vacío (borde rojo + focus). |
| Detalle de rendición | Nueva vista `detalle_rendicion(rendicion_id)` con `@require_role("tesorero", "admin")`. Muestra encabezado, totales, cierres incluidos y liquidaciones de comisión. Botón "Ver detalle" en historial del tesorero y en tabla de rendiciones del admin. Template `tesorero/detalle_rendicion.html`. URL `/tesorero/rendicion/<id>/`. |
| Comisiones de vendedores vacías (bug) | `crear_rendicion()` en `views_admin.py` creaba la `Rendicion` pero nunca generaba `LiquidacionComision`. Fix: al crear la rendición, agrupa `CierreCaja.ganancia_usuario` por vendedor y crea una liquidación por cada vendedor con comisión > 0. |

### Sesión 2026-09-06 (tarde 4) — Auto-impresión, sugerencias por rol, bug horario inspector, alias impresora

| Ítem | Detalle |
|---|---|
| Bug: inspector actúa sin horario configurado | `services/horarios.py`: `puede_estacionar_ahora()` ganó parámetro `bloquear_sin_horario`. Cuando es `True` y no hay horario para hoy (ej: domingo), devuelve `False` sin cachear. Usado en `verificar_vehiculo` y `registrar_infraccion`. |
| Auto-impresión al cargar ticket | `ticket_infraccion.html`: `imprimirActa()` se llama en `DOMContentLoaded`. Vista previa del acta oculta. Botón "Reintentar" solo aparece si hay error. |
| Sugerencias filtradas por rol | `views_conductor.py`: `AREAS_POR_ROL` filtra las áreas del select por rol. Conductor ve solo "conductor"+"general"; inspector solo "inspector"+"general", etc. |
| Alias impresora más visible | `panel_inspectores.html`: al vincular impresora, el `<details>` de config se abre solo. Nuevo placeholder "Ej: Mi impresora". |

### Sesión 2026-09-06 (tarde 3) — Logo en registro + pausa configurable entre copias

| Ítem | Detalle |
|---|---|
| Logo municipio en registro | `registro.html`: logo/nombre debajo del ícono. 1 municipio → fijo. Varios → JS actualiza al seleccionar. |
| Pausa configurable entre copias | `Municipio.segundos_pausa_doble_copia` (migración 0071). 0=el inspector confirma. >0=pausa automática. Config en `editar_municipio.html`. JS en `ticket_infraccion.html`. |

### Sesión 2026-09-06 (tarde 2) — Banner impresora BLE

| Ítem | Detalle |
|---|---|
| Banner visible sin impresora | `panel_inspectores.html`: banner con botón "Vincular impresora" en lugar del `<span>` oculto. Se oculta al detectar impresora. |

### Sesión 2026-09-06 (tarde 1) — Tablas, UptimeRobot, alerta cambios sin guardar, limpieza Railway

| Ítem | Detalle |
|---|---|
| Alerta JS "cambios sin guardar" | `editar_municipio.html`: detecta cambios en cada sección, resalta el botón Guardar con outline naranja. |
| Tablas desktop ≥ 1050px | `global.css`: `.card` con `overflow-x: auto` + `table { width:100% }`. |
| UptimeRobot | Endpoint `/health/` verificado. Config: uptimerobot.com → HTTP(s) → `https://estacionamiento.up.railway.app/health/` → 5 min. |
| Limpieza datos prueba Railway | UI en superadmin → editar_municipio → Zona de peligro → escribir `CONFIRMAR+NOMBRE` → botón. |

### Sesión 2026-09-06 (mañana) — Mejoras UX/UI

| Ítem | Detalle |
|---|---|
| Validación de email backend al crear tesorero | `views_admin.py`: `_correo_invalido()` + `validate_email` |
| Toggle 👁 para inputs de contraseña | `gestionar_staff.html`, `editar_staff.html`; script en `base.html` |
| Toasts `position:fixed` | `global.css` (clases `.toast*`), `base.html` (script + contenedor) |
| Fix: comentario Django multilinea visible en producción | `base.html`: `{# ... #}` de Django solo funciona en 1 línea. Comentario multilinea se eliminó. |

### Sesión 2026-09-06 (backlog) — SugerenciaMejora, SolicitudEliminacionCuenta, staff

| Ítem | Detalle |
|---|---|
| Reseteo de contraseña para admins | `views_admin.py`: `editar_staff` + `gestionar_staff` |
| Sectorizar `editar_municipio` | `views_superadmin.py` (4 ramas POST), `editar_municipio.html` (4 forms) |
| Admin puede gestionar tesoreros | `views_admin.py`: `gestionar_staff`, `editar_staff` |
| Responsive ≥ 1050px | `global.css`: `@media (min-width: 1050px)` |
| `SugerenciaMejora` | modelo, migración 0070, `views_conductor` + `views_superadmin`, 5 templates |
| `SolicitudEliminacionCuenta` | modelo, migración 0070, `views_conductor`, 1 template |

### Sesión 2026-09-04 — Bugs pre-demo

| Ítem | Detalle |
|---|---|
| Bug conductor: fuera de horario en GET | `views_conductor.py`: `puede_estacionar_ahora()` evaluado en GET. Botón deshabilitado con mensaje. |
| Bug dark mode: btn-outline y tarjeta-vehiculo | `global.css`: overrides dark mode para `.btn-outline` y `.tarjeta-vehiculo.seleccionada`. |
| Bug horario conductor ≠ inspector | `services/horarios.py`: todas las funciones usan `.order_by("-id").first()` para consistencia. |

### Sesiones 2026-08-13 al 2026-09-03 — Base del sistema

| Bloque | Resumen |
|---|---|
| Templates conductor faltantes | `crear_impugnacion.html`, `transferir_saldo.html`, `transferencias_saldo.html` |
| Token TV | `editar_municipio.html`: sección "Dashboard TV" con URL y botón regenerar. |
| Badge impugnaciones en admin | `views_admin.py`: count + badge en sidebar. |
| Vendedores — permiso individual para abonos | `models.py`, `views_admin.py` |
| Perfil extendido conductor/vendedor | migraciones 0064 (`domicilio`, `ubicacion_lat/lon`) |
| Admin panel responsive | `panel_admin.html` con desplegables |
| Ícono PWA dinámico | `views_conductor.py`, `manifest.json` |
| `ForzarCambioPasswordMiddleware` | `middleware.py` + `settings.py` |
| `dashboard_admin` con filtro de fechas | `views_admin.py`, `/admin-dashboard/` |
| `Infraccion.subcuadra → SET_NULL` | migración 0061 |
| `VerificacionInspector FK → SET_NULL` | migración 0062 |
| Descuentos voluntarios de infracciones | migración 0063, `services/infracciones.py` |
| Cierre de caja por período | migración 0064, `caja_vendedores`, `forzar_cierre_vendedor` |
| GPS subcuadra | endpoint `subcuadra_cercana`, JS en `estacionar_vehiculo.html` |
| Tesorero certifica cierres de admin | `views_admin.py`, `panel_tesorero.html` |
| Panel auditoría superadmin | `views_superadmin.py auditoria_superadmin` |
| Reportes de subcuadras | `views_admin.py reportes_subcuadras` |
| Módulo reintegro residentes | migración 0065, `services/reintegro.py` |
| Toggle estadísticas inspectores | `Municipio.estadisticas_inspectores_activo`, migración 0066 |
| Inspector cobrador (módulo premium) | `ModuloMunicipio cobrador_inspector` |
| Dashboard TV | `Municipio.token_tv`, migración 0066, vista pública |
| Mapa de calor de infracciones | Leaflet.js, círculos por subcuadra |
| Módulo de impugnaciones | modelo `Impugnacion`, migración 0067 |
| Transferencia de saldo | modelo `TransferenciaSaldo`, migración 0067 |
| GitHub Pages landing | `landing_github_pages.html` |
| Auditorías (seguridad, rendimiento, BD) | informes `AUDITORIA_*_2026-09-01.md` |
| Checklist de producción | `CHECKLIST_PRODUCCION_2026-09-01.md` |
| Impresora BLE base | persistencia `localStorage`, doble copia, QR nativo ESC/POS |
| Rendiciones base | PDF, tesorero valida/observa, `LiquidacionComision` |
| Dark mode + colores municipio | `global.css`, `Municipio.color_acento` (migración 0055) |
| Responsive completo | grid admin colapsable |
| `auditoria_staff` | vista unificada admin |
| OAuth bloqueo account takeover | `adapters.py` |
| SIA ANDIS | `services/sia_verificacion.py`, campos en `Infraccion` (migración 0054) |
| Bloqueo inspector fuera de horario | `views_inspector.py`, `verificar.html` |
| MercadoPago + backups + email + axes | sesiones 2026-08-18/20 |
| SIA parser v2 + titular + sidebar agrupado | sesión 2026-08-24 |
| Tarifas click-to-edit + login UX + lockout | sesión 2026-08-24 |
