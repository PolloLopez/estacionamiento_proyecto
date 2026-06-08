// ESTACIONAMIENTO_PROYECTO/testeo.md
# Checklist antes de commit

## 1. Tests automáticos

python manage.py test app_estacionamiento.tests

Resultado esperado:

Ran 17 tests

OK

---

## 2. Validación Django

python manage.py check

Resultado esperado:

System check identified no issues

---

## 3. Migraciones

python manage.py showmigrations

Todas deben aparecer con [X]

---

## 4. Migraciones pendientes

python manage.py makemigrations

Resultado esperado:

No changes detected

---

## 5. Test manual

### Conductor

* Login
* Estacionar
* Finalizar
* Consultar historial

### Inspector

* Verificar vehículo
* Generar infracción

### Administrador

* Exenciones
* Usuarios
* Estadísticas
