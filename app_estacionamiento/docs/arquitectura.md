# Arquitectura actual del sistema

## Modelo de datos

- Usuario
  - Roles: admin, inspector, vendedor, conductor
  - Relación con Municipio

- Vehiculo
  - patente única
  - exento_global
  - subcuadras_exentas (ManyToMany)

- Subcuadra
  - calle
  - altura
  - municipio

- Estacionamiento
  - vehiculo
  - subcuadra
  - activo
  - costo

- Infraccion
  - vehiculo
  - inspector
  - subcuadra
  - foto

---

## Lógica principal

- Registro de estacionamiento (vendedor)
- Verificación de vehículo (inspector)
- Registro de infracción (inspector)
- Gestión de exenciones
  - Global
  - Por subcuadra

---

## Autenticación actual

- Basada en session:
  - request.session["usuario_id"]
- Middleware:
  - request.usuario

---

## Observaciones

- Pendiente migración a Django Auth (`request.user`)
- Pendiente API REST
- Pendiente frontend separado