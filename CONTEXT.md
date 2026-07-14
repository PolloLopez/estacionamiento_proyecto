# CONTEXT.md — Sistema de Estacionamiento Medido

> Referencia fija del proyecto. No incluye tareas pendientes ni cambios en curso → ver PENDIENTES.md.

Última actualización estructural: 2026-07-14

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
| Producción | Railway (pendiente reactivar) | — |
| Local | `python manage.py runserver` | http://localhost:8000 |

Variables de entorno requeridas:
```
SECRET_KEY
DATABASE_URL         # PostgreSQL en prod, SQLite en local
DEBUG                # False en prod
SITE_ID              # 2 en Railway (para allauth)
CSRF_TRUSTED_ORIGINS # https://dominio.railway.app
MP_ACCESS_TOKEN      # MercadoPago
MP_PUBLIC_KEY        # MercadoPago
```

Git flow: `develop` → trabajo activo · `main` → Railway auto-deploy.

---

## Stack

| Capa | Tecnología | Motivo |
|------|-----------|--------|
| Backend | Django 5.x, Python 3.12 | Framework principal |
| Base de datos | SQLite (local) / PostgreSQL (prod) | Railway provee Postgres |
| Autenticación | django-allauth + Google OAuth | Login social + email |
| Pagos | MercadoPago SDK | Carga de saldo online |
| PDF | reportlab | PDF de infracciones del día |
| Frontend | HTML + CSS propio | Sin frameworks JS |
| Deploy | Railway + gunicorn + WhiteNoise | PaaS simple |
| Tests | Django TestCase | 95+ tests, sin pytest |

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
- `views_tesorero.py` — rendiciones, depositar comisiones
- `views_mp.py` — integración MercadoPago (carga de saldo)

**services/ (Sprint 2 — TRAMA):**
- `services/horarios.py` — `puede_estacionar_ahora()`, `calcular_opciones_duracion()`, `obtener_tarifa_hora()`, `cerrar_estacionamientos_vencidos_por_horario()`
- `services/infracciones.py` — `crear_infraccion()`, `cobrar_infraccion_efectivo()`
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

**utils.py** — 32 líneas, solo `get_subcuadra_default()`.

**middleware.py** — redirige conductores sin `first_name` a `completar_perfil` (flujo OAuth).

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
| `Infraccion` | Estado: `pendiente` / `pagada` / `anulada`. `monto`, `motivo`, `foto`, `fecha_pago`, `creado_en`. |
| `MovimientoCaja` | Registro contable de cada cobro. `tipo`: `ingreso`/`egreso`. `medio_pago`: `efectivo`/`mercadopago`. `comision_monto`. |
| `CierreCaja` | Cierre de turno de inspector/vendedor. Incluye `ganancia_usuario` y `monto_municipio`. |
| `AbonoMensual` | Habilita estacionamiento libre por un mes. `mes` (primer día del mes), `vehiculo`, `municipio`, `vendedor`. |
| `Tarifa` | `precio_por_hora`, `precio_por_hora_moto`, `precio_abono_auto`, `precio_abono_moto`. |
| `HorarioEstacionamiento` | Horario semanal por día (`dia_semana` 0-6). `hora_inicio`, `hora_fin`. |
| `DiaEspecial` | Feriados o días sin cobro. `fecha`, `cobro_activo`. |
| `VerificacionInspector` | Resultado de verificar una patente. Estado del vehículo en el momento. |
| `SolicitudVerificacion` | El conductor pide verificación de identidad al admin. |
| `Rendicion` | El admin cierra un período y genera totales para el tesorero. Estado: `pendiente`/`validada`/`observada`. |
| `LiquidacionComision` | Pago de comisiones acumuladas a un vendedor. Flujo: `pendiente` → `depositada` (tesorero) → `certificada` (vendedor). |
| `Notificacion` | Notificaciones internas al conductor. |

---

## Roles y reglas de negocio

**Tolerancia de gracia:** si el conductor paga una infracción dentro de `municipio.tolerancia_multa_minutos` desde que fue labrada, se anula automáticamente sin cobrar. Pasado ese plazo, se descuenta el monto del saldo.

**Exenciones:** exento global → nunca paga. Exento parcial → libre en sus subcuadras exentas, paga en el resto. El inspector ve el estado al verificar la patente.

**Abono mensual:** una vez cobrado para un mes/vehículo/municipio, no se puede cobrar de nuevo (unique constraint). El inspector lo ve al verificar la patente.

**Comisión vendedor:** se calcula `monto * comision_vendedor% / 100` al cobrar y se guarda en `MovimientoCaja.comision_monto`. Se acumula hasta que el tesorero genera una `LiquidacionComision`.

**Saldo doble-check:** antes de estacionar se verifica saldo optimista (sin lock) y luego dentro de `select_for_update()` para evitar race conditions.

**Login:** `correo` como username. Google OAuth disponible. Conductores sin `first_name` son redirigidos a `completar_perfil` por el middleware.

**Multi-municipio:** cada municipio tiene su propia tarifa, horario, inspectores y vendedores. Los datos no se cruzan entre municipios.
