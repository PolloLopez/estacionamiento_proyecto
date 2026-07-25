# CONTEXT.md — Sistema de Estacionamiento Medido
https://github.com/leandrolopezalbini/estacionamiento.git
> Referencia fija del proyecto. No incluye tareas pendientes ni cambios en curso → ver PENDIENTES.md.

Última actualización estructural: 2026-07-22

---

## Proyecto

Sistema web de gestión de estacionamiento medido para municipios.
Permite que conductores registren estacionamientos, inspectores labren infracciones,
vendedores cobren en efectivo y administradores gestionen el sistema por completo.

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
DATABASE_URL          # PostgreSQL (Railway add-on)
SITE_ID               # 2 (para allauth)
GOOGLE_CLIENT_ID, GOOGLE_CLIENT_SECRET
MP_ACCESS_TOKEN, MP_PUBLIC_KEY, MP_CLIENT_ID, MP_CLIENT_SECRET
CLOUDINARY_CLOUD_NAME, CLOUDINARY_API_KEY, CLOUDINARY_API_SECRET
EMAIL_HOST_USER, EMAIL_HOST_PASSWORD, DEFAULT_FROM_EMAIL
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
| Excel | openpyxl | Exportación de estadísticas (pendiente) |
| Frontend | HTML + CSS propio | Sin frameworks JS |
| Deploy | Railway + Gunicorn + WhiteNoise | PaaS simple |
| Tests | Django TestCase | 89 tests |

---

## Arquitectura

```
views_*.py  →  use_cases/  →  services/  →  domain/
                                          →  models.py
```

**views.py** — fachada pura (98 líneas), re-exporta desde módulos por rol. No define vistas.

**Módulos de vistas (Sprint 1 — TRAMA):**
- `views_auth.py` — login, logout, registro, completar_perfil, OAuth
- `views_conductor.py` — estacionar, historial, infracciones, vehículos
- `views_inspector.py` — panel, verificar patente, infracciones, PDF
- `views_vendedor.py` — cobros, abono mensual, caja, comisiones
- `views_admin.py` — gestión completa del municipio
- `views_tesorero.py` — panel tesorero, validar/observar rendiciones del admin, depositar comisiones de vendedores
- `views_mp.py` — integración MercadoPago (carga de saldo)

**services/ (Sprint 2 — TRAMA):**
- `services/horarios.py` — `puede_estacionar_ahora()`, `calcular_opciones_duracion()`, `obtener_tarifa_hora()`, `cerrar_estacionamientos_vencidos_por_horario()`
- `services/infracciones.py` — `crear_infraccion()`, `cobrar_infraccion_efectivo()`, `calcular_estado_tolerancia()` (con `MARGEN_TOLERANCIA_SEGUNDOS = 60`)
- `services/saldo.py` — `cargar_saldo_conductor()`, `debitar_saldo_conductor()`
- `services/caja.py` — `generar_cierre_caja()`, `registrar_cobro_efectivo()`
- `services/verificacion.py` — `verificar_estado_vehiculo()`

**use_cases/ (Sprint 3 — TRAMA):** delegan en services/, sin lógica inline.
- `estacionar_vehiculo.py`, `pagar_infraccion.py`, `cobrar_estacionamiento.py`
- `finalizar_estacionamiento.py`, `registrar_infraccion.py`, `acreditar_saldo_mp.py`

**domain/:**
- `vehiculo_policy.py` — warnings por tipo de vehículo
- `saldo_policy.py` — `tiene_saldo(usuario, monto)`

**Shims de compatibilidad:** `services_caja.py`, `services_infracciones.py`, `services_verificacion.py`
— 4 líneas cada uno, re-exportan desde `services/` para no romper imports viejos.

**utils.py** — `get_subcuadra_default()` + `sanitizar_patente()` (elimina todo lo que no sea alfanumérico y convierte a mayúsculas).

**middleware.py** — redirige conductores sin `first_name` a `completar_perfil` (flujo OAuth y registro email).

**factories.py** — `EstacionamientoFactory.crear()` centraliza creación con estado inicial.

---

## Modelo de datos — entidades principales

| Modelo | Descripción |
|--------|-------------|
| `Usuario` | AbstractUser con `correo` como USERNAME_FIELD. Flags: `es_admin`, `es_inspector`, `es_vendedor`, `es_conductor`, `es_tesorero`. Campos: `saldo`, `saldo_operativo`, `es_verificado`, `municipio`. |
| `Municipio` | Configuración del municipio: `comision_vendedor (%)`, `tolerancia_multa_minutos`, `precio_hora`, branding (logo, colores). |
| `Vehiculo` | Patente única. Tipos: `auto`, `moto`. Exenciones: `exento_global`, `exento_parcial`, `subcuadras_exentas`. |
| `VehiculoUsuario` | Relación N:N entre vehículo y conductor. |
| `Subcuadra` | Calle + altura + municipio. Unique together. |
| `Estacionamiento` | Estado: `ACTIVO` / `FINALIZADO`. `hora_inicio`, `hora_fin`, `duracion_horas`, `costo_base`, `costo_final`. Constraint: un ACTIVO por vehículo. |
| `Infraccion` | Estado: `pendiente` / `pagada` / `anulada`. `monto`, `motivo`, `foto` (ImageField → Cloudinary en Railway), `motivo_anulacion`, `fecha_pago`, `creado_en`. |
| `MovimientoCaja` | Registro contable de cada cobro. `tipo`: `ingreso`/`egreso`. `medio_pago`: `efectivo`/`mercadopago`. `comision_monto`. |
| `CierreCaja` | Cierre de turno de inspector/vendedor. Incluye `ganancia_usuario` y `monto_municipio`. |
| `AbonoMensual` | Habilita estacionamiento libre por un mes. `mes` (primer día del mes), `vehiculo`, `municipio`, `vendedor` (null si lo paga el conductor). `medio_pago`: `efectivo` / `mercadopago` / `saldo`. |
| `Tarifa` | `precio_por_hora`, `precio_por_hora_moto`, `precio_abono_auto`, `precio_abono_moto`. |
| `HorarioEstacionamiento` | Horario semanal por día (`dia_semana` 0-6). `hora_inicio`, `hora_fin`. |
| `DiaEspecial` | Feriados o días sin cobro. `fecha`, `cobro_activo`. |
| `VerificacionInspector` | Resultado de verificar una patente. Estado del vehículo en el momento. |
| `SolicitudVerificacion` | El conductor pide verificación de identidad al admin. |
| `Rendicion` | El admin cierra un período y genera totales (efectivo/digital/comisiones/neto) para el tesorero. Estado: `pendiente`/`validada`/`observada`. El tesorero registra quién validó y cuándo (`tesorero`, `validado_en`). |
| `LiquidacionComision` | Pago de comisiones acumuladas a un vendedor. Flujo: `pendiente` → `depositada` (tesorero) → `certificada` (vendedor). |
| `DestinatarioInforme` | Personas que reciben el informe mensual por email. `nombre`, `correo`, `activo`, `municipio`. |
| `Notificacion` | Notificaciones internas al conductor. |

---

## Roles y reglas de negocio

**Tolerancia de gracia:** si el conductor (o el vendedor) resuelve una infracción dentro de `municipio.tolerancia_multa_minutos` desde que fue labrada, se anula automáticamente sin cobrar. El chequeo ocurre en dos momentos: al estacionar el vehículo (use case `estacionar_vehiculo`) y al pagar explícitamente desde "Mis infracciones" o "Cobrar infracción" (vendedor). Pasado el plazo, se cobra el monto (saldo digital o efectivo). Centralizado en `calcular_estado_tolerancia()` de `services/infracciones.py`; incluye margen de 60 segundos para evitar cobrar por diferencias mínimas.

**Exenciones:** exento global → nunca paga. Exento parcial → libre en sus subcuadras exentas, paga en el resto. El inspector ve el estado al verificar la patente.

**Abono mensual:** una vez cobrado para un mes/vehículo/municipio, no se puede cobrar de nuevo (unique constraint). El inspector lo ve al verificar la patente. Puede cobrarlo el vendedor (en efectivo, con comisión), el admin (sin comisión, 100% a tesorería) o el propio conductor (con saldo digital, `vendedor=null`). El vehículo se crea automáticamente si no existe (`get_or_create`) — no requiere registro previo.

**Comisión vendedor:** se calcula `monto * comision_vendedor% / 100` al cobrar y se guarda en `MovimientoCaja.comision_monto`. Se acumula hasta que el tesorero genera una `LiquidacionComision`.

**Duración mínima de estacionamiento:** 1 hora. La opción de 30 minutos fue eliminada. `calcular_opciones_duracion()` en `services/horarios.py` arranca desde `n=2` (1.0h).

**Reintegro por cancelación temprana:** si el conductor finaliza el estacionamiento antes de `UMBRAL_REINTEGRO_MINUTOS = 30` minutos, se devuelve el 100% del `costo_base` a su saldo y el `costo_final` queda en 0. El reintegro se registra como `MovimientoCaja(tipo="ingreso")`. Lógica centralizada en `use_cases/finalizar_estacionamiento.py`.

**Patentes sanitizadas:** `sanitizar_patente(patente)` en `utils.py` elimina todo lo que no sea alfanumérico y convierte a mayúsculas. Se aplica en todas las vistas que reciben patente (inspector, vendedor, conductor, admin) y en todos los templates vía handler JS `oninput`.

**Saldo doble-check:** antes de estacionar se verifica saldo optimista (sin lock) y luego dentro de `select_for_update()` para evitar race conditions.

**Login:** `correo` como username. Google OAuth disponible. Conductores sin `first_name` son redirigidos a `completar_perfil` por el middleware. El formulario de registro (`RegistroUsuarioForm`) pide `nombre` y `apellido` desde el inicio para evitar este redirect.

**Rendición a tesorería:** el admin genera una `Rendicion` con desglose de efectivo/digital/comisiones. La vista `crear_rendicion` pre-completa `fecha_desde` con el día siguiente a la última rendición del admin. El tesorero puede marcarla como `validada` (recibida) u `observada` (con notas). El admin ve sus propias rendiciones y su estado en la página de rendiciones. El vendedor ve sus cierres de caja pendientes de certificación en su panel.

**Multi-municipio:** cada municipio tiene su propia tarifa, horario, inspectores y vendedores. Los datos no se cruzan entre municipios.
