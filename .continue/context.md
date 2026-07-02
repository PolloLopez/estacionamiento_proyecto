// ESTACIONAMIENTO_PROYECTO/.continue/context.md

# Proyecto
Sistema de Estacionamiento Medido municipal. Gestiona cobro de estacionamiento en vía pública,
infracciones, abonos mensuales y rendición a tesorería. Opera en múltiples municipios desde
una sola base de código con aislamiento completo de datos por municipio.

Deploy en Railway: https://estacionamiento.up.railway.app

---

# Estado actual
Sistema en testing con la municipalidad (fase piloto). Funcional end-to-end.

## Funciones operativas
- Registro y login (email + Google OAuth via allauth)
  → Google popula nombre, apellido y correo automáticamente desde el perfil
  → Sesión siempre persistente (ACCOUNT_SESSION_REMEMBER = True)
- Verificación de identidad del conductor con documentación adjunta
- Estacionamiento por horas para autos y motos
  → Tarifa diferenciada auto/moto (precio_por_hora_moto = 0 → usa precio auto)
  → Límite horario: no se puede estacionar más horas de las que quedan hasta el cierre
  → Cierre reactivo al inicio de sesión y al verificar (sin Celery)
- Carga de saldo vía MercadoPago
  → Webhook + back_url, idempotente por payment_id
  → Exitoso: redirige a inicio_usuarios con mensaje de confirmación
  → Fallido/pendiente: redirige con mensaje adecuado
- Inspector: verifica patentes en calle y genera infracciones
  → Elige tipo (🚗 Auto / 🏍️ Moto) antes de ingresar la patente
  → Si el vehículo no está registrado, se crea con el tipo elegido
  → Si está registrado con tipo distinto, se actualiza
  → Inspector NO puede cobrar estacionamientos (rol cobrador deshabilitado)
- Conductor: paga infracciones online con saldo
- Vendedor: cobra en efectivo (estacionamiento, infracciones, abonos mensuales)
  → Comisión automática calculada al cobrar (% configurable, guardada en comision_monto)
  → Panel de comisiones: mis_comisiones / depositar_comision / certificar_comision
- Abono mensual: acceso libre todo el mes sin registrar sesiones
  → Vendedor cobra, sistema verifica que no tenga abono activo para el mes
  → Inspector ve "Abono mensual activo" al verificar
  → No limitado por horario de cierre
- Tesorería: panel con rendiciones y liquidaciones de comisiones
  → Tesorero deposita → vendedor certifica recibo
- Exenciones totales y parciales por subcuadra
- Horarios de cobro semanales + días especiales
- Cierre de caja para vendedores (cerrar + certificar con tesorero)
- Admin: gestión completa (tarifas, horarios, inspectores, vendedores, usuarios, exenciones)
  → Cobrar infracción desde panel admin: tiene confirm JS + redirige a comprobante
- Páginas de error: 500.html y 404.html standalone (sin extends base.html)

## Flujo de comisiones (vendedor)
1. Cobro crea MovimientoCaja con comision_monto calculado (% del municipio)
2. CierreCaja agrupa los movimientos al rendir
3. LiquidacionComision: tesorero deposita → vendedor certifica
   → Views: depositar_comision (tesorero) / certificar_comision (vendedor) / mis_comisiones (vendedor)

---

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
requests==2.32.3
pandas==2.2.3
openpyxl==3.1.5
pytest==9.0.1
pytest-django==4.11.1

Deploy: Railway (PaaS). DB: PostgreSQL. Estáticos: WhiteNoise. Python: 3.12.

---

# Arquitectura

## Capas

### Views — app_estacionamiento/views.py (~3200 líneas)
Solo orquestación HTTP. Valida inputs, llama a services/use_cases, hace redirect o render.
Sin lógica de negocio. POST-Redirect-Get en todos los formularios.
Flujos multi-paso con accion=buscar|confirmar|cobrar en una sola URL.
⚠️ Pendiente: dividir en módulos views_admin.py, views_conductor.py, etc.

### Services — services_*.py
Lógica reutilizable con efectos de borde en DB:
- services_caja.py         → generar_cierre_caja(usuario) — cierre atómico con snapshot comisión
- services_infracciones.py → crear_infraccion(...) — valida todo, lanza ErrorInfraccion, graba foto GPS
- services_verificacion.py → verificar_estado_vehiculo(patente, usuario, subcuadra)

### Use Cases — use_cases/
Un módulo por caso de uso. Punto de entrada único: función ejecutar(...).
- estacionar_vehiculo.py     — tarifa según tipo (auto/moto), verifica saldo
- cobrar_estacionamiento.py  — ingreso en caja con comision_monto; parámetros: inspector, monto, descripcion, comision_monto
- finalizar_estacionamiento.py
- pagar_infraccion.py        — verifica tolerancia de gracia, anula o cobra (texto: "ANULADA ✅")
- acreditar_saldo_mp.py      — idempotente por payment_id
- registrar_movimiento.py
- registrar_infraccion.py

### Domain — domain/
Sin dependencia del ORM.
- enums.py        → EstadoVehiculo: NO_REGISTRADO, IMPAGO, PAGADO, ABONO_ACTIVO,
                    EXENTO_TOTAL, EXENTO_PARCIAL, PENDIENTE_PAGO
- verificacion.py → ResultadoVerificacion (dataclass): necesita_infraccion(), css_class(), to_dict()
- saldo_policy.py → SaldoPolicy.tiene_saldo(usuario, costo) → bool

---

## Autorización
Decorador @require_role(*roles) — retorna 403.html si falla.
Roles = flags booleanos en Usuario:
  "admin"     → is_superuser OR is_staff OR es_admin
  "inspector" → es_inspector
  "vendedor"  → es_vendedor
  "conductor" → es_conductor
  "tesorero"  → es_tesorero

Regla de cobro manual:
  registrar_estacionamiento_vendedor → @require_role("vendedor", "admin")  [inspector excluido]
  registrar_estacionamiento_manual   → @require_role("vendedor", "admin")  [inspector excluido]

---

## Modelos principales (app_estacionamiento/models.py)

### Usuarios
- Usuario (AbstractUser, USERNAME_FIELD="correo"):
    campos: correo, municipio FK, saldo, saldo_operativo, roles (5 flags bool), es_verificado
    inspectores: telefono, numero_dni, numero_legajo
    vendedores: nombre_propietario, documento_cuil, horario_atencion
    properties: nombre (→first_name), apellido (→last_name)
- SocialAccountAdapter (adapters.py):
    popula correo, first_name (given_name), last_name (family_name) desde Google
    asigna municipio automáticamente si hay exactamente 1 activo

### Municipio y configuración
- Municipio: comision_vendedor (Decimal %, None=0), tolerancia_multa_minutos (int)
- Tarifa: precio_por_hora, precio_por_hora_moto (0=usar auto), monto_infraccion,
          precio_abono_auto, precio_abono_moto
- HorarioEstacionamiento: dia_semana (0-6) + hora_inicio/fin
- DiaEspecial: fecha + tipo + cobro_activo bool
- Subcuadra: calle + altura (0 = "Zona Única")

### Vehículos y estacionamiento
- Vehiculo: patente (unique), tipo ('auto'|'moto'), exento_global, subcuadras_exentas M2M
- VehiculoUsuario: intermedia Usuario↔Vehiculo
- Estacionamiento: duracion_min (⚠️ almacena HORAS, no minutos — no cambiar sin migration)
    UniqueConstraint: solo un estacionamiento ACTIVO por vehículo
- AbonoMensual: mes=primer día del mes, unique (vehiculo, municipio, mes)
    vendedor FK, conductor FK, movimiento_caja FK (null)

### Cobros y caja
- MovimientoCaja: tipo ingreso/egreso, medio_pago, comision_monto
    save() bloquea si cerrado=True
- CierreCaja: snapshot con ganancia_usuario, monto_municipio, porcentaje aplicado, certificado bool
- Rendicion: pendiente/validada/observada
- LiquidacionComision: pendiente/depositada/certificada — tesorero deposita, vendedor certifica

### Infracciones
- Infraccion: monto = snapshot de Tarifa.monto_infraccion al crear
    estado: pendiente/pagada/anulada
    tolerancia_multa_minutos: si paga dentro del período → anulada (texto: "ANULADA ✅")
- VerificacionInspector: registra cada escaneo; tolerancia entre verificaciones = 15 min fijo

---

## Concurrencia
Todo cobro usa transaction.atomic() + select_for_update():

    with transaction.atomic():
        obj = Modelo.objects.select_for_update().get(id=...)
        # modificar y guardar

Modelos que requieren este patrón: Usuario (saldo), MovimientoCaja, Infraccion.

---

## Multi-municipio
Todo filtrado por request.user.municipio. Usar siempre:
    get_object_or_404(Modelo, id=pk, municipio=municipio)
Nunca .get(id=pk) sin filtro de municipio.

---

## Cierre reactivo (sin Celery)
Los estacionamientos vencidos se cierran al acceder a inicio_usuarios y al verificar.
Pull-based al inicio de sesión.

---

# Convenciones de código

- Modelos: PascalCase en castellano (MovimientoCaja, CierreCaja)
- Campos y funciones: snake_case en castellano (correo, es_inspector)
- URL names con prefijo de rol: inspectores_*, vendedores_*, usuarios_*, admin_*
- Comentarios en castellano
- comision_pct: siempre `getattr(municipio, "comision_vendedor", None) or Decimal("0")`
  (el campo puede ser None si no está configurado)
- Lógica de negocio nunca en views — siempre en services/ o use_cases/
- POST-Redirect-Get en todos los formularios
- Flujos multi-paso: accion= en POST (buscar → confirmar → cobrar)

---

# URLs importantes

/usuarios/                          → conductor
/usuarios/admin-inicio/             → panel admin
/usuarios/admin-usuarios/           → gestionar conductores
/usuarios/admin-inspectores/        → gestionar inspectores
/usuarios/admin-vendedores/         → gestionar vendedores
/usuarios/inspectores/              → panel inspector
/usuarios/inspectores/verificar/    → verificar patente (con selector tipo auto/moto)
/usuarios/inspectores/registrar-infraccion/ → labrar acta
/usuarios/vendedores/               → panel vendedor
/usuarios/vendedores/abono/         → cobrar abono mensual
/usuarios/vendedores/cobrar-infraccion/ → cobrar multa en efectivo
/usuarios/vendedores/caja/          → caja del vendedor
/usuarios/vendedores/comisiones/    → liquidaciones de comisiones
/usuarios/tesorero/                 → panel tesorero
/usuarios/mp/iniciar/               → iniciar carga MercadoPago
/usuarios/mp/exitoso/               → callback MP exitoso → redirige a inicio
/usuarios/mis-infracciones/         → infracciones del conductor
/usuarios/ticket-pago-multa/<id>/   → comprobante de pago de multa (admin/vendedor/inspector)
