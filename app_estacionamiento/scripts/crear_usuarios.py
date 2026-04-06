##app_estacionamiento/scripts/crear_usuarios.py

import os
import sys
import django

# Agregar la carpeta raíz al sys.path
sys.path.append(os.path.dirname(os.path.dirname(os.path.dirname(__file__))))

# Inicializar Django con el settings correcto
os.environ.setdefault('DJANGO_SETTINGS_MODULE', 'sitio.settings')
django.setup()

from app_estacionamiento.models import Municipio, Usuario, Vehiculo, Subcuadra


def crear_subcuadras_municipio(municipio):
    zonas = [
        (["Calle 12","Calle 14","Calle 16","Calle 18","Calle 20","Calle 22","Calle 28","Calle 30"], [400,450,500,550,600,650,700]),
        (["Calle 24","Calle 26"], [400,450,500,550,600,650,700,750,800,850]), 
        (["Calle 17","Calle 19","Calle 21","Calle 23","Calle 25","Calle 27","Calle 29","Calle 31","Calle 33"], [250,300,350,400,450,500,550,600,650,700]),
        (["Calle 35","Calle 37"], [550]),
    ]

    for calles, alturas in zonas:
        for calle in calles:
            for altura in alturas:
                Subcuadra.objects.get_or_create(
                    calle=calle,
                    altura=altura,
                    municipio=municipio
                )


def run():
    municipio, _ = Municipio.objects.get_or_create(nombre="Mercedes")

    # Zona única SIEMPRE
    Subcuadra.objects.get_or_create(
        calle="Zona Única",
        altura=0,
        municipio=municipio
    )

    crear_subcuadras_municipio(municipio)

    # =========================================================
    # ⚠️ DATOS DE PRUEBA (SOLO DESARROLLO)
    # 👉 ELIMINAR O NO EJECUTAR EN PRODUCCIÓN
    # =========================================================

    # 👤 Conductor
    conductor, _ = Usuario.objects.get_or_create(correo="juanperez@ejemplo.com")
    conductor.municipio = municipio
    conductor.nombre = "Juan Pérez"
    conductor.saldo = 1000
    conductor.es_admin = False
    conductor.es_inspector = False
    conductor.es_vendedor = False
    conductor.es_conductor = True
    conductor.set_password("1234")
    conductor.save()

    # 🚗 Vehículos normales
    auto1, _ = Vehiculo.objects.get_or_create(patente="ABC123")
    auto2, _ = Vehiculo.objects.get_or_create(patente="XYZ789")
    conductor.vehiculos.add(auto1, auto2)

    # 🚗 Vehículo con EXENCIÓN GLOBAL
    vehiculo_exento_global, _ = Vehiculo.objects.get_or_create(patente="EXG123")
    vehiculo_exento_global.exento_global = True
    vehiculo_exento_global.save()

    # 🚗 Vehículo con EXENCIÓN PARCIAL (para testing UI)
    vehiculo_exento_parcial, _ = Vehiculo.objects.get_or_create(patente="EXP123")

    subcuadras_test = Subcuadra.objects.filter(
        calle="Calle 21",
        municipio=municipio
    )[:2]

    if subcuadras_test:
        vehiculo_exento_parcial.subcuadras_exentas.set(subcuadras_test)

    # 👮 Inspector
    inspector, _ = Usuario.objects.get_or_create(correo="garcia@ejemplo.com")
    inspector.municipio = municipio
    inspector.nombre = "Inspector García"
    inspector.es_inspector = True
    inspector.es_conductor = False
    inspector.set_password("1234")
    inspector.save()

    # 💰 Vendedor
    vendedor, _ = Usuario.objects.get_or_create(correo="kiosco@ejemplo.com")
    vendedor.municipio = municipio
    vendedor.nombre = "Kiosco San Martín"
    vendedor.es_vendedor = True
    vendedor.es_conductor = False
    vendedor.set_password("1234")
    vendedor.save()

    # 🛠️ Admin
    admin, _ = Usuario.objects.get_or_create(correo="admin@ejemplo.com")
    admin.municipio = municipio
    admin.nombre = "Admin Municipal"
    admin.es_admin = True
    admin.es_conductor = False
    admin.set_password("1234")
    admin.save()

    # =========================================================
    # ✔ Logs
    # =========================================================
    print("Vehículos del conductor:", [v.patente for v in conductor.vehiculos.all()])
    print("✔ Datos de prueba creados correctamente")


if __name__ == "__main__":
    run()