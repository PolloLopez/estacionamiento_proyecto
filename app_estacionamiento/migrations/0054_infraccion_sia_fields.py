from django.db import migrations, models


class Migration(migrations.Migration):
    """
    Agrega campos SIA (Símbolo Internacional de Acceso) a Infraccion
    para registrar verificaciones de certificados de discapacidad ANDIS.
    """

    dependencies = [
        ('app_estacionamiento', '0053_municipio_info_institucional_tarifa_maxdigits'),
    ]

    operations = [
        migrations.AddField(
            model_name='infraccion',
            name='sia_presentado',
            field=models.BooleanField(default=False),
        ),
        migrations.AddField(
            model_name='infraccion',
            name='sia_verificado',
            field=models.BooleanField(default=False),
        ),
        migrations.AddField(
            model_name='infraccion',
            name='sia_estado',
            field=models.CharField(blank=True, default='', max_length=40),
        ),
        migrations.AddField(
            model_name='infraccion',
            name='sia_url',
            field=models.CharField(blank=True, default='', max_length=500),
        ),
        migrations.AddField(
            model_name='infraccion',
            name='sia_code',
            field=models.CharField(blank=True, default='', max_length=100),
        ),
        migrations.AddField(
            model_name='infraccion',
            name='sia_patente_sia',
            field=models.CharField(blank=True, default='', max_length=20),
        ),
        migrations.AddField(
            model_name='infraccion',
            name='sia_vencimiento',
            field=models.DateField(blank=True, null=True),
        ),
        migrations.AddField(
            model_name='infraccion',
            name='sia_nci',
            field=models.CharField(blank=True, default='', max_length=30),
        ),
        migrations.AddField(
            model_name='infraccion',
            name='sia_titular',
            field=models.CharField(blank=True, default='', max_length=200),
        ),
        migrations.AddField(
            model_name='infraccion',
            name='sia_verificado_en',
            field=models.DateTimeField(blank=True, null=True),
        ),
        migrations.AddField(
            model_name='infraccion',
            name='sia_observacion',
            field=models.TextField(blank=True, default=''),
        ),
    ]
