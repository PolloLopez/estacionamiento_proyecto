# CONTEXT.md — Sistema de Estacionamiento Medido
> Referencia fija del proyecto. No incluye tareas pendientes ni cambios en curso → ver PENDIENTES.md.

Última actualización estructural: 2026-10-01 (sesión 33)

---

## Proyecto

Sistema web de gestión de estacionamiento medido para municipios.
Permite que conductores registren estacionamientos, inspectores labren infracciones,
vendedores cobren en efectivo o con otros medios, y administradores gestionen el sistema completo.

**Multi-tenant básico**: cada municipio opera de forma independiente. Los datos
(usuarios, vehículos, infracciones, caja) no se mezclan entre municipios.

Repo: https://github.com/PolloLopez/estacionamiento_proyecto

---

## Deploy

| Entorno | Plataforma | URL |
|---------|-----------|-----|
| Testing | Railway (Hobby, $5/mes) | https://estacionamiento.up.railway.app |
| Producción futura | Digital Ocean | — (migración pendiente) |
| Local | `python manage.py runserver` | http://localhost:8000 |

Variables de entorno en Railway:
```
SECRET_KEY, DEBUG=False, ALLOWED_HOSTS, CSRF_TRUSTED_ORIGINS
DATABASE_URL                    # PostgreSQL (Railway add-on)
SITE_ID                         # 2 (para allauth)
GOOGLE_CLIENT_ID, GOOGLE_CLIENT_SECRET
MP_ACCESS_TOKEN, MP_PUBLIC_KEY, MP_CLIENT_ID, MP_CLIENT_SECRET
MP_WEBHOOK_SECRET               # secreto HMAC desde MP Dashboard → Webhooks
CLOUDINARY_CLOUD_NAME, CLOUDINARY_API_KEY, CLOUDINARY_API_SECRET
BREVO_API_KEY                   # email transaccional
DEFAULT_FROM_EMAIL
SENTRY_DSN                      # error tracking (Sentry)
```

Git flow: `develop` → trabajo activo · `main` → Railway auto-deploy.
Admin URL: `/sistema-interno/` (no obvia, reduce bruteforce).

---

## Stack

| Capa | Tecnología | Motivo |
|------|-----------|--------|
| Backend | Django 5.2, Python 3.12 | Framework principal |
| Base de datos | SQLite (local) / PostgreSQL (Railway) | Railway provee Postgres |
| Autenticación | django-allauth + Google OAuth | Login social + email |
| Pagos | MercadoPago SDK | Carga de saldo online |
| Media storage | Cloudinary (cdn) / filesystem (local) | Fotos de infracciones y logos en Railway |
| Imágenes | Pillow | Watermark GPS sobre fotos de actas |
| PDF | reportlab | PDF de infracciones para juzgado de faltas |
| Excel | openpyxl | Exportación estadísticas inspectores |
| Seguridad | django-axes | Rate limiting en login (5 intentos, 1h cooloff) |
| Error tracking | Sentry (django-sentry-sdk) | Alertas de errores en Railway |
| Email | django-anymail + Brevo | API transaccional |
| Frontend | HTML + CSS propio (`global.css`) + **React 18 UMD** (hibridación incremental) | Sin build step (no Vite/Webpack). React servido desde `static/` propio. Componentes: `PanelEstado`, `HistorialConductor`, `MisVehiculos`, `FormularioEstacionar`, `VerificadorInspector` (incluye `FormularioInfraccion` + `ModalTicket`). Django sigue siendo el shell (routing, auth, base). `JsonResponse` puro, sin DRF. |
| Deploy | Railway + Gunicorn + WhiteNoise | PaaS simple |
| Tests | Django TestCase | ~198 tests (suite estable) |
| Impresora BLE | Web Bluetooth API (`impresora_bluetooth.js`) | Chrome Android (HTTPS). ESC/POS 58mm. Doble copia con pausa configurable (`Municipio.segundos_pausa_doble_copia`): 0=el inspector confirma, >0=pausa automática en segundos. Alias por dispositivo en localStorage. QR nativo `GS(k)`. |

---

## Arquitectura

```
views_*.py  →  use_cases/  →  services/  →  domain/
                                          →  models.py
```

**views_api.py** — endpoints `JsonResponse` puro para el frontend React. Sin DRF. Convención: `api_conductor_*` y `api_inspector_*`. Endpoints actuales: `GET datos-estacionar/`, `POST estacionar/`, `GET historial/`, `GET opciones-renovar/<id>/`, `POST renovar/<id>/`, `GET dashboard/`, `GET estacionamientos/activos/`, `POST inspector/verificar/`, `POST inspector/registrar_infraccion/` (multipart — incluye foto).

**views.py** — fachada pura (~100 líneas), re-exporta desde módulos por rol. No define vistas.

**Módulos de vistas:**
- `views_auth.py` — login, logout, registro (con logo del municipio), completar_perfil, OAuth
- `views_conductor.py` — estacionar, historial, infracciones, vehículos, sugerencias de mejora (con `rango_edad`), eliminación de cuenta. UX estacionar: GPS on demand (botón "Detectar mi cuadra", no auto-detect al cargar), `vehiculos_recientes` (últimos 3 usados), agregar vehículo inline.
- `views_inspector.py` — panel, verificar patente, infracciones, PDF, `subcuadra_cercana` (API GPS)
- `views_vendedor.py` — cobros, abono mensual, caja, comisiones
- `views_admin.py` — gestión completa del municipio. Incluye `auditoria_staff` (actividad de vendedores e inspectores con filtro de fechas), `crear_rendicion` (genera automáticamente `LiquidacionComision` por vendedor al crear la rendición)
- `views_tesorero.py` — panel tesorero, `validar_rendicion` (notas obligatorias al observar), `detalle_rendicion`, depositar comisiones
- `views_superadmin.py` — gestión de municipios, admins y módulos
- `views_mp.py` — integración MercadoPago (carga de saldo + webhook unificado)
- `views_pago_publico.py` — pago sin registro: buscar por patente, pagar infracción/estacionamiento/abono vía MP
- `views_pwa.py` — manifest.json y service worker para PWA

**services/:**
- `services/horarios.py` — `puede_estacionar_ahora(municipio, bloquear_sin_horario=False)`: cuando `bloquear_sin_horario=True` y no hay `HorarioEstacionamiento` para el día de hoy, devuelve `(False, "No hay horario...")` sin cachear. Usado en vistas del inspector. Cuando `False` (default): sin horario = libre de cobro (conductor). `calcular_opciones_duracion(minutos_disponibles, tarifa_hora)`: tres casos — `< 30 min` → solo "30 min"; `30–59 min` → solo "1 hora"; `≥ 60 min` → opciones normales desde 1h. Así siempre hay al menos una opción mientras el horario esté activo. También: `obtener_tarifa_hora()`, `cerrar_estacionamientos_vencidos_por_horario()`.
- `services/infracciones.py` — `crear_infraccion()`, `cobrar_infraccion_efectivo()`, `calcular_estado_tolerancia()` (con `MARGEN_TOLERANCIA_SEGUNDOS = 60`). `MEDIOS_VALIDOS_COBRO = frozenset({"efectivo","transferencia","debito","credito","qr"})`.
- `services/saldo.py` — `cargar_saldo_conductor()`, `debitar_saldo_conductor()`
- `services/caja.py` — `generar_cierre_caja()`, `registrar_cobro_efectivo()`
- `services/verificacion.py` — `verificar_estado_vehiculo()`. Respeta `vigencia_exencion`.
- `services/descuentos_verificados.py` — `calcular_descuento_conductor()` y `aplicar_descuento_conductor()`. Aplica el descuento por conductor verificado definido en `Municipio.descuento_verificados_pct`. Usado en `use_cases/estacionar_vehiculo.py` antes del débito. La tarifa efectiva (ya con descuento) se pasa al GET de estacionar para que las opciones de duración muestren el precio real.
- `services/notificaciones.py` — `enviar_notificacion(usuario, tipo, mensaje)`. Respeta las preferencias `notif_*` del usuario. Usado desde vistas admin y superadmin.
- `services/sia_verificacion.py` — verificación SIA contra ANDIS. `verificar_sia(qr_url, patente_inspector) → ResultadoSia`. 8 estados posibles. Dos estrategias de parseo (clave-valor / encabezados ANDIS).

**use_cases/:** delegan en services/, sin lógica inline.
- `estacionar_vehiculo.py`, `pagar_infraccion.py`, `cobrar_estacionamiento.py`
- `finalizar_estacionamiento.py`, `registrar_infraccion.py`, `acreditar_saldo_mp.py`
- `procesar_pago_publico.py` — idempotente, `select_for_update()`.

**domain/:** `vehiculo_policy.py`, `saldo_policy.py`

**Shims de compatibilidad:** `services_caja.py`, `services_infracciones.py`, `services_verificacion.py` — re-exportan desde `services/`.

**utils.py** — `get_subcuadra_default()` + `sanitizar_patente()`.

**middleware.py** — redirige conductores sin `first_name` a `completar_perfil`. `ForzarCambioPasswordMiddleware`.

**factories.py** — `EstacionamientoFactory.crear()` centraliza creación con estado inicial.

---

## Modelo de datos — entidades principales

| Modelo | Descripción |
|--------|-------------|
| `Usuario` | AbstractUser con `correo` como USERNAME_FIELD. Flags: `es_admin`, `es_inspector`, `es_vendedor`, `es_conductor`, `es_tesorero`, `es_superadmin`. Campos: `saldo` (legacy, no usar — reemplazado por `BilleteraConductor`), `saldo_operativo` (caja del vendedor/inspector), `es_verificado`, `municipio`, `porcentaje_ganancia`, `cambio_password_requerido`. Preferencias de notificaciones: `notif_verificacion`, `notif_exencion`, `notif_sugerencia` (BooleanFields). |
| `BilleteraConductor` | Saldo digital del conductor por municipio. `UniqueConstraint(conductor, municipio)`. Un conductor puede tener saldo en N municipios. `services/saldo.py` → `debitar_saldo_conductor()` y `cargar_saldo_conductor()` usan este modelo como fuente de verdad. **No usar `Usuario.saldo` directo en código nuevo.** Migración `0085`. |
| `Municipio` | Configuración del municipio. Campos de tarifa/horario. Branding: `logo (ImageField, upload_to="municipios/logos/")`, `color_primario`, `color_secundario`, `color_acento`. Textos: `leyenda_horarios`, `texto_ordenanza`. Opciones: `tolerancia_multa_minutos`, `minutos_entre_infracciones`, `monto_minimo_carga`, `monto_maximo_carga`. Features: `estadisticas_inspectores_activo`, `token_tv`, `inspector_ve_sus_infracciones (Bool)`, `admin_puede_editar_plantillas (Bool)`, `modulo_informes_activo (Bool, default=False)` — activa tab "Informes" en `/admin-rendiciones/`, habilitado desde superadmin. `puede_gestionar_subcuadras (Bool, default=False)` — habilita `/admin-subcuadras/` para el admin municipal (por defecto solo superadmin); el superadmin lo activa desde `editar_municipio.html`. Migración `0087`. Impresora BLE: `segundos_pausa_doble_copia (0=el inspector confirma, >0=pausa automática en segundos)`. Ticket configurable: `ticket_fuente_size (1-3, default 2)` — mapea a byte ESC/POS `GS ! n`; `ticket_qr_size (1-8, default 4)` — módulo QR. Ambos editables desde superadmin (`editar_municipio.html`). Descuentos: `descuento_verificados_pct (Decimal, null=módulo inactivo)`, `descuento_solo_vecinos (Bool)`. Facturación: `porcentaje_plataforma`, `cuota_mantenimiento_mensual`, `concepto_recaudacion`. |
| `ModuloMunicipio` | Feature flags premium por municipio (activo/inactivo). Gestionado por superadmin. |
| `Vehiculo` | Patente única. Tipos: `auto`, `moto`. Exenciones: `exento_global`, `tipo_exencion`, `vigencia_exencion (DateField, null=indefinida)`, `exencion_verificada`, `notas_exencion`. Exención parcial: `subcuadras_exentas (M2M)`. Campos SIA: `sia_titular_nombre`, `sia_titular_apellido`, `sia_titular_dni`, `sia_nci`. |
| `Infraccion` | Estado: `pendiente`/`pagada`/`anulada`. `monto`, `motivo`, `foto (ImageField → Cloudinary)`, `descuento_porcentaje`. GPS del inspector: `gps_lat`, `gps_lon`, `gps_acc` (guardados al labrar; panel admin muestra "📍 Ver en mapa" vía OpenStreetMap). Campos SIA: `sia_presentado`, `sia_verificado`, `sia_estado`, `sia_url`, `sia_patente_sia`, `sia_nci`, `sia_titular`, `sia_vencimiento`, etc. |
| `VehiculoUsuario` | Relación N:N entre vehículo y conductor. |
| `Subcuadra` | Calle + altura + municipio. `unique_together`. `lat`/`lon` para GPS. `tipo_zona`: `"pagado"` (default) o `"libre"`. Mapa Leaflet/OSM en `/admin-subcuadras/` (pin azul = pagado, verde = libre). |
| `Estacionamiento` | Estado: `ACTIVO`/`FINALIZADO`. `hora_inicio`, `hora_fin`, `duracion_horas`, `costo_base`, `costo_final`. Un ACTIVO por vehículo. |
| `MovimientoCaja` | Registro contable de cada cobro. `medio_pago`: `efectivo`, `transferencia`, `debito`, `credito`, `qr`, `mercadopago`. `comision_monto`. `cerrado` al incluirse en un CierreCaja. |
| `CierreCaja` | Cierre de turno. `total_cobrado`, `ganancia_usuario`, `monto_municipio`. Desglose: `total_efectivo`, `total_transferencia`, `total_digital`. FK `rendicion → Rendicion (SET_NULL)`. Admins también cierran caja y otro admin certifica. |
| `AbonoMensual` | Estacionamiento libre por un mes. `mes`, `vehiculo`, `municipio`. `medio_pago`: `efectivo`/`mercadopago`/`saldo`. |
| `PagoPublico` | Pago vía MP sin cuenta. `tipo`: `infraccion`/`estacionamiento`/`abono`. `mp_payment_id (unique)`. Webhook detecta `metadata.pago_publico_id`. |
| `Tarifa` | `precio_por_hora`, `precio_por_hora_moto`, `precio_abono_auto`, `precio_abono_moto`, `monto_infraccion` (snapshot al crear el acta). |
| `HorarioEstacionamiento` | Horario semanal por día (`dia_semana` 0-6). `hora_inicio`, `hora_fin`, `activo`. Siempre usar `.order_by("-id").first()` si puede haber duplicados. |
| `DiaEspecial` | Feriados o días sin cobro. `fecha`, `cobro_activo`. |
| `VerificacionInspector` | Resultado de verificar una patente. Índice compuesto `(vehiculo_id, fecha DESC)`. |
| `Rendicion` | El admin cierra un período seleccionando `CierreCaja` certificados. Totales **calculados automáticamente**: `total_efectivo`, `total_digital` (transferencia+débito+crédito+QR), `total_neto`. Estado: `pendiente`/`validada`/`observada`. Al crear la rendición, el sistema genera automáticamente `LiquidacionComision` por cada vendedor con `ganancia_usuario > 0` en los cierres incluidos. |
| `LiquidacionComision` | Comisiones de un vendedor por período. Flujo: `pendiente` → `depositada` (tesorero) → `certificada` (vendedor). `factura_presentada`, `factura_archivo`. **Se crean automáticamente** al crear la `Rendicion` desde `views_admin.crear_rendicion()`. |
| `SugerenciaMejora` | Cualquier usuario puede enviar sugerencias de mejora. `area` filtrada por rol del usuario (conductor ve áreas de conductor+general, inspector ve inspector+general, etc.). `criticidad`, `estado`, `rango_edad` (opcional, choices: menor18/18-25/26-35/36-50/51-65/mayor65). Gestionada por superadmin. |
| `AuditoriaPassword` | Registro de cada reset de contraseña de un conductor por parte de un admin. Campos: `admin (FK→Usuario, SET_NULL)`, `conductor (FK→Usuario, CASCADE)`, `municipio (FK, SET_NULL)`, `tipo (choices: "dni"/"personalizada")`, `ip (GenericIPAddressField, null=ok)`, `fecha (auto_now_add)`. Se crea automáticamente en `views_admin.detalle_usuario_admin` al ejecutar `cambiar_password` o `resetear_password_dni`. El historial (últimos 10) se muestra dentro de la sección "🔑 Cambiar contraseña" en `admin/detalle_usuario.html`. Migración `0088`. |
| `SolicitudEliminacionCuenta` | El conductor puede solicitar darse de baja (soft-delete). Revisada por admin. |
| `Impugnacion` | El conductor impugna una infracción. Revisada por admin. |
| `TransferenciaSaldo` | Transferencia de saldo entre conductores. |
| `Reintegro` | Reintegro por cancelación temprana de estacionamiento. |
| `LiquidacionPlataforma` | Lo que el municipio le paga a la plataforma (Leandro). Iniciada por tesorero o superadmin. |
| `PlantillaDocumento` | Texto personalizable por municipio para comprobantes/actas. Tipos: `acta`, `cobro_hora`, `abono`, `cobro_infraccion`, `anulacion`. |
| `Notificacion` | Notificaciones internas al conductor. |
| `ConfigDocumentoVerificacion` | Define qué documentos pide el municipio al conductor para verificar su identidad. Campos: `municipio`, `nombre`, `tipo_predefinido` (dni_frente/dni_dorso/cedula_verde/domicilio/licencia_conducir/custom), `obligatorio`, `orden`, `activo`. Solo visible cuando `Municipio.modulo_verificacion_documental_activo=True`. Migración `0097`. |
| `DocumentoVerificacion` | Archivo subido por el conductor al solicitar verificación. FK a `SolicitudVerificacion` y `ConfigDocumentoVerificacion`. `archivo` → Cloudinary. `subido_en (auto_now_add)`. Migración `0097`. |

---

## Roles y reglas de negocio

**Tolerancia de gracia:** si el conductor resuelve una infracción dentro de `municipio.tolerancia_multa_minutos`, se anula automáticamente. Centralizado en `calcular_estado_tolerancia()` con `MARGEN_TOLERANCIA_SEGUNDOS = 60`.

**Exenciones:** exento global → nunca paga. Exento parcial → libre en sus subcuadras exentas. El inspector puede registrar exención 'discapacitado' vía SIA ANDIS.

**Horario inspector vs conductor:** `puede_estacionar_ahora(bloquear_sin_horario=True)` en vistas del inspector. Sin horario para hoy → inspector no puede operar (distinto al conductor, que estaciona gratis). El resultado de `bloquear_sin_horario=True` **no se cachea** para no contaminar el flujo del conductor.

**Abono mensual:** unique constraint (mes + vehículo + municipio). Cobra el vendedor (con comisión), el admin (sin comisión) o el conductor (con saldo digital).

**Comisión vendedor:** `monto * comision_vendedor% / 100` al cobrar → `MovimientoCaja.comision_monto`. Se acumula en `CierreCaja.ganancia_usuario` hasta que se genera la `LiquidacionComision`.

**Flujo financiero completo:**
1. Conductor activa estacionamiento → `debitar_saldo_conductor()` → `conductor.saldo ↓` + `MovimientoCaja(egreso)`
2. Vendedor cobra en persona → `MovimientoCaja(ingreso)` → `vendedor.saldo_operativo ↑`
3. Vendedor cierra caja → `generar_cierre_caja()` → `CierreCaja` creado, movimientos `cerrado=True`
4. Admin certifica cierre → revisa desglose efectivo/digital
5. Admin crea rendición → selecciona `CierreCaja` certificados → totales calculados automáticamente → `CierreCaja.rendicion FK` vinculado → **`LiquidacionComision` generada automáticamente por vendedor** (suma de `ganancia_usuario` de sus cierres)
6. Tesorero valida rendición → marca `validada` o `observada` (notas obligatorias al observar)
7. Tesorero deposita comisión → `LiquidacionComision(depositada)` → vendedor certifica recibo y adjunta factura

**Debitar saldo conductor:** `debitar_saldo_conductor()` NO abre su propia transacción. Debe llamarse dentro de `transaction.atomic()` + `select_for_update()`.

**Multi-municipio:** patrón obligatorio en todas las vistas:
```python
get_object_or_404(Modelo, id=pk, municipio=request.user.municipio)
# Nunca: Modelo.objects.get(id=pk)
```

**Concurrencia:** todo cobro usa `transaction.atomic()` + `select_for_update()`.

**Cierre reactivo (sin Celery):** estacionamientos vencidos se cierran al acceder a `inicio_usuarios` y al verificar una patente. Pull-based.

**Cache:** `puede_estacionar_ahora()` cacheada 1 hora por clave `municipio+fecha+hora`. El resultado con `bloquear_sin_horario=True` **no** se cachea.

**Patentes sanitizadas:** `sanitizar_patente()` — alfanumérico, mayúsculas, en todas las vistas.

**Rendición a tesorería:** notas obligatorias cuando el tesorero marca "observada". El tesorero y el admin que la generó pueden ver el detalle desde `/tesorero/rendicion/<id>/` (`detalle_rendicion`).

**Dashboard TV:** URL pública `/tv/<token>/` (sin auth). Token generado por superadmin en `editar_municipio`.

**Sugerencias de mejora:** las áreas del formulario se filtran por rol del usuario vía `AREAS_POR_ROL` en `views_conductor.py`.

---

## URLs de referencia

```
/usuarios/                                     → inicio conductor
/usuarios/admin-inicio/                        → panel admin
/usuarios/admin-usuarios/                      → gestionar conductores
/usuarios/admin-usuarios/<id>/                 → detalle conductor
/usuarios/admin-inspectores/                   → gestionar inspectores
/usuarios/admin-inspectores/estadisticas/      → estadísticas + exportar Excel
/usuarios/admin-vendedores/                    → gestionar vendedores
/usuarios/admin-infracciones/                  → infracciones
/usuarios/admin-rendiciones/                   → rendiciones (crear / certificar cierres)
/usuarios/admin-exenciones/                    → exenciones de vehículos
/usuarios/admin-subcuadras/                    → subcuadras + mapa GPS Leaflet
/usuarios/admin-dashboard/                     → dashboard con filtro de fechas
/usuarios/inspectores/                         → panel inspector
/usuarios/inspectores/verificar/               → verificar patente
/usuarios/inspectores/subcuadra-cercana/       → API JSON GPS (uso interno)
/usuarios/inspectores/infraccion/              → labrar acta (auto-impresión BLE al cargar)
/usuarios/inspectores/resumen/                 → mis infracciones del día
/usuarios/vendedores/                          → panel vendedor
/usuarios/vendedores/cobrar-infraccion/        → cobrar multa en efectivo
/usuarios/vendedores/cobrar-abono/             → cobrar abono mensual
/usuarios/vendedores/caja/                     → resumen de caja
/usuarios/vendedores/comisiones/               → mis liquidaciones de comisión
/usuarios/vendedores/comisiones/<id>/factura/  → presentar factura
/usuarios/tesorero/                            → panel tesorero
/usuarios/tesorero/rendicion/<id>/             → detalle rendición (tesorero + admin)
/usuarios/tesorero/rendicion/<id>/validar/     → validar/observar (POST)
/usuarios/tesorero/depositar/<id>/             → depositar comisión
/usuarios/sugerencias/nueva/                   → nueva sugerencia (áreas filtradas por rol)
/usuarios/mp/cargar/                           → iniciar carga MercadoPago
/usuarios/pagar/                               → pago público sin registro
/usuarios/pagar/<patente>/                     → detalle patente pública
/usuarios/manifest.json                        → PWA manifest
/usuarios/sw.js                                → PWA service worker
/usuarios/mis-infracciones/                    → infracciones del conductor
/usuarios/consultar-deuda/                     → buscar deuda por patente
/superadmin/municipios/                        → lista de municipios
/superadmin/municipio/<id>/editar/             → configuración completa del municipio
/superadmin/sugerencias/                       → panel de sugerencias
/sistema-interno/                              → Django Admin
/health/                                       → healthcheck (UptimeRobot)
/tv/<token>/                                   → dashboard TV público
```

---

## Historial de cambios por sesión

| Sesión | Fecha | Cambios principales |
|--------|-------|---------------------|
| 12 | 2026-09-20 | Input monto entero en carga MP · Mis vehículos en `/inicio/` · Multi-vehículo simultáneo · Agregar vehículo inline en abono · Cards responsive en mis-infracciones y mis-estacionamientos · Layout expandible detalle conductor · Reset contraseña al DNI |
| 13 | 2026-09-20 | `BilleteraConductor` (saldo por municipio, migración 0085) · Mail al resetear contraseña · Panel tesorero UX · Flujo confirmación depósito tesorero→vendedor · Flag `modulo_informes_activo` (migración 0086) · Rediseño `/admin-rendiciones/` con flujo de 3 pasos numerados |
| 14 | 2026-09-20 | Fix 10 errores en tests (nombre_completo property, UnboundLocalError, HorarioEstacionamiento en setUp) · Refactor 84 estilos inline → 6 clases CSS en global.css |
| 14-cont | 2026-09-20 | BLE impresora: fix duplicado no imprime (reconexión siempre fresca con `reconectarSilencioso()`) · BLE UX: muestra alias de impresora al pedir reconexión · Flag `puede_gestionar_subcuadras` en Municipio (migración 0087) · `/admin-subcuadras/` habilitado para admin con gate interno |
| 14-cont | 2026-09-21 | `AuditoriaPassword` model + migración 0088 · Integración en `detalle_usuario_admin` (crea registro en cada reset) · Historial de cambios en template `detalle_usuario.html` · Limpieza y reorganización completa de PENDIENTES.md |
| 15–17 | 2026-09-21/22 | Bug mapa subcuadras Leaflet CSS/JS · QR scan muestra infracciones recientes antes de estacionar · Notificaciones → Sugerencias en conductor · Alerta saldo insuficiente · Superadmin: tolerancia de multa + flag `admin_puede_configurar_tolerancia` · Sidebar admin condicional por flags · Seguridad: admin no gestiona a otro admin/tesorero · Tabs Vendedores/Inspectores en staff · Dashboard cobros+infracciones por día · Importar exenciones Excel (6 columnas) · Footer tutorial todos los roles · Flag `modulo_informes_activo` · `/admin-subcuadras/` con gate de flag. |
| 18 | 2026-09-24 | Datalist cascade básico en `registrar_infraccion.html` · Menú hamburguesa X en rojo · Dark mode `historial_infracciones.html` · SIA `PATENTE_NO_COINCIDE` mini-diálogo · `ticket_infraccion.html` solo opciones de impresión · BLE reconexión 3 niveles · Reintegro unificado en Módulos de pago · Fix `btn-confirmar-est` siempre deshabilitado. |
| 18–19 (V1.0.1) | 2026-09-24 | `estacionar_vehiculo.html`: sel-altura muestra "500 — Entre X y Y", botones GPS/duración/confirmar con 3 colores distintos, vehículos en `<details>`, tarjetas responsive. `inicio_usuarios.html`: "hasta HH:MM" + botón Renovar inline. `subcuadras.html`: popup Leaflet editar, filtro tabla, click fila→centra mapa, formulario unificado nueva subcuadra, pin 🏛️ sede, elimina toggle numérico. `editar_municipio.html`: badge "Sede configurada". |
| 20 | 2026-09-25 | BLE doble diálogo al infraccionar → un solo diálogo limpio · `agregar_vehiculo.html` btn-general → btn · `renovar_estacionamiento.html` bug 30 min con `LANGUAGE_CODE = "es-ar"` → `|unlocalize` en 4 valores · Railway DB password reseteada. |
| 22 | 2026-09-26 | Geoloc por municipio: `Municipio.geoloc_conductor_activa / geoloc_inspector_activa` · Conductor GPS silencioso → `Estacionamiento.gps_lat/gps_lon` · Precio custom subcuadra: `Subcuadra.precio_por_hora_custom`, prioridad en `obtener_tarifa_hora()` · Domicilio electrónico conductor: `UsuarioCustom.domicilio_electronico`, view `guardar_domicilio_electronico` · Migración `0096`. |
| 23 | 2026-09-26 | Verificación documental completa: `ConfigDocumentoVerificacion` + `DocumentoVerificacion` + flags en `Municipio` y `SolicitudVerificacion` (migración `0097`) · Superadmin CRUD configs · Conductor sube docs dinámicos en `solicitar_verificacion` · Admin revisa docs en `gestionar_verificaciones` · Bug `es_dia_libre_conductor()` filtro `activo=True` → fix con query separado · Selector subcuadra conductor: `<select>` → `<datalist>` con intersecciones y matching 4 niveles · `Municipio.selector_manual_conductor_activo` (migración `0098`). |
| 24 | 2026-09-26 | Selector subcuadra con intersección en `verificar.html` e `registrar_infraccion.html`: `SUBCUADRAS_*` incluye `entre_calles`, datalist muestra "500 — E/ X y Y", matching 4 niveles, párrafo referencia. Fix bug en `registrar_infraccion.html`: `altura` era string en lugar de número. |
| 27 | 2026-09-30 | **UX subcuadra + preselección + API JSON (Fase 2).** `estacionar_vehiculo.html`: selector subcuadra compacto con datalist, GPS auto-trigger, preselección de vehículo por patente desde URL, patente en botón confirmar ("✅ AA123BB — $5.20"), abono activo bloquea seccciones correctamente. `views_api.py`: `GET /api/conductor/dashboard/` y `GET /api/conductor/estacionamientos/activos/` como `JsonResponse` puro. Migración `0101` (`SolicitudEliminacionCuenta`) con `SeparateDatabaseAndState` — tabla ya existía en producción. |
| 30 | 2026-10-01 | **Fase 4C React — FormularioEstacionar.** `GET /api/conductor/datos-estacionar/`: devuelve vehículos, subcuadras, opciones duración (auto y moto separadas), saldo, tarifa efectiva con descuento, flags horario/geoloc. `POST /api/conductor/estacionar/`: valida horario, duración, resolve subcuadra, llama `ejecutar_estacionamiento` use case, setea `notif_infraccion_pendiente` en sesión, devuelve `{ok, redirect_url, info_infraccion}`. `formulario_estacionar_conductor.js`: componente React con GPS (`detectarSubcuadraCercana` + `capturarCoordsGps`), cascade subcuadra calle→altura (React state), tarjetas vehículo con eliminar vía fetch, botones duración, aviso abono activo, zona libre, saldo insuficiente, submit a API, redirect sin recarga. `estacionar_vehiculo.html`: mount point React + fallback Django `#formulario-estacionar-fallback` (oculto al montar). `views_api.py` imports limpios (consolidado `calcular_opciones_duracion` en un solo bloque). |
| 29 | 2026-09-30 | **Fase 4A + 4B React en producción.** 4A: `HistorialConductor` (`historial_conductor.js`) en `/mis_estacionamientos/` — paginación sin recarga, expand/collapse, fallback Django. 3 endpoints nuevos en `views_api.py`: `api_conductor_historial`, `api_conductor_opciones_renovar`, `api_conductor_renovar`. Modal inline `ModalRenovar` en `PanelEstado` — "Extender" ya no navega a página separada, actualiza timer en vivo. Fix `calcular_opciones_duracion` (`services/horarios.py`): respeta `duracion_minima_min` en franja final (< 60 min disponibles). Fix comentario multilinea `{# #}` con null bytes renderizado como texto en `inicio_usuarios.html`. 4B: `MisVehiculos` (`mis_vehiculos_conductor.js`) en `/inicio/` — badges 🟢/🔵/⚪ por estado, infracciones pendientes, exento, links historial/infracciones. Fix badge abono: comparación por `vehiculo_id` en vez de patente string. |
| 28 | 2026-09-30 | **Fase 3 React en producción.** `PanelEstado` component (`static/app_estacionamiento/js/panel_estado_conductor.js`): React 18 UMD sin JSX, `React.createElement`, `useState`/`useEffect`, contador regresivo, polling 30s, 5 estados (cargando/error/fuera horario/activo/sin activo). `inicio_usuarios.html`: reemplaza bloque Django de 60 líneas. React servido desde static propio (no CDN). Fix: comentario Django `{# ... #}` con `<script>` en texto se renderizaba como HTML literal → `SyntaxError: Unexpected identifier 'y'`. Migración `0102`: `AlterField` `help_text`/`verbose_name` en `Subcuadra.calles_entre/interseccion_1/interseccion_2` (no-op en BD). |
| 26 | 2026-09-29 | **Fix bug Error 500 `/admin/caja-vendedores/{id}/forzar/`.** Causa: `periodo="Cierre forzado por admin"` (22 chars) en `CharField(max_length=10, choices=PERIODOS)` → `DataError` en PostgreSQL (silencioso en SQLite local). Fix: `generar_cierre_caja()` acepta `creado_por=None` opcional; `forzar_cierre_vendedor` llama sin `periodo` y pasa `creado_por=request.user` para registrar al admin. Test nuevo `test_cierre_forzado_por_admin_registra_creado_por`. Push notifications en producción: VAPID keys en Railway, cron `*/5 * * * *` (mínimo Railway), ventana alerta ±3 min. Duración mínima testing: opciones 5/10/15/20 min en admin, validación dinámica en conductor. Fixes UX: timer "VENCIDO" → "⏰ Tiempo vencido" + clearInterval; confirm dialog limpio; `Estacionamiento.duracion_horas` y `PreferenciaEstacionamiento.duracion_horas` → `decimal_places=4` (migración 0100) para representar exactamente 10 min (0.1667h). |
| 25 | 2026-09-28 | **Web Push + acuse de anulación.** `SuscripcionPush` model · `Infraccion.notificado_anulacion_en/ip` · `Municipio.minutos_alerta_push` · Migración `0099` · `views_push.py`: endpoints `/push/vapid-public-key/`, `/push/suscribir/`, `/push/acuse-anulacion/<id>/` · `pywebpush` en requirements · VAPID vars en settings · sw.js extendido con eventos `push` + `notificationclick` · `inicio_usuarios.html` suscribe al cargar (solo si `minutos_alerta_push > 0`) · management command `enviar_alertas_vencimiento` (cron Railway `*/1 * * * *`) · Push automática al anular infracción desde admin (`_enviar_push_anulacion`) · `detalle_patente.html`: banners claros por estado (pendiente/pagada/anulada) + botón "Confirmar que me notifiqué" con fetch sin recarga · `editar_municipio.html`: campo numérico `minutos_alerta_push` con instrucciones de cron. |
| 33 | 2026-10-01 | **Ticket config superadmin + Fase 5B.** `Municipio.ticket_fuente_size` (1-3) y `ticket_qr_size` (1-8) — migración `0103`. `editar_municipio.html` expone los campos. `generarTicketInfraccion(d)` usa `d.fuente_size`/`d.qr_size` (ESC/POS dinámico). **Fase 5B**: `POST /api/inspector/registrar_infraccion/` (multipart: foto + patente + subcuadra + GPS → devuelve `datos_acta`). `verificar_inspector.js` reescrito con 3 fases: `FormularioInfraccion` (foto, GPS, cascade) + `ModalTicket` (2 copias BLE, reconexión silenciosa, confirmación manual/auto). `verificar.html` carga `impresora_bluetooth.js` antes del componente; mount point con `data-url-registrar` y `data-geoloc`. Fix BLE: inspector ya no navega entre páginas → sesión Bluetooth sobrevive todo el flujo verificar → infraccionar → imprimir. |
