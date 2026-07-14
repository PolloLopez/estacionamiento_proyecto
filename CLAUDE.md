Sistema de gestión de estacionamiento medido municipal (Django 5.x).
Roles: conductor, inspector, vendedor, admin, tesorero.
Ver CONTEXT.md para arquitectura completa. Ver PENDIENTES.md para tareas.

## Convenciones de código

- Nombres descriptivos en castellano (términos técnicos en inglés entre paréntesis).
- Funciones separadas por responsabilidad, sin sobreingeniería.
- Comentarios en lógica no trivial (ej: por qué `debitar_saldo_conductor` no abre su propia transacción).
- Capa: `views_*.py` → `use_cases/` → `services/` → `domain/` → `models.py`.

## Reglas de negocio clave

- **Tolerancia**: usar SIEMPRE `calcular_estado_tolerancia()` de `services/infracciones.py`.
  Nunca replicar la lógica inline. Incluye `MARGEN_TOLERANCIA_SEGUNDOS = 60`.
- **Saldo con lock**: `debitar_saldo_conductor()` NO abre su propia transacción.
  Debe llamarse desde dentro de un `transaction.atomic()` con `select_for_update()` ya activo.
- **Estacionar con infracción**: `estacionar_vehiculo.py` chequea infracciones pendientes del vehículo
  antes de crear el Estacionamiento. Dentro de gracia → anula. Fuera → deja pendiente + timestamps en sesión.

## Ramas Git

- `main` → producción (Railway despliega desde acá). Solo recibe merges desde `develop`.
- `develop` → rama de trabajo activa. Todo feature nuevo va acá.

Flujo de trabajo:
1. Desarrollar y commitear en `develop`
2. Cuando el feature está listo y probado localmente: `git checkout main && git merge develop && git push`
3. Railway despliega automáticamente desde `main`

## Tests

```powershell
python manage.py test app_estacionamiento --verbosity=2
# Resultado esperado: 89 tests, OK
```

## Gotchas conocidos

- **Null bytes en archivos**: editar archivos del repo desde herramientas externas (Edit/Write tools
  de Claude vía mount Linux→Windows) puede corromper archivos con null bytes. Si ocurre:
  `git show HEAD:archivo.py` → aplicar cambios vía Python string replace → verificar con `ast.parse()`.
- **`auto_now_add` en tests**: para setear `creado_en` en tests usar
  `Infraccion.objects.filter(pk=inf.pk).update(creado_en=...)`, no el constructor.
- **`timezone.now()` en tests**: mockear con `patch("app_estacionamiento.use_cases.pagar_infraccion.timezone")`.