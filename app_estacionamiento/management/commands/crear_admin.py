"""
Comando para crear el usuario admin inicial en producción.

Uso en Railway (Console del servicio):
    python manage.py crear_admin

También acepta argumentos:
    python manage.py crear_admin --correo admin@demo.com --password MiClave123
"""

from django.core.management.base import BaseCommand
from django.db import transaction
from app_estacionamiento.models import Municipio, Usuario


class Command(BaseCommand):
    help = "Crea el municipio demo y el usuario admin inicial para el entorno de producción."

    def add_arguments(self, parser):
        parser.add_argument(
            "--correo",
            default="admin@estacionamiento.demo",
            help="Correo del admin (default: admin@estacionamiento.demo)",
        )
        parser.add_argument(
            "--password",
            default="Admin1234!",
            help="Contraseña del admin (default: Admin1234!)",
        )
        parser.add_argument(
            "--municipio",
            default="Municipio Demo",
            help="Nombre del municipio (default: Municipio Demo)",
        )

    def handle(self, *args, **options):
        correo = options["correo"]
        password = options["password"]
        nombre_municipio = options["municipio"]

        with transaction.atomic():
            # Crear municipio si no existe
            municipio, creado = Municipio.objects.get_or_create(nombre=nombre_municipio)
            if creado:
                self.stdout.write(f"  Municipio creado: {nombre_municipio}")
            else:
                self.stdout.write(f"  Municipio existente: {nombre_municipio}")

            # Crear admin si no existe
            if Usuario.objects.filter(correo=correo).exists():
                self.stdout.write(self.style.WARNING(f"  Ya existe un usuario con correo {correo}. No se creó nada."))
                return

            admin = Usuario.objects.create_superuser(
                correo=correo,
                password=password,
                municipio=municipio,
            )
            admin.es_admin = True
            admin.first_name = "Admin"
            admin.last_name = "Demo"
            admin.save()

        self.stdout.write(self.style.SUCCESS(
            f"\n✅ Admin creado correctamente:\n"
            f"   Correo:   {correo}\n"
            f"   Password: {password}\n"
            f"   Municipio: {nombre_municipio}\n\n"
            f"⚠️  Cambiá la contraseña después del primer login."
        ))
