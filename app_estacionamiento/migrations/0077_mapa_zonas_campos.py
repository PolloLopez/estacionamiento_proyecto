from django.db import migrations, models


class Migration(migrations.Migration):
    """
    Agrega campos para el mapa de zonas:
    - Subcuadra.tipo_zona: distingue zonas pagadas de zonas libres.
    - Municipio.sede_lat / sede_lon: coordenadas de la oficina/sede del admin,
      para mostrarla como pin en el mapa de zonas.
    """

    dependencies = [
        ('app_estacionamiento', '0076_municipio_inspector_ve_sus_infracciones'),
    ]

    operations = [
        # ── Subcuadra: tipo de zona (pagado / libre) ───────────────────────────
        migrations.AddField(
            model_name='subcuadra',
            name='tipo_zona',
            field=models.CharField(
                max_length=10,
                choices=[('pagado', 'Zona pagada'), ('libre', 'Zona libre')],
                default='pagado',
                verbose_name='Tipo de zona',
                help_text='Pagado = estacionamiento medido. Libre = sin cobro.',
            ),
        ),

        # ── Municipio: coordenadas de la sede ─────────────────────────────────
        migrations.AddField(
            model_name='municipio',
            name='sede_lat',
            field=models.DecimalField(
                max_digits=9, decimal_places=6,
                null=True, blank=True,
                verbose_name='Latitud sede municipal',
                help_text='Latitud de la oficina o sede del administrador.',
            ),
        ),
        migrations.AddField(
            model_name='municipio',
            name='sede_lon',
            field=models.DecimalField(
                max_digits=9, decimal_places=6,
                null=True, blank=True,
                verbose_name='Longitud sede municipal',
                help_text='Longitud de la oficina o sede del administrador.',
            ),
        ),
    ]
