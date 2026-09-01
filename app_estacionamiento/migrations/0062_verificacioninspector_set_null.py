# Migración manual — 2026-09-01
# Cambia VerificacionInspector.inspector/vehiculo/subcuadra de CASCADE a SET_NULL.
#
# Con CASCADE, borrar un inspector, vehículo o subcuadra eliminaba todas sus
# verificaciones — historial de trazabilidad perdido silenciosamente. SET_NULL
# conserva el registro con el campo en None, lo que permite saber que existió
# la verificación aunque ya no se pueda navegar al objeto relacionado.
#
# A diferencia de la migración 0061 (Infraccion.subcuadra), acá SÍ hay cambio
# de schema: las 3 columnas pasan de NOT NULL a nullable (DROP NOT NULL en
# PostgreSQL). En Postgres esto es un cambio de metadatos — sin reescritura de
# tabla, seguro incluso con miles de registros existentes.

import django.db.models.deletion
from django.conf import settings
from django.db import migrations, models


class Migration(migrations.Migration):

    dependencies = [
        ('app_estacionamiento', '0061_infraccion_subcuadra_set_null'),
    ]

    operations = [
        migrations.AlterField(
            model_name='verificacioninspector',
            name='inspector',
            field=models.ForeignKey(
                blank=True,
                null=True,
                on_delete=django.db.models.deletion.SET_NULL,
                to=settings.AUTH_USER_MODEL,
            ),
        ),
        migrations.AlterField(
            model_name='verificacioninspector',
            name='vehiculo',
            field=models.ForeignKey(
                blank=True,
                null=True,
                on_delete=django.db.models.deletion.SET_NULL,
                to='app_estacionamiento.vehiculo',
            ),
        ),
        migrations.AlterField(
            model_name='verificacioninspector',
            name='subcuadra',
            field=models.ForeignKey(
                blank=True,
                null=True,
                on_delete=django.db.models.deletion.SET_NULL,
                to='app_estacionamiento.subcuadra',
            ),
        ),
    ]
