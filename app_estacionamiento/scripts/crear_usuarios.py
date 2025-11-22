# scripts/crear_usuarios.py
from app_estacionamiento.models import Usuario

def run():
    # Conductor
    Usuario.objects.get_or_create(
        correo="juanperez@example.com",
        defaults={
            "nombre": "Juan Pérez",
            "saldo": 100,
            "es_conductor": True,
            "es_inspector": False,
            "es_vendedor": False,
            "es_admin": False,
        }
    )

    # Inspector
    Usuario.objects.get_or_create(
        correo="garcia@example.com",
        defaults={
            "nombre": "Inspector García",
            "saldo": 0,
            "es_conductor": False,
            "es_inspector": True,
            "es_vendedor": False,
            "es_admin": False,
        }
    )

    # Vendedor
    Usuario.objects.get_or_create(
        correo="kiosco@example.com",
        defaults={
            "nombre": "Kiosco San Martín",
            "saldo": 0,
            "es_conductor": False,
            "es_inspector": False,
            "es_vendedor": True,
            "es_admin": False,
        }
    )

    # Administrador
    Usuario.objects.get_or_create(
        correo="admin@example.com",
        defaults={
            "nombre": "Admin Municipal",
            "saldo": 0,
            "es_conductor": False,
            "es_inspector": False,
            "es_vendedor": False,
            "es_admin": True,
        }
    )

    print("Usuarios de prueba creados correctamente ✅")
