from django.db import migrations, models


class Migration(migrations.Migration):

    dependencies = [
        ('app_estacionamiento', '0079_municipio_admin_puede_editar_plantillas'),
    ]

    operations = [
        migrations.AddField(
            model_name='infraccion',
            name='gps_lat',
            field=models.DecimalField(
                blank=True, decimal_places=6, max_digits=9, null=True,
                verbose_name='Latitud GPS (inspector)',
            ),
        ),
        migrations.AddField(
            model_name='infraccion',
            name='gps_lon',
            field=models.DecimalField(
                blank=True, decimal_places=6, max_digits=9, null=True,
                verbose_name='Longitud GPS (inspector)',
            ),
        ),
        migrations.AddField(
            model_name='infraccion',
            name='gps_acc',
            field=models.DecimalField(
                blank=True, decimal_places=1, max_digits=8, null=True,
                verbose_name='Precisión GPS (metros)',
            ),
        ),
    ]
