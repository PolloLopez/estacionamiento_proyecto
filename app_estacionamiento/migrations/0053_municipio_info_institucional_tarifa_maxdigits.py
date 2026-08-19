from django.db import migrations, models


class Migration(migrations.Migration):

    dependencies = [
        ('app_estacionamiento', '0052_municipio_limites_carga_mp'),
    ]

    operations = [
        # Nuevos campos de texto institucional en Municipio
        migrations.AddField(
            model_name='municipio',
            name='leyenda_horarios',
            field=models.TextField(
                blank=True, default='',
                verbose_name='Leyenda de horarios',
                help_text='Ej: Lunes a viernes de 8 a 20 hs · Sábados de 8 a 13 hs.',
            ),
        ),
        migrations.AddField(
            model_name='municipio',
            name='texto_ordenanza',
            field=models.TextField(
                blank=True, default='',
                verbose_name='Marco legal / Ordenanza',
                help_text='Ej: Ordenanza N° 1234/2023 — Estacionamiento Medido Municipal.',
            ),
        ),
        # Ampliar max_digits de precio_por_hora para soportar montos grandes
        migrations.AlterField(
            model_name='tarifa',
            name='precio_por_hora',
            field=models.DecimalField(max_digits=10, decimal_places=2),
        ),
    ]
