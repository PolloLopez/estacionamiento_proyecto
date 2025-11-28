import os
import django

# Configurar entorno Django
os.environ.setdefault("DJANGO_SETTINGS_MODULE", "sitio.settings")
django.setup()

from app_estacionamiento.models import Usuario, Vehiculo, Subcuadra

def run():
    # Crear subcuadras de ejemplo
    zona_unica, _ = Subcuadra.objects.get_or_create(calle="Zona Única", altura=0)
    calle21_400, _ = Subcuadra.objects.get_or_create(calle="Calle 21", altura=400)
    calle21_450, _ = Subcuadra.objects.get_or_create(calle="Calle 21", altura=450)

    # Conductor
    juan, _ = Usuario.objects.get_or_create(
        correo="juanperez@example.com",
        defaults={
            "nombre": "Juan Pérez",
            "saldo": 100,
            "es_conductor": True,
        }
    )
    auto1, _ = Vehiculo.objects.get_or_create(patente="ABC123")
    juan.vehiculos.add(auto1)

    # Vehículo con exención global
    vehiculo_exento_global, _ = Vehiculo.objects.get_or_create(patente="XYZ789")
    vehiculo_exento_global.exento_global = True
    vehiculo_exento_global.save()

    # Vehículo con exención en subcuadras específicas
    vehiculo_exento_sub, _ = Vehiculo.objects.get_or_create(patente="LMN456")
    vehiculo_exento_sub.subcuadras_exentas.add(calle21_300, calle21_350)

    # Inspector
    Usuario.objects.get_or_create(
        correo="garcia@example.com",
        defaults={
            "nombre": "Inspector García",
            "es_inspector": True,
        }
    )

    # Vendedor
    Usuario.objects.get_or_create(
        correo="kiosco@example.com",
        defaults={
            "nombre": "Kiosco San Martín",
            "es_vendedor": True,
        }
    )

    # Administrador
    Usuario.objects.get_or_create(
        correo="admin@example.com",
        defaults={
            "nombre": "Admin Municipal",
            "es_admin": True,
        }
    )

    print("✅ Base inicializada con usuarios, vehículos y subcuadras de prueba")

if __name__ == "__main__":
    run()
