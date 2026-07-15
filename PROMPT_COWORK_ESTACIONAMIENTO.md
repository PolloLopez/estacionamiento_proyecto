# Prompt de contexto — Sistema de Estacionamiento Medido
# Pegar esto al inicio de una nueva sesión de Cowork para retomar el proyecto.

---

Estoy trabajando en un sistema web de estacionamiento medido municipal en Django.
La carpeta del proyecto está seleccionada como workspace.

Lee estos archivos en este orden antes de hacer cualquier cosa:
1. `CLAUDE.md` — convenciones de código, reglas de negocio críticas, git flow, gotchas
2. `CONTEXT.md` — arquitectura completa, stack, modelos, roles
3. `PENDIENTES.md` — qué falta hacer y qué ya está resuelto

## Resumen rápido del sistema

**Stack**: Django 5.x, Python 3.12, SQLite (local) / PostgreSQL (prod), Railway (deploy)

**Roles**: conductor, inspector, vendedor, admin, tesorero

**Arquitectura**: `views_*.py` → `use_cases/` → `services/` → `domain/` → `models.py`

**Tests**: `python manage.py test app_estacionamiento --verbosity=2` → 89 tests, OK

**Ramas**: `develop` → trabajo activo. `main` → Railway autodeploy.

## Reglas críticas que nunca hay que violar

1. **Tolerancia**: usar SIEMPRE `calcular_estado_tolerancia()` de `services/infracciones.py`.
   Nunca replicar la lógica inline.

2. **Saldo con lock**: `debitar_saldo_conductor()` NO abre su propia transacción.
   Llamar siempre desde dentro de `transaction.atomic()` con `select_for_update()` ya activo.

3. **Null bytes**: editar archivos via mount Linux→Windows puede corromper con null bytes.
   Después de cada escritura verificar con `ast.parse()`.
   Si hay corrupción: leer con Python (`replace(b'\x00', b'')`), reconstruir, reescribir.

## Estado actual

Ver `PENDIENTES.md` para el detalle completo.
Lo más reciente implementado: abono mensual con saldo digital para el conductor,
admin cobra abono sin comisión, tolerancia de gracia integrada al estacionar.
