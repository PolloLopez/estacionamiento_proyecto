// ESTACIONAMIENTO_PROYECTO/app_estacionamiento/docs/arquitectura.md
# Arquitectura actual

## Capas

### Views

Responsables de:

* Recibir requests.
* Validar permisos.
* Invocar services y use cases.
* Renderizar respuestas.

No deben contener reglas de negocio complejas.

---

### Services

Responsables de:

* Verificación de vehículos.
* Gestión de infracciones.
* Reglas reutilizables.

Archivos principales:

* services_verificacion.py
* services_infracciones.py

---

### Use Cases

Responsables de procesos completos.

Ejemplos:

* estacionar_vehiculo.py
* cobrar_estacionamiento.py

---

### Domain

Contiene:

* Enums.
* Policies.
* Objetos de dominio.

Objetivo:
centralizar reglas de negocio desacopladas de Django.

---

## Estado actual

Implementado:

* Multi-municipio básico.
* Verificación desacoplada.
* Infracciones desacopladas.
* Caja auditada.
* Tests automatizados.

Pendiente:

* Ownership de vehículos.
* Atomicidad transaccional.
* API REST.
* JWT.
