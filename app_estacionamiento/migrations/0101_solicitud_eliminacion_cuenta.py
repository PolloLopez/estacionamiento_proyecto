import django.db.models.deletion
from django.conf import settings
from django.db import migrations, models


class Migration(migrations.Migration):
    """
    Crea el modelo SolicitudEliminacionCuenta.

    Este modelo existía en models.py pero nunca tuvo su migración correspondiente,
    lo que causaba el warning 'Your models have changes that are not yet reflected
    in a migration' en cada deploy de Railway.

    El modelo registra cuando un conductor solicita eliminar su cuenta.
    """

    dependencies = [
        ("app_estacionamiento", "0100_duracion_horas_mayor_precision"),
        migrations.swappable_dependency(settings.AUTH_USER_MODEL),
    ]

    operations = [
        migrations.CreateModel(
            name="SolicitudEliminacionCuenta",
            fields=[
                (
                    "id",
                    models.BigAutoField(
                        auto_created=True,
                        primary_key=True,
                        serialize=False,
                        verbose_name="ID",
                    ),
                ),
                (
                    "estado",
                    models.CharField(
                        choices=[
                            ("pendiente",  "Pendiente de confirmación"),
                            ("completada", "Cuenta eliminada"),
                            ("cancelada",  "Cancelada por el usuario"),
                        ],
                        default="pendiente",
                        max_length=15,
                    ),
                ),
                ("motivo",      models.TextField(blank=True, default="")),
                ("creado_en",   models.DateTimeField(auto_now_add=True)),
                ("resuelto_en", models.DateTimeField(blank=True, null=True)),
                (
                    "usuario",
                    models.OneToOneField(
                        on_delete=django.db.models.deletion.CASCADE,
                        related_name="solicitud_eliminacion",
                        to=settings.AUTH_USER_MODEL,
                    ),
                ),
            ],
            options={
                "verbose_name":        "Solicitud de eliminación de cuenta",
                "verbose_name_plural": "Solicitudes de eliminación de cuenta",
            },
        ),
    ]
