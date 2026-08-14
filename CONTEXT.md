# CONTEXT.md — Sistema de Estacionamiento Medido
> Referencia fija del proyecto. No incluye tareas pendientes ni cambios en curso → ver PENDIENTES.md.

Última actualización estructural: 2026-08-14

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
BREVO_API_KEY                   # email transaccional (pendiente configurar)
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
| Pagos | MercadoPago SDK (producción real) | Carga de saldo online |
| Media storage | Cloudinary (cdn) / filesystem (local) | Fotos de infracciones persistentes en Railway |
| Imágenes | Pillow | Watermark GPS sobre fotos de actas |
| PDF | reportlab | PDF de infracciones para juzgado de faltas |
| Excel | openpyxl | Exportación estadísticas inspectores |
| Seguridad | django-axes | Rate limiting en login (5 intentos, 1h cooloff) |
| Error tracking | Sentry (django-sentry-sdk) | Alertas de errores en Railway |
| Email | django-anymail + Brevo | API transaccional (pendiente verificar remitente) |
| Frontend | HTML + CSS propio | Sin frameworks JS |
| Deploy | Railway + Gunicorn + WhiteNoise | PaaS simple |
| Tests | Django TestCase | 155 tests |

---

## Arquitectura

```
views_*.py  →  use_cases/  →  services/  →  domain/
                                          →  models.py
```

**views.py** — fachada pura (~100 líneas), re-exporta desde módulos por rol. No define vistas.

**Módulos de vistas:**
- `views_auth.py` — login, logout, registro, completar_perfil, OAuth
- `views_conductor.py` — estacionar, historial, infracciones, vehículos
- `views_inspector.py` — panel, verificar patente, infracciones, PDF, `subcuadra_cercana` (API GPS)
- `views_vendedor.py` — cobros, abono mensual, caja, comisiones
- `views_admin.py` — gestión completa del municipio
- `views_tesorero.py` — panel tesorero, validar/observar rendiciones, depositar comisiones
- `views_superadmin.py` — gestión de municipios, admins y módulos (rol superadmin)
- `views_mp.py` — integración MercadoPago (carga de saldo conductores + webhook unificado)
- `views_pago_publico.py` — pago sin registro: buscar por patente, pagar infracción/estacionamiento/abono vía MP
- `views_pwa.py` — manifest.json y service worker para PWA

**services/:**
- `services/horarios.py` — `puede_estacionar_ahora()`, `calcular_opciones_duracion()`, `obtener_tarifa_hora()`, `cerrar_estacionamientos_vencidos_por_horario()`
- `services/infracciones.py` — `crear_infraccion()`, `cobrar_infraccion_efectivo(medio_pago='efectivo')`, `calcular_estado_tolerancia()` (con `MARGEN_TOLERANCIA_SEGUNDOS = 60`). Constante exportada: `MEDIOS_VALIDOS_COBRO = frozenset({"efectivo","transferencia","debito","credito","qr"})`. Normaliza valores inválidos a `'efectivo'`.
- `services/saldo.py` — `cargar_saldo_conductor()`, `debitar_saldo_conductor()`
- `services/caja.py` — `generar_cierre_caja()` (calcula desglose por medio de pago en una sola query de agregación condicional), `registrar_cobro_efectivo()`
- `services/verificacion.py` — `verificar_estado_vehiculo()`

**use_cases/:** delegan en services/, sin lógica inline.
- `estacionar_vehiculo.py`, `pagar_infraccion.py`, `cobrar_estacionamiento.py`
- `finalizar_estacionamiento.py`, `registrar_infraccion.py`, `acreditar_saldo_mp.py`
- `procesar_pago_publico.py` — idempotente: marca infraccion pagada, crea Estacionamiento o AbonoMensual según tipo. Usa `select_for_update()`.

**domain/:**
- `vehiculo_policy.py` — warnings por tipo de vehículo
- `saldo_policy.py` — `tiene_saldo(usuario, monto)`

**Shims de compatibilidad:** `services_caja.py`, `services_infracciones.py`, `services_verificacion.py`
— re-exportan desde `services/` para no romper imports viejos.

**utils.py** — `get_subcuadra_default()` + `sanitizar_patente()`.

**middleware.py** — redirige conductores sin `first_name` a `completar_perfil`.

**factories.py** — `EstacionamientoFactory.crear()` centraliza creación con estado inicial.

---

## Modelo de datos — entidades principales

| Modelo | Descripción |
|--------|-------------|
| `Usuario` | AbstractUser con `correo` como USERNAME_FIELD. Flags: `es_admin`, `es_inspector`, `es_vendedor`, `es_conductor`, `es_tesorero`, `es_superadmin`. Campos: `saldo` (wallet digital conductor), `saldo_operativo` (caja del vendedor/inspector), `es_verificado`, `municipio`, `porcentaje_ganancia`. |
| `Municipio` | Configuración del municipio: `comision_vendedor (%)`, `tolerancia_multa_minutos`, branding (logo, colores). |
| `ModuloMunicipio` | Feature flags por municipio (activo/inactivo). Gestionado por superadmin. |
| `Vehiculo` | Patente única. Tipos: `auto`, `moto`. Exenciones: `exento_global`, `exento_parcial`, `subcuadras_exentas`. |
| `VehiculoUsuario` | Relación N:N entre vehículo y conductor. |
| `Subcuadra` | Calle + altura + municipio. `unique_together = (calle, altura, municipio)`. `lat`/`lon` (DecimalField, null) para GPS preselección desde `verificar.html`. El admin las carga desde `/admin-subcuadras/` con mapa Leaflet/OSM (sin API key). |
| `Estacionamiento` | Estado: `ACTIVO` / `FINALIZADO`. `hora_inicio`, `hora_fin`, `duracion_horas (DecimalField)`, `costo_base`, `costo_final`. Constraint: un ACTIVO por vehículo. |
| `Infraccion` | Estado: `pendiente` / `pagada` / `anulada`. `monto`, `motivo`, `foto` (ImageField → Cloudinary en Railway), `motivo_anulacion`, `fecha_pago`, `creado_en`. |
| `MovimientoCaja` | Registro contable de cada cobro. `tipo`: `ingreso`/`egreso`. `medio_pago`: `efectivo`, `transferencia`, `debito`, `credito`, `qr`, `mercadopago` (default `efectivo`). `comision_monto`. `cerrado`: True cuando el movimiento fue incluido en un CierreCaja. |
| `CierreCaja` | Cierre de turno de inspector/vendedor. `total_cobrado`, `ganancia_usuario`, `monto_municipio`. Desglose automático: `total_efectivo`, `total_transferencia`, `total_digital` (débito+crédito+QR). FK `rendicion → Rendicion (SET_NULL)`: null = pendiente de rendir. |
| `AbonoMensual` | Habilita estacionamiento libre por un mes. `mes`, `vehiculo`, `municipio`, `vendedor`. `medio_pago`: `efectivo` / `mercadopago` / `saldo`. `conductor` y `vendedor` nullable (pagos públicos anónimos). |
| `PagoPublico` | Registro de pagos via MP sin cuenta de usuario. `tipo`: `infraccion`/`estacionamiento`/`abono`. `estado`: `pendiente`/`aprobado`/`fallido`. FK nullable a `Infraccion`, `Estacionamiento`, `AbonoMensual`. `mp_preference_id`, `mp_payment_id (unique)`, `email_contacto`, `patente`, `duracion_horas`, `mes_abono`, `subcuadra`. Webhook MP detecta `metadata.pago_publico_id` para rutear. |
| `Tarifa` | `precio_por_hora`, `precio_por_hora_moto`, `precio_abono_auto`, `precio_abono_moto`. |
| `HorarioEstacionamiento` | Horario semanal por día (`dia_semana` 0-6). `hora_inicio`, `hora_fin`. |
| `DiaEspecial` | Feriados o días sin cobro. `fecha`, `cobro_activo`. |
| `VerificacionInspector` | Resultado de verificar una patente. Índice compuesto `(vehiculo_id, fecha DESC)`. |
| `SolicitudVerificacion` | El conductor pide verificación de identidad al admin. |
| `Rendicion` | El admin cierra un período seleccionando CierreCaja certificados. Totales **calculados automáticamente** del desglose de los cierres elegidos: `total_efectivo`, `total_digital` (transferencia+débito+crédito+QR agrupados), `total_neto = efectivo + digital`. `comprobante_archivo` para adjuntar comprobante de transferencia. Estado: `pendiente`/`validada`/`observada`. El tesorero registra quién validó y cuándo. |
| `LiquidacionComision` | Pago de comisiones a un vendedor. Flujo: `pendiente` → `depositada` (tesorero) → `certificada` (vendedor). `factura_presentada (BooleanField)` + `factura_archivo (FileField)` para el comprobante de factura del vendedor. |
| `DestinatarioInforme` | Personas que reciben el informe mensual por email. |
| `PlantillaDocumento` | *(pendiente)* Texto personalizable por municipio para cada tipo de comprobante/acta. Tipos: `acta`, `cobro_hora`, `abono`, `cobro_infraccion`, `anulacion`. Campos: `encabezado`, `cuerpo`, `pie`. Si no existe plantilla → usa texto hardcodeado actual. |
| `Notificacion` | Notificaciones internas al conductor. |

---

## Roles y reglas de negocio

**Tolerancia de gracia:** si el conductor (o el vendedor) resuelve una infracción dentro de
`municipio.tolerancia_multa_minutos` desde que fue labrada, se anula automáticamente sin cobrar.
Centralizado en `calcular_estado_tolerancia()` de `services/infracciones.py`; incluye margen de
60 segundos para evitar cobrar por diferencias mínimas.

**Exenciones:** exento global → nunca paga. Exento parcial → libre en sus subcuadras exentas,
paga en el resto. El inspector ve el estado al verificar la patente.

**Abono mensual:** unique constraint (mes + vehículo + municipio). Puede cobrarlo el vendedor
(con comisión), el admin (sin comisión, 100% a tesorería) o el propio conductor (con saldo digital).
El vehículo se crea automáticamente si no existe.

**Comisión vendedor:** `monto * comision_vendedor% / 100` al cobrar, guardado en
`MovimientoCaja.comision_monto`. Se acumula hasta que el tesorero genera una `LiquidacionComision`.

**Duración mínima de estacionamiento:** 1 hora. `calcular_opciones_duracion()` arranca desde `n=2`.

**Reintegro por cancelación temprana:** si el conductor finaliza antes de
`UMBRAL_REINTEGRO_MINUTOS = 30`, se devuelve el 100% del `costo_base`. Centralizado en
`use_cases/finalizar_estacionamiento.py`.

**Debitar saldo conductor:** `debitar_saldo_conductor()` en `services/saldo.py` NO abre su propia
transacción. Debe llamarse desde dentro de un `transaction.atomic()` con `select_for_update()` ya
activo. El estacionamiento se descuenta al activarlo (no cuando el inspector verifica).

**Flujo financiero completo:**
1. Conductor activa estacionamiento → `debitar_saldo_conductor()` → `conductor.saldo ↓` + `MovimientoCaja(conductor, egreso)`
2. Vendedor cobra en persona → `MovimientoCaja(vendedor, ingreso, medio_pago=...)` → `vendedor.saldo_operativo ↑`
3. Vendedor cierra caja → `generar_cierre_caja()` → calcula desglose por medio_pago en 1 query → `CierreCaja` creado → movimientos `cerrado=True`
4. Admin certifica cierre → revisa el desglose efectivo/digital
5. Admin crea rendición → selecciona CierreCaja certificados con checkboxes → totales calculados automáticamente → `CierreCaja.rendicion FK` vinculado → `Rendicion` creada
6. Tesorero valida rendición → marca `validada` o `observada`
7. Tesorero paga comisiones → `LiquidacionComision(depositada)` → vendedor certifica recibo → puede adjuntar factura

**Medios de pago (MovimientoCaja.medio_pago):**
- `efectivo`: el cobrador recibe cash y lo rinde físicamente al admin.
- `transferencia`: va a la cuenta personal del vendedor; se rinde en efectivo o con nueva transferencia.
- `debito`, `credito`, `qr`: van directo a tesorería (no pasan por el vendedor físicamente).
- `mercadopago`: carga de saldo online del conductor (webhook MP → `acreditar_saldo_mp`).

En el CierreCaja: `total_transferencia` y `total_digital` se calculan por separado.
En la Rendición: `total_digital = total_transferencia + total_digital` (tesorería los agrupa porque ninguno es efectivo físico).

**Rendición a tesorería:** el admin selecciona cierres certificados (certificado=True, rendicion=null).
Los totales son calculados por el sistema, no hay entrada manual. El admin puede adjuntar comprobante
de transferencia. Las comisiones de vendedores son gestionadas por tesorería aparte via LiquidacionComision.

**Multi-municipio:** cada municipio tiene su propia tarifa, horario, inspectores y vendedores.
Los datos no se cruzan entre municipios. Patrón obligatorio en todas las vistas:
```python
get_object_or_404(Modelo, id=pk, municipio=request.user.municipio)
# Nunca: Modelo.objects.get(id=pk)  ← no filtra por municipio
```

**Concurrencia:** todo cobro usa `transaction.atomic()` + `select_for_update()`:
```python
with transaction.atomic():
    obj = Modelo.objects.select_for_update().get(pk=...)
    # modificar y guardar
```
Modelos que requieren este patrón: `Usuario` (saldo), `MovimientoCaja`, `Infraccion`.

**Cierre reactivo (sin Celery):** los estacionamientos vencidos se cierran al acceder a
`inicio_usuarios` y al verificar una patente. Pull-based: no hay tareas programadas.

**Cache:** `puede_estacionar_ahora(municipio)` cacheada 1 hora por clave `municipio+fecha+hora`.
Se invalida automáticamente al cambiar el tramo horario.

**Patentes sanitizadas:** `sanitizar_patente()` en `utils.py` — alfanumérico, mayúsculas, en todas
las vistas y templates via handler JS `oninput`.

**Saldo doble-check:** antes de estacionar se verifica saldo optimista (sin lock) y luego dentro
de `select_for_update()` para evitar race conditions.

---

## URLs de referencia

```
/usuarios/                                     → inicio conductor
/usuarios/admin-inicio/                        → panel admin
/usuarios/admin-usuarios/                      → gestionar conductores
/usuarios/admin-usuarios/<id>/                 → detalle conductor (cambiar contraseña)
/usuarios/admin-inspectores/                   → gestionar inspectores
/usuarios/admin-inspectores/estadisticas/      → estadísticas + exportar Excel
/usuarios/admin-vendedores/                    → gestionar vendedores
/usuarios/admin-infracciones/                  → infracciones (cobrar / anular / PDF juzgado)
/usuarios/admin-rendiciones/                   → rendiciones (crear / certificar cierres)
/usuarios/admin-exenciones/                    → exenciones de vehículos
/usuarios/admin-subcuadras/                    → gestionar subcuadras + asignar coordenadas GPS (mapa Leaflet)
/usuarios/inspectores/                         → panel inspector
/usuarios/inspectores/verificar/               → verificar patente en calle (preselección GPS si hay coordenadas cargadas)
/usuarios/inspectores/subcuadra-cercana/       → API JSON: subcuadra más cercana por lat/lon (uso interno del template)
/usuarios/inspectores/infraccion/              → labrar acta
/usuarios/inspectores/resumen/                 → mis infracciones del día
/usuarios/vendedores/                          → panel vendedor
/usuarios/vendedores/cobrar-infraccion/        → cobrar multa en efectivo
/usuarios/vendedores/cobrar-abono/             → cobrar abono mensual
/usuarios/vendedores/caja/                     → resumen de caja del vendedor
/usuarios/vendedores/comisiones/               → mis liquidaciones de comisión
/usuarios/vendedores/comisiones/<id>/factura/  → presentar factura de comisión
/usuarios/tesorero/                            → panel tesorero
/usuarios/mp/cargar/                           → iniciar carga MercadoPago
/usuarios/pagar/                               → buscar patente (pago público sin registro)
/usuarios/pagar/<patente>/                     → detalle: infracciones + form estacionar + form abono
/usuarios/pagar/infraccion/<id>/               → iniciar pago infracción (POST → MP)
/usuarios/pagar/estacionar/                    → iniciar pago estacionamiento (POST → MP)
/usuarios/pagar/abono/                         → iniciar pago abono mensual (POST → MP)
/usuarios/pagar/subcuadra-cercana/             → API GPS pública (sin auth)
/usuarios/manifest.json                        → PWA manifest
/usuarios/sw.js                                → PWA service worker
/usuarios/mis-infracciones/                    → infracciones del conductor
/usuarios/consultar-deuda/                     → buscar deuda por patente (conductor/vendedor)
/sistema-interno/                              → Django Admin (URL no obvia, reduce bruteforce)
```
