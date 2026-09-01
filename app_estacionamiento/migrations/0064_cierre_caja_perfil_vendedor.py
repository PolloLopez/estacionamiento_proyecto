from django.db import migrations, models


class Migration(migrations.Migration):

    dependencies = [
        ("app_estacionamiento", "0063_descuentos_voluntarios"),
    ]

    operations = [
        # Actualiza el campo choices de ModuloMunicipio.modulo (solo metadatos)
        migrations.AlterField(
            model_name="modulomunicipio",
            name="modulo",
            field=models.CharField(
                max_length=50,
                choices=[
                    ("ocupacion_tiempo_real",     "Ocupación en tiempo real"),
                    ("reportes_comparativos",      "Reportes comparativos"),
                    ("balance_por_dominio",        "Balance por dominio"),
                    ("areas_reservadas",           "Áreas reservadas"),
                    ("geolocalizacion_inspector",  "Geolocalización del inspector"),
                    ("notificaciones_conductor",   "Notificaciones al conductor"),
                    ("informes_automaticos",       "Informes automáticos programados"),
                    ("descuentos_voluntarios",     "Descuentos por pago voluntario de infracciones"),
                    ("comisiones_vendedores",      "Comisiones por venta para vendedores"),
                ],
            ),
        ),
        # Perfil extendido de vendedor
        migrations.AddField(
            model_name="usuario",
            name="domicilio_comercial",
            field=models.CharField(
                blank=True,
                default="",
                max_length=255,
                verbose_name="Domicilio comercial",
                help_text="Dirección del kiosco o comercio del vendedor.",
            ),
        ),
        migrations.AddField(
            model_name="usuario",
            name="ubicacion_lat",
            field=models.DecimalField(
                blank=True,
                null=True,
                max_digits=9,
                decimal_places=6,
                verbose_name="Latitud del local",
            ),
        ),
        migrations.AddField(
            model_name="usuario",
            name="ubicacion_lon",
            field=models.DecimalField(
                blank=True,
                null=True,
                max_digits=9,
                decimal_places=6,
                verbose_name="Longitud del local",
            ),
        ),
        # Frecuencia de cierre de caja por municipio
        migrations.AddField(
            model_name="municipio",
            name="frecuencia_cierre_caja",
            field=models.CharField(
                max_length=10,
                choices=[
                    ("diaria", "Diaria"),
                    ("semanal", "Semanal"),
                    ("mensual", "Mensual"),
                ],
                default="diaria",
                verbose_name="Frecuencia de cierre de caja (vendedores)",
                help_text="Cada cuánto se espera que los vendedores cierren su caja.",
            ),
        ),
    ]
