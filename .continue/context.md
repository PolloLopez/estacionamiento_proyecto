// ESTACIONAMIENTO_PROYECTO/.continue/context.md

# Proyecto
Sistema de Estacionamiento Medido municipal. Gestiona cobro de estacionamiento en vía pública,
infracciones, abonos mensuales y rendición a tesorería. Opera en múltiples municipios desde
una sola base de código con aislamiento completo de datos por municipio.

Deploy en Railway: https://estacionamiento.up.railway.app

# Estado actual
Sistema funcional end-to-end. En fase de testing con la municipalidad.

Funciona hoy:
- Registro y login (email + Google OAuth via allauth)
- Verificación de identidad del conductor con documentación adjunta
- Estacionamiento por horas para autos y motos, con descuento de saldo digital
- Carga de saldo vía MercadoPago (webhook + back_url, idempotente por payment_id)
- Inspector: verifica patentes en calle, genera infracciones con foto y GPS watermark
- Tolerancia de gracia en multas: configurable por municipio (default 5 min), si el conductor paga dentro del plazo la infracción se anula automáticamente sin cobrar
- Conductor: paga infracciones online descontando saldo
- Vendedor: cobra en efectivo (estacionamiento, infracciones, abonos mensuales)
- Comisión automática para vendedores (% configurable por municipio, default 7%)
- Tesorería: panel con rendiciones y liquidaciones de comisiones
- Tesorero deposita comisiones → vendedor certifica recibo
- Exenciones totales y parciales por subcuadra (discapacidad, vecino frentista, jubilado, etc.)
- Abono mensual: acceso libre todo el mes, sin registrar cada estacionamiento
- Horarios de cobro semanales + días especiales (feriados, festivos)
- Cierre de caja para inspectores y vendedores con rendición por período
- Admin: gestión de tarifas, horarios, inspectores, vendedores, usuarios, exenciones, verificaciones

# Stack actual
Django==5.2.8
asgiref==3.11.0
django-allauth[socialaccount]==65.3.0   # Google OAuth
mercadopago==2.2.3
gunicorn==23.0.0
whitenoise==6.8.2
psycopg2-binary==2.9.10
dj-database-url==2.3.0
django-extensions==4.1
Pillow==12.0.0
sqlparse==0.5.3
requests==2.32.3
pandas==2.2.3
openpyxl==3.1.5
numpy==2.2.6
pytest==9.0.1
pytest-django==4.11.1
pytest-cov==6.1.0
geopy==2.4.1

Deploy: Railway (PaaS). DB: PostgreSQL. Estáticos: WhiteNoise. Python: 3.12.

# Arquitectura

## Capas

### Views — app_estacionamiento/views.py (~3100 líneas)
Solo orquestación HTTP. Valida inputs, llama a services/use_cases, hace redirect o render.
Sin lógica de negocio. POST-Redirect-Get en todos los formularios.
Flujos multi-paso con `accion=buscar|confirmar|cobrar` en una sola URL.
Pendiente: dividir en módulos views_admin.py, views_conductor.py, etc.

### Services — services_*.py
Lógica reutilizable con efectos de borde en DB:
- services_caja.py         → generar_cierre_caja(usuario) — cierre atómico con comisión snapshot
- services_infracciones.py → crear_infraccion(...) — valida todo, lanza ErrorInfraccion, graba foto GPS
- services_verificacion.py → verificar_estado_vehiculo(patente, usuario, subcuadra)

### Use Cases — use_cases/
Un módulo por caso de uso. Punto de entrada único: función ejecutar(...).
- estacionar_vehiculo.py    — tarifa según tipo (auto/moto), verifica saldo, crea Estacionamiento
- cobrar_estacionamiento.py — ingreso en caja del vendedor/inspector
- finalizar_estacionamiento.py
- pagar_infraccion.py       — verifica tolerancia de gracia, anula o cobra
- acreditar_saldo_mp.py     — idempotente por payment_id
- registrar_movimiento.py   — crea MovimientoCaja
- registrar_infraccion.py   — wrapper de creación

### Domain — domain/
Sin dependencia del ORM. Objetos de valor y políticas puras:
- enums.py           → EstadoVehiculo: NO_REGISTRADO, IMPAGO, PAGADO, ABONO_ACTIVO,
                       EXENTO_TOTAL, EXENTO_PARCIAL, PENDIENTE_PAGO
- verificacion.py    → ResultadoVerificacion (dataclass): necesita_infraccion(), css_class(), to_dict()
- saldo_policy.py    → SaldoPolicy.tiene_saldo(usuario, costo) → bool
- vehiculo_policy.py → VehiculoPolicy.generar_warnings(...) → list[str]

## Autorización
Decorador propio @require_role(*roles) — retorna 403.html si falla.
Roles = flags booleanos en Usuario:
  "admin"     → is_superuser OR is_staff OR es_admin
  "inspector" → es_inspector
  "vendedor"  → es_vendedor
  "conductor" → es_conductor
  "tesorero"  → es_tesorero
Un usuario puede tener varios roles activos simultáneamente.

## Modelos principales (app_estacionamiento/models.py)

### Usuarios
- Usuario (AbstractUser, USERNAME_FIELD="correo"):
    campos: correo, municipio FK, saldo, saldo_operativo, roles (5 flags bool), es_verificado
    inspectores: telefono, numero_dni, numero_legajo
    vendedores: nombre_propietario, documento_cuil, horario_atencion
    properties: nombre (→first_name), apellido (→last_name), nombre_completo()
- SolicitudVerificacion (OneToOne→Usuario): identidad + exención con archivos adjuntos

### Municipio y configuración
- Municipio: comision_vendedor (Decimal, %), tolerancia_multa_minutos (int), logo, colores branding
- Tarifa: precio_por_hora, precio_por_hora_moto (0=usar auto), monto_infraccion,
          precio_abono_auto, precio_abono_moto
- HorarioEstacionamiento: dia_semana (0-6) + hora_inicio/fin, unique (municipio, dia_semana)
- DiaEspecial: fecha + tipo (feriado/festivo/duelo/otro) + cobro_activo bool
- Subcuadra: calle + altura; altura=0 significa "Zona Única"

### Vehículos y estacionamiento
- Vehiculo: patente (unique), tipo ('auto'|'moto'), exento_global, subcuadras_exentas (M2M)
- VehiculoUsuario: intermedia Usuario↔Vehiculo con es_propietario y verificado
- Estacionamiento: duracion_min (almacena horas, naming confuso), estado ACTIVO/FINALIZADO
    UniqueConstraint: solo un estacionamiento ACTIVO por vehículo
- AbonoMensual: mes=primer día del mes, unique (vehiculo, municipio, mes)

### Cobros y caja
- MovimientoCaja: tipo ingreso/egreso, medio_pago (efectivo/mercadopago), comision_monto
    save() bloquea si cerrado=True
- CierreCaja: snapshot con ganancia_usuario, monto_municipio, porcentaje aplicado
- Rendicion: pendiente/validada/observada — admin genera, tesorero valida
- LiquidacionComision: pendiente/depositada/certificada — tesorero deposita, vendedor certifica

### Infracciones
- Infraccion: monto = snapshot de Tarifa.monto_infraccion al momento de creación
    estado: pendiente/pagada/anulada
    save() hereda municipio del inspector si no se especifica
- VerificacionInspector: registra cada escaneo; base para calcular tolerancia entre verificaciones

## Concurrencia
Todo cobro usa transaction.atomic() + select_for_update(). Patrón consistente:

    with transaction.atomic():
        obj = Modelo.objects.select_for_update().get(id=...)
        # modificar y guardar

Modelos críticos que requieren este patrón: Usuario (saldo), MovimientoCaja, Infraccion.

## Multi-municipio
Todo dato filtrado por request.user.municipio. Usar siempre:
    get_object_or_404(Modelo, id=pk, municipio=municipio)
Nunca .get(id=pk) sin filtro de municipio.

## Cierre reactivo (sin Celery)
Los estacionamientos vencidos se cierran al acceder a inicio_usuarios y al verificar un
vehículo. No hay tareas periódicas — es pull-based al inicio de sesión.

# Reglas

## Lógica de negocio
- Nunca en views. Siempre en services/ o use_cases/.
- Use cases: función ejecutar(...) como único punto de entrada.
- Services: función descriptiva verbo-objeto (crear_infraccion, generar_cierre_caja).

## Seguridad y datos
- Siempre filtrar por municipio. get_object_or_404 con municipio=municipio.
- select_for_update() en todo lo que toque saldo, MovimientoCaja o Infraccion.
- transaction.atomic() en cualquier operación con 2+ escrituras en DB.
- Montos de infracción son snapshots: no cambiar aunque cambie la tarifa.

## Tarifas
- Leer siempre frescos desde DB, nunca hardcodear precios.
- precio_por_hora_moto == 0 significa "usar precio de auto".
- Comisión calculada al momento del cobro, guardada en MovimientoCaja.comision_monto.

## Naming
- Modelos: PascalCase en castellano (MovimientoCaja, CierreCaja).
- Campos y funciones: snake_case en castellano (correo, es_inspector, porcentaje_ganancia).
- URL names con prefijo de rol: inspectores_*, vendedores_*, usuarios_*, admin_*.
- Comentarios y explicaciones en castellano.

## Templates
- POST-Redirect-Get en todos los formularios.
- Flujos multi-paso: parámetro accion= en POST (buscar → confirmar → cobrar).
- base.html tiene branding por municipio (logo, colores CSS variables).

# Pendiente / deuda técnica
- Dividir views.py (~3100 líneas) en módulos por rol (views_admin.py, etc.) — sin riesgo de migration
- admin_rendiciones usa modelo CierreCaja antiguo; debería migrar a nuevo modelo Rendicion
- duracion_min en Estacionamiento almacena horas (naming incorrecto, no cambiar sin migration)
- Tests cubren ~25 casos; faltan tests para: abono mensual, tolerancia multa, comisiones, tesorero
- El commit de los cambios recientes (feat: motos, abono, tesorería) requiere
  eliminar .git/index.lock antes de hacer push desde Windows

Al finalizar actualiza context.md y dame el commit descriptivo del dia. 