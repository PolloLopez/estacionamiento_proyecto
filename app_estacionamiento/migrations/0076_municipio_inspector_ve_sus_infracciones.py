from django.db import migrations, models


class Migration(migrations.Migration):

    dependencies = [
        ('app_estacionamiento', '0075_liquidacion_comprobante_deposito'),
    ]

    operations = [
        migrations.AddField(
            model_name='municipio',
            name='inspector_ve_sus_infracciones',
            field=models.BooleanField(
                default=False,
                verbose_name='Inspector ve sus propias infracciones',
                help_text=(
                    'Si está activado, el inspector puede ver en su panel las infracciones '
                    'que él mismo labró. Por defecto desactivado: el inspector solo carga '
                    'infracciones, el admin las gestiona.'
                ),
            ),
        ),
    ]
