import django.db.models.deletion
from django.db import migrations, models


class Migration(migrations.Migration):
    """
    Registra el modelo SolicitudEliminacionCuenta en el estado de migraciones
    de Django SIN ejecutar SQL — la tabla ya existe en producción.

    Por qué SeparateDatabaseAndState:
    El modelo vivía en models.py sin su migración correspondiente. En algún
    deploy anterior Django creó la tabla de forma implícita (por el warning
    'models have changes not reflected'). Si ahora ejecutamos un CREATE TABLE
    normal, PostgreSQL falla con 'relation already exists'.

    SeparateDatabaseAndState resuelve esto:
    - database_operations=[]  → no toca la BD (tabla ya existe)
    - state_operations=[...]  → actualiza el registro interno de Django
                                para que sepa que el modelo está migrado

    Después de este deploy, makemigrations y el warning desaparecen.
    """

    dependencies = [
        ("app_estacionamiento", "0100_duracion_horas_mayor_precision"),
    ]

    operations = [
        migrations.SeparateDatabaseAndState(
            # La tabla ya existe: no ejecutar ningún SQL
            database_operations=[],
            # Solo actualizar el estado interno de Django
            state_operations=[
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
                                to="app_estacionamiento.usuario",
                            ),
                        ),
                    ],
                    options={
                        "verbose_name":        "Solicitud de eliminación de cuenta",
                        "verbose_name_plural": "Solicitudes de eliminación de cuenta",
                    },
                ),
            ],
        ),
    ]
