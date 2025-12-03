# app_estacionamiento/scripts/crear_usuarios.py
from app_estacionamiento.models import Usuario, Vehiculo, Subcuadra

def run():
    # Crear subcuadras de ejemplo
    zona_unica, _ = Subcuadra.objects.get_or_create(calle="Zona Única", altura=0)
    calle21_200, _ = Subcuadra.objects.get_or_create(calle="Calle 21", altura=200)
    calle21_250, _ = Subcuadra.objects.get_or_create(calle="Calle 21", altura=250)
    calle21_300, _ = Subcuadra.objects.get_or_create(calle="Calle 21", altura=300)
    calle21_350, _ = Subcuadra.objects.get_or_create(calle="Calle 21", altura=350)
    calle22_200, _ = Subcuadra.objects.get_or_create(calle="Calle 22", altura=200)
    calle22_250, _ = Subcuadra.objects.get_or_create(calle="Calle 22", altura=250)
    calle22_300, _ = Subcuadra.objects.get_or_create(calle="Calle 22", altura=300)
    calle22_350, _ = Subcuadra.objects.get_or_create(calle="Calle 22", altura=350)
    calle23_200, _ = Subcuadra.objects.get_or_create(calle="Calle 23", altura=200)
    calle23_250, _ = Subcuadra.objects.get_or_create(calle="Calle 23", altura=250)
    calle23_300, _ = Subcuadra.objects.get_or_create(calle="Calle 23", altura=300)
    calle23_350, _ = Subcuadra.objects.get_or_create(calle="Calle 23", altura=350)
    calle24_200, _ = Subcuadra.objects.get_or_create(calle="Calle 24", altura=200)
    calle24_250, _ = Subcuadra.objects.get_or_create(calle="Calle 24", altura=250)
    calle24_300, _ = Subcuadra.objects.get_or_create(calle="Calle 24", altura=300)
    calle24_350, _ = Subcuadra.objects.get_or_create(calle="Calle 24", altura=350)

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

    print("Usuarios y vehículos de prueba creados correctamente ✅")
  