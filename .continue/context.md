// ESTACIONAMIENTO_PROYECTO/.continue/context.md
Proyecto: Sistema de Estacionamiento Medido

Estado actual:
Aplicación Django monolítica preparada para evolución SaaS.

Stack actual:

* Django 5
* SQLite (desarrollo)
* Templates HTML
* Pillow
* Pytest + Django TestCase

Arquitectura:

* Views livianas
* Services
* Use Cases
* Domain Layer

Reglas:

* Mantener lógica de negocio fuera de views.
* Priorizar services y use cases.
* Explicaciones detalladas en castellano.
* Mantener compatibilidad multi-municipio.

Próximos objetivos:

1. Ownership vehículo ↔ usuario.
2. Atomicidad de cobros.
3. API REST (DRF).
4. PostgreSQL.
5. JWT.
6. Frontend desacoplado.
