"""
Comando para crear o actualizar el usuario admin en producción.

Uso en Railway Console:
    python manage.py crear_admin

Con opciones:
    python manage.py crear_admin --correo admin@ejemplo.com --password admin12345 --municipio Mercedes

Si el usuario ya existe, con --forzar lo actualiza (resetea password y flags):
    python manage.py crear_admin --forzar
"""

from django.core.management.base import BaseCommand
from django.db import transaction
from app_estacionamiento.models import Municipio, Usuario


class Command(BaseCommand):
    help = "Crea o actualiza el usuario admin para producción."

    def add_arguments(self, parser):
        parser.add_argument(
            "--correo",
            default="admin@ejemplo.com",
            help="Correo del admin (default: admin@ejemplo.com)",
        )
        parser.add_argument(
            "--password",
            default="admin12345",
            help="Contraseña del admin (default: admin12345)",
        )
        parser.add_argument(
            "--municipio",
            default="Mercedes",
            help="Nombre del municipio (default: Mercedes)",
        )
        parser.add_argument(
            "--forzar",
            action="store_true",
            default=False,
            help="Actualiza el usuario aunque ya exista (resetea password y flags)",
        )

    def handle(self, *args, **options):
        correo = options["correo"]
        password = options["password"]
        nombre_municipio = options["municipio"]
        forzar = options["forzar"]

        with transaction.atomic():
            # Crear municipio si no existe
            municipio, creado_mun = Municipio.objects.get_or_create(nombre=nombre_municipio)
            if creado_mun:
                self.stdout.write(f"  Municipio creado: {nombre_municipio}")
            else:
                self.stdout.write(f"  Municipio existente: {nombre_municipio}")

            # Verificar si el usuario ya existe
            usuario_existente = Usuario.objects.filter(correo=correo).first()

            if usuario_existente and not forzar:
                self.stdout.write(self.style.WARNING(
                    f"\n⚠️  Ya existe un usuario con correo '{correo}'.\n"
                    f"   Para actualizarlo, agregá --forzar al comando.\n"
                    f"   Ejemplo: python manage.py crear_admin --forzar\n"
                ))
                return

            if usuario_existente:
                # Actualizar usuario existente
                admin = usuario_existente
                accion = "actualizado"
            else:
                # Crear nuevo
                admin = Usuario(correo=correo)
                accion = "creado"

            # Configurar flags de admin
            admin.municipio = municipio
            admin.nombre = "Admin"
            admin.es_admin = True
            admin.es_conductor = False
            admin.es_inspector = False
            admin.es_vendedor = False
            admin.is_staff = True
            admin.is_superuser = True
            admin.set_password(password)
            admin.save()

        self.stdout.write(self.style.SUCCESS(
            f"\n✅ Admin {accion} correctamente:\n"
            f"   Correo:    {correo}\n"
            f"   Password:  {password}\n"
            f"   Municipio: {nombre_municipio}\n"
            f"\n⚠️  Cambiá la contraseña después del primer login.\n"
        ))
