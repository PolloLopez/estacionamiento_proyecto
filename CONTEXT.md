# CONTEXT.md — Sistema de Estacionamiento Medido
> Referencia fija del proyecto. No incluye tareas pendientes ni cambios en curso → ver PENDIENTES.md.

Última actualización estructural: 2026-09-06

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
| Frontend | HTML + CSS propio (`global.css`) | Sin frameworks JS. Colores del municipio inyectados como variables CSS en `base.html`. |
| Deploy | Railway + Gunicorn + WhiteNoise | PaaS simple |
| Tests | Django TestCase | ~130 tests (suite estable) |
| Impresora BLE | Web Bluetooth API (`impresora_bluetooth.js`) | Chrome Android (HTTPS). ESC/POS 58mm. Doble copia con pausa configurable (`Municipio.segundos_pausa_doble_copia`): 0=el inspector confirma, >0=pausa automática en segundos. Alias por dispositivo en localStorage. QR nativo `GS(k)`. |

---

## Arquitectura

```
views_*.py  →  use_cases/  →  services/  →  domain/
                                          →  models.py
```

**views.py** — fachada pura (~100 líneas), re-exporta desde módulos por rol. No define vistas.

**Módulos de vistas:**
- `views_auth.py` — login, logout, registro (con logo del municipio), completar_perfil, OAuth
- `views_conductor.py` — estacionar, historial, infracciones, vehículos, sugerencias de mejora, eliminación de cuenta
- `views_inspector.py` — panel, verificar patente, infracciones, PDF, `subcuadra_cercana` (API GPS)
- `views_vendedor.py` — cobros, abono mensual, caja, comisiones
- `views_admin.py` — gestión completa del municipio. Incluye `auditoria_staff` (actividad de vendedores e inspectores con filtro de fechas), `crear_rendicion` (genera automáticamente `LiquidacionComision` por vendedor al crear la rendición)
- `views_tesorero.py` — panel tesorero, `validar_rendicion` (notas obligatorias al observar), `detalle_rendicion`, depositar comisiones
- `views_superadmin.py` — gestión de municipios, admins y módulos
- `views_mp.py` — integración MercadoPago (carga de saldo + webhook unificado)
- `views_pago_publico.py` — pago sin registro: buscar por patente, pagar infracción/estacionamiento/abono vía MP
- `views_pwa.py` — manifest.json y service worker para PWA

**services/:**
- `services/horarios.py` — `puede_estacionar_ahora(municipio, bloquear_sin_horario=False)`: cuando `bloquear_sin_horario=True` y no hay `HorarioEstacionamiento` para el día de hoy, devuelve `(False, "No hay horario...")` sin cachear (para no contaminar el caché del conductor). Usado en vistas del inspector. Cuando `False` (default): sin horario = libre de cobro (conductor). También: `calcular_opciones_duracion()`, `obtener_tarifa_hora()`, `cerrar_estacionamientos_vencidos_por_horario()`.
- `services/infracciones.py` — `crear_infraccion()`, `cobrar_infraccion_efectivo()`, `calcular_estado_tolerancia()` (con `MARGEN_TOLERANCIA_SEGUNDOS = 60`). `MEDIOS_VALIDOS_COBRO = frozenset({"efectivo","transferencia","debito","credito","qr"})`.
- `services/saldo.py` — `cargar_saldo_conductor()`, `debitar_saldo_conductor()`
- `services/caja.py` — `generar_cierre_caja()`, `registrar_cobro_efectivo()`
- `services/verificacion.py` — `verificar_estado_vehiculo()`. Respeta `vigencia_exencion`.
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
| `Usuario` | AbstractUser con `correo` como USERNAME_FIELD. Flags: `es_admin`, `es_inspector`, `es_vendedor`, `es_conductor`, `es_tesorero`, `es_superadmin`. Campos: `saldo` (wallet digital conductor), `saldo_operativo` (caja del vendedor/inspector), `es_verificado`, `municipio`, `porcentaje_ganancia`, `cambio_password_requerido`. |
| `Municipio` | Configuración del municipio. Campos de tarifa/horario. Branding: `logo (ImageField, upload_to="municipios/logos/")`, `color_primario`, `color_secundario`, `color_acento`. Textos: `leyenda_horarios`, `texto_ordenanza`. Opciones: `tolerancia_multa_minutos`, `minutos_entre_infracciones`, `monto_minimo_carga`, `monto_maximo_carga`. Features: `estadisticas_inspectores_activo`, `token_tv (CharField secreto para dashboard público)`. Impresora BLE: `segundos_pausa_doble_copia (PositiveIntegerField, 0=el inspector confirma antes de la copia 2, >0=pausa automática en segundos)`. Facturación: `porcentaje_plataforma`, `cuota_mantenimiento_mensual`, `concepto_recaudacion`. |
| `ModuloMunicipio` | Feature flags premium por municipio (activo/inactivo). Gestionado por superadmin. |
| `Vehiculo` | Patente única. Tipos: `auto`, `moto`. Exenciones: `exento_global`, `tipo_exencion`, `vigencia_exencion (DateField, null=indefinida)`, `exencion_verificada`, `notas_exencion`. Exención parcial: `subcuadras_exentas (M2M)`. Campos SIA: `sia_titular_nombre`, `sia_titular_apellido`, `sia_titular_dni`, `sia_nci`. |
| `Infraccion` | Estado: `pendiente`/`pagada`/`anulada`. `monto`, `motivo`, `foto (ImageField → Cloudinary)`, `descuento_porcentaje`. Campos SIA: `sia_presentado`, `sia_verificado`, `sia_estado`, `sia_url`, `sia_patente_sia`, `sia_nci`, `sia_titular`, `sia_vencimiento`, etc. |
| `VehiculoUsuario` | Relación N:N entre vehículo y conductor. |
| `Subcuadra` | Calle + altura + municipio. `unique_together`. `lat`/`lon` para GPS. Mapa Leaflet/OSM en `/admin-subcuadras/`. |
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
| `SugerenciaMejora` | Cualquier usuario puede enviar sugerencias de mejora. `area` filtrada por rol del usuario (conductor ve áreas de conductor+general, inspector ve inspector+general, etc.). `criticidad`, `estado`. Gestionada por superadmin. |
| `SolicitudEliminacionCuenta` | El conductor puede solicitar darse de baja (soft-delete). Revisada por admin. |
| `Impugnacion` | El conductor impugna una infracción. Revisada por admin. |
| `TransferenciaSaldo` | Transferencia de saldo entre conductores. |
| `Reintegro` | Reintegro por cancelación temprana de estacionamiento. |
| `LiquidacionPlataforma` | Lo que el municipio le paga a la plataforma (Leandro). Iniciada por tesorero o superadmin. |
| `PlantillaDocumento` | Texto personalizable por municipio para comprobantes/actas. Tipos: `acta`, `cobro_hora`, `abono`, `cobro_infraccion`, `anulacion`. |
| `Notificacion` | Notificaciones internas al conductor. |

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
