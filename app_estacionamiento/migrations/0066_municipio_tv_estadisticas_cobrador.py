from django.db import migrations, models


class Migration(migrations.Migration):

    dependencies = [
        ("app_estacionamiento", "0065_reintegro_residentes"),
    ]

    operations = [
        # Campos operacionales de Municipio
        migrations.AddField(
            model_name="municipio",
            name="estadisticas_inspectores_activo",
            field=models.BooleanField(
                default=True,
                verbose_name="Mostrar estadísticas a inspectores",
                help_text="Si está desactivado, el inspector no ve sus métricas en el panel.",
            ),
        ),
        migrations.AddField(
            model_name="municipio",
            name="token_tv",
            field=models.CharField(
                max_length=64, blank=True, default="",
                verbose_name="Token de dashboard TV",
                help_text="Token de solo lectura para /tv/<token>/. Vacío = desactivado.",
            ),
        ),
        # Actualiza choices de ModuloMunicipio.modulo (solo metadatos Django, sin cambio en BD)
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
                    ("reintegro_residentes",       "Reintegro de estacionamiento para vecinos"),
                    ("cobrador_inspector",         "Inspectores pueden cobrar infracciones en campo"),
                ],
            ),
        ),
    ]
