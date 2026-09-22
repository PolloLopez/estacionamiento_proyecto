from django.db import migrations, models


class Migration(migrations.Migration):

    dependencies = [
        ('app_estacionamiento', '0088_auditoria_password'),
    ]

    operations = [
        migrations.AddField(
            model_name='municipio',
            name='mapa_infracciones_activo',
            field=models.BooleanField(
                default=False,
                verbose_name='Mapa de infracciones activo',
                help_text=(
                    'Si está activo, el admin municipal puede ver el mapa de calor de '
                    'infracciones desde /admin/mapa-infracciones/. '
                    'Por defecto está desactivado.'
                ),
            ),
        ),
    ]
