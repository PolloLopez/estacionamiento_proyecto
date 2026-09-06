from django.conf import settings
from django.db import migrations, models
import django.db.models.deletion


class Migration(migrations.Migration):

    dependencies = [
        ("app_estacionamiento", "0064_cierre_caja_perfil_vendedor"),
    ]

    operations = [
        # Actualiza choices de ModuloMunicipio.modulo (solo metadatos)
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
                ],
            ),
        ),
        # Campos de configuración de reintegro en Municipio
        migrations.AddField(
            model_name="municipio",
            name="reintegro_minutos",
            field=models.PositiveIntegerField(
                default=30,
                verbose_name="Minutos de reintegro por estacionamiento",
                help_text="Cuántos minutos se reintegran como saldo al conductor por cada estacionamiento.",
            ),
        ),
        migrations.AddField(
            model_name="municipio",
            name="reintegro_max_por_dia",
            field=models.PositiveIntegerField(
                default=1,
                verbose_name="Máx. reintegros por día (por conductor)",
                help_text="Límite de reintegros que un mismo conductor puede recibir en un día.",
            ),
        ),
        migrations.AddField(
            model_name="municipio",
            name="reintegro_alcance",
            field=models.CharField(
                max_length=20,
                choices=[
                    ("todos",      "Todos los conductores"),
                    ("residentes", "Solo residentes verificados"),
                ],
                default="residentes",
                verbose_name="Alcance del reintegro",
                help_text="A quiénes aplica el reintegro.",
            ),
        ),
        # Campos de residencia en Usuario
        migrations.AddField(
            model_name="usuario",
            name="es_residente_verificado",
            field=models.BooleanField(
                default=False,
                verbose_name="Residente verificado",
                help_text="El admin verificó que este conductor es vecino del municipio.",
            ),
        ),
        migrations.AddField(
            model_name="usuario",
            name="fecha_verificacion_residencia",
            field=models.DateField(
                null=True,
                blank=True,
                verbose_name="Fecha de verificación de residencia",
            ),
        ),
        # Modelo Reintegro
        migrations.CreateModel(
            name="Reintegro",
            fields=[
                ("id", models.BigAutoField(auto_created=True, primary_key=True, serialize=False, verbose_name="ID")),
                ("monto",     models.DecimalField(max_digits=10, decimal_places=2)),
                ("creado_en", models.DateTimeField(auto_now_add=True)),
                ("conductor", models.ForeignKey(
                    on_delete=django.db.models.deletion.PROTECT,
                    related_name="reintegros",
                    to=settings.AUTH_USER_MODEL,
                )),
                ("municipio", models.ForeignKey(
                    on_delete=django.db.models.deletion.PROTECT,
                    related_name="reintegros",
                    to="app_estacionamiento.municipio",
                )),
                ("estacionamiento", models.OneToOneField(
                    blank=True,
                    null=True,
                    on_delete=django.db.models.deletion.SET_NULL,
                    related_name="reintegro",
                    to="app_estacionamiento.estacionamiento",
                )),
            ],
            options={"ordering": ["-creado_en"]},
        ),
    ]
