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

### Flujo completo — paso a paso

**Durante la sesión de trabajo (en `develop`):**

```powershell
git add -A                  # 1. Marca todos los archivos modificados para incluir en el commit
git commit -m "mensaje"     # 2. Guarda el snapshot en tu máquina (local, no sube nada todavía)
git push                    # 3. Sube los commits al servidor remoto (GitHub)
```

**Cuando querés que Railway lo deploye (merge a main):**

```powershell
git checkout main           # 4. Te movés a la rama main
git merge develop           # 5. Traés todos los commits de develop a main
git push                    # 6. Subís main → Railway detecta y deploya automático
git checkout develop        # 7. Volvés a develop para seguir trabajando
```

**Por qué cada comando:**
- `git add -A` → Git no trackea cambios automáticamente. Tenés que decirle qué incluir.
- `git commit` → Crea el "foto" del estado del código. Solo existe en tu PC hasta el push.
- `git push` → Sube esa foto al servidor remoto. Ahí queda respaldado.
- `git checkout main` → Cambiás de rama (de develop a main).
- `git merge develop` → Fusionás el trabajo de develop dentro de main.
- El último `git push` es el que dispara el deploy en Railway.

> **Recordatorio:** cada vez que haya que subir a producción, leé esta sección antes de ejecutar.

## Desarrollo local vs producción

Railway solo despliega cuando se hace push a `main`. Mientras estés en `develop`, podés testear todo localmente sin tocar producción.

```powershell
# Arrancás el servidor local (en la rama develop)
python manage.py runserver
```

Luego abrís `http://127.0.0.1:8000` en tu navegador. Railway no se entera de nada hasta que mergees a `main`.

**Regla práctica:**
- Cambios en `develop` + `python manage.py runserver` → solo vos lo ves, en tu PC.
- `git checkout main` + `git merge develop` + `git push` → Railway lo despliega.
- Nunca toques `main` directamente para desarrollar.

**Flujo completo para deployar** (recordatorio compacto):
```powershell
git add -A
git commit -m "feat: descripción del cambio"
git push                  # sube develop a GitHub (Railway no reacciona)
git checkout main
git merge develop
git push                  # esto sí dispara el deploy en Railway
git checkout develop      # volvés a trabajar en develop
```

## Migraciones — cuándo y por qué

Cada vez que modificás un modelo (`models.py`), Django necesita actualizar la base de datos.
Son dos pasos distintos y siempre en ese orden:

```powershell
python manage.py makemigrations   # 1. Genera el archivo de migración (en migrations/)
python manage.py migrate          # 2. Aplica la migración a la base de datos real
```

- `makemigrations` → lee tus modelos y crea un archivo Python con los cambios (ej: `0054_infraccion_sia_fields.py`). No toca la BD.
- `migrate` → ejecuta esos archivos contra la BD. Railway lo corre automático al deployar.
- Si creás un campo nuevo y no corrés `makemigrations`, Django tira error al arrancar.
- Si el campo tiene `default=` o `null=True`, la migración no requiere datos previos.

> **Regla práctica:** ¿Cambié `models.py`? → `makemigrations` + `migrate` antes de correr el servidor.

## Django Shell — explorar el código en vivo

Cuando no entendés por qué algo falla o querés probar una query antes de escribirla en el código:

```powershell
python manage.py shell
```

Dentro del shell podés importar cualquier cosa y probarla:

```python
from app_estacionamiento.models import Vehiculo, Infraccion
from app_estacionamiento.services.sia_verificacion import verificar_sia

# Ver un objeto real
v = Vehiculo.objects.get(patente="AA123BB")
print(v.exento_global, v.vigencia_exencion)

# Probar una query
Infraccion.objects.filter(inspector__correo="inspector@test.com").count()
```

Es la forma más directa de entender qué tiene la BD y cómo responden las funciones sin tener que correr el servidor completo.

## Arquitectura — por qué el código está separado así

```
views_*.py   → recibe la request HTTP, valida el formulario, devuelve la respuesta
use_cases/   → orquesta una operación completa (ej: "estacionar un vehículo")
services/    → lógica de negocio reutilizable (ej: verificar estado, calcular tarifa)
domain/      → reglas puras sin DB (ej: ¿este vehículo puede estacionar?)
models.py    → estructura de la base de datos
```

**Por qué importa aprenderlo:** si necesitás cambiar cómo se calcula la tolerancia,
sabés que es en `services/infracciones.py`, no en una vista. Si algo falla en la
verificación de vehículos, buscás en `services/verificacion.py`. El error te dice
dónde mirar.

**Regla para leer código nuevo:** empezá por la vista (`views_*.py`) para entender
el flujo, seguí al use_case o service que llama, y llegás a la lógica real.

## Tests

```powershell
python manage.py test app_estacionamiento --verbosity=2
# Resultado esperado: 130+ tests, OK
```

**Cuándo correr los tests:**
- Después de cualquier cambio en `models.py`, `services/`, o `use_cases/`.
- Antes de mergear a `main` (antes de deployar).
- Si algo se rompe en producción y no sabés qué fue.

Un test que falla te dice exactamente qué función rompiste y cómo se esperaba que se comportara.
Leerlos también es una forma de entender cómo funciona el código.

## Gotchas conocidos

- **Null bytes en archivos**: editar archivos del repo desde herramientas externas (Edit/Write tools
  de Claude vía mount Linux→Windows) puede corromper archivos con null bytes. Si ocurre:
  `git show HEAD:archivo.py` → aplicar cambios vía Python string replace → verificar con `ast.parse()`.
- **`auto_now_add` en tests**: para setear `creado_en` en tests usar
  `Infraccion.objects.filter(pk=inf.pk).update(creado_en=...)`, no el constructor.
- **`timezone.now()` en tests**: mockear con `patch("app_estacionamiento.use_cases.pagar_infraccion.timezone")`.