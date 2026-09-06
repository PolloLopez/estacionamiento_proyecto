# Migración manual — 2026-09-01
# Cambia Infraccion.subcuadra de on_delete=CASCADE a SET_NULL.
#
# Con CASCADE, borrar una subcuadra eliminaba todas sus infracciones —
# historial contable perdido silenciosamente. SET_NULL conserva la
# infracción con subcuadra=None, que ya era nullable antes de esta migración.
#
# Nota: on_delete vive solo en el ORM de Django, no en la constraint de FK
# de PostgreSQL. Esta migración no altera el schema de la base — solo
# actualiza el estado del ORM para que futuros cambios sean consistentes.

import django.db.models.deletion
from django.db import migrations, models


class Migration(migrations.Migration):

    dependencies = [
        ('app_estacionamiento', '0060_usuario_cambio_password_requerido'),
    ]

    operations = [
        migrations.AlterField(
            model_name='infraccion',
            name='subcuadra',
            field=models.ForeignKey(
                blank=True,
                null=True,
                on_delete=django.db.models.deletion.SET_NULL,
                to='app_estacionamiento.subcuadra',
            ),
        ),
    ]
