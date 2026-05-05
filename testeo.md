🧪 Cómo hacer un TEST antes del commit (bien hecho, rápido)

No hace falta que te metas en testing complejo todavía.
Hacé test funcional mínimo + sanity check.

✅ 1. TEST MANUAL (el más importante ahora)

Hacé este flujo:

🔐 Login
entrar con admin ✔
🚗 Estacionar
ir a:
/usuarios/estacionar/

Probar:

✅ patente nueva → debería crear
✅ patente existente → debería permitir
⚠️ patente con otro usuario → warning
❌ patente con estacionamiento activo → bloquear
✅ 2. TEST DE URLS (evita errores como el que tuviste)

Corré:

python manage.py check

✔ debe decir:

System check identified no issues
✅ 3. TEST DE MIGRACIONES
python manage.py showmigrations

✔ todas con [X]