# app_estacionamiento/scripts/crear_usuarios.py
from app_estacionamiento.models import Usuario, Vehiculo, Subcuadra, Infraccion

def run():
    
    # Crear subcuadras de ejemplo
    zona_unica, _ = Subcuadra.objects.get_or_create(calle="Zona Única", altura=0)
    calle21_200, _ = Subcuadra.objects.get_or_create(calle="Calle 21", altura=200)
    calle21_250, _ = Subcuadra.objects.get_or_create(calle="Calle 21", altura=250)
    calle21_300, _ = Subcuadra.objects.get_or_create(calle="Calle 21", altura=300)
    calle21_350, _ = Subcuadra.objects.get_or_create(calle="Calle 21", altura=350)

    # Conductor
    juan, _ = Usuario.objects.get_or_create(correo="juanperez@ejemplo.com")
    juan.nombre = "Juan Pérez"
    juan.saldo = 1000   # saldo inicial para la demo
    juan.es_admin = False
    juan.es_inspector = False
    juan.es_vendedor = False
    juan.es_conductor = True
    juan.set_password("1234")
    juan.save()

    # Asociar vehículos normales
    auto1, _ = Vehiculo.objects.get_or_create(patente="ABC123")
    juan.vehiculos.add(auto1)
    auto2, _ = Vehiculo.objects.get_or_create(patente="XYZ789")
    juan.vehiculos.add(auto2)

    # Vehículo con exención global
    vehiculo_exento_global, _ = Vehiculo.objects.get_or_create(patente="EXG123")
    vehiculo_exento_global.exento_global = True
    vehiculo_exento_global.save()

    # Vehículo con exención en subcuadras específicas
    vehiculo_exento_sub, _ = Vehiculo.objects.get_or_create(patente="EXP123")
    vehiculo_exento_sub.subcuadras_exentas.add(calle21_300, calle21_350)
    vehiculo_exento_sub.save()
    print("Subcuadras exentas de EXP123:", [s.calle + " " + str(s.altura) for s in vehiculo_exento_sub.subcuadras_exentas.all()])

    # Inspector
    inspector, _ = Usuario.objects.get_or_create(correo="garcia@ejemplo.com")
    inspector.nombre = "Inspector García"
    inspector.es_admin = False
    inspector.es_inspector = True
    inspector.es_vendedor = False
    inspector.es_conductor = False
    inspector.set_password("1234")
    inspector.save()

    # Vendedor
    vendedor, _ = Usuario.objects.get_or_create(correo="kiosco@ejemplo.com")
    vendedor.nombre = "Kiosco San Martín"
    vendedor.es_admin = False
    vendedor.es_inspector = False
    vendedor.es_vendedor = True
    vendedor.es_conductor = False
    vendedor.set_password("1234")
    vendedor.save()

    # Administrador
    admin, _ = Usuario.objects.get_or_create(correo="admin@ejemplo.com")
    admin.nombre = "Admin Municipal"
    admin.es_admin = True
    admin.es_inspector = False
    admin.es_vendedor = False
    admin.es_conductor = False
    admin.set_password("1234")
    admin.save()

    # Mostrar en consola las patentes de Juan
    print("Vehículos de Juan:", [v.patente for v in juan.vehiculos.all()])
    print("Usuarios, vehículos y subcuadras de prueba creados correctamente ✅")