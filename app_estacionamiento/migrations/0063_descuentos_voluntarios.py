# app_estacionamiento/migrations/0063_descuentos_voluntarios.py
"""
Migración: módulo premium "descuentos_voluntarios" + campos de descuento en Tarifa e Infraccion.

Cambios:
- ModuloMunicipio.modulo: agrega choice "descuentos_voluntarios" (metadata only, sin cambio de schema)
- Tarifa: 4 campos nuevos nullable (descuento_horas_plazo, descuento_horas_pct,
          descuento_dias_plazo, descuento_dias_pct)
- Infraccion: 3 campos nuevos nullable (monto_pagado, descuento_pct_aplicado, descuento_motivo)

Todos los campos nuevos son null=True o blank=True → no requieren datos previos.
Sin cambios en tablas existentes de datos.
"""

from django.db import migrations, models


class Migration(migrations.Migration):

    dependencies = [
        ("app_estacionamiento", "0062_verificacioninspector_set_null"),
    ]

    operations = [
        # ── ModuloMunicipio.modulo: ampliar choices (solo metadata Django) ──
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
                ],
            ),
        ),

        # ── Tarifa: campos de descuento (nullable → no afectan filas existentes) ──
        migrations.AddField(
            model_name="tarifa",
            name="descuento_horas_plazo",
            field=models.IntegerField(
                null=True, blank=True,
                verbose_name="Plazo en horas para descuento mayor",
                help_text="Horas desde el acta dentro de las cuales aplica el descuento alto.",
            ),
        ),
        migrations.AddField(
            model_name="tarifa",
            name="descuento_horas_pct",
            field=models.DecimalField(
                max_digits=5, decimal_places=2, null=True, blank=True,
                verbose_name="Descuento (%) por pago en horas",
                help_text="Porcentaje de descuento si el conductor paga dentro del plazo en horas.",
            ),
        ),
        migrations.AddField(
            model_name="tarifa",
            name="descuento_dias_plazo",
            field=models.IntegerField(
                null=True, blank=True,
                verbose_name="Plazo en días para descuento menor",
                help_text="Días desde el acta dentro de los cuales aplica el descuento bajo.",
            ),
        ),
        migrations.AddField(
            model_name="tarifa",
            name="descuento_dias_pct",
            field=models.DecimalField(
                max_digits=5, decimal_places=2, null=True, blank=True,
                verbose_name="Descuento (%) por pago en días",
                help_text="Porcentaje de descuento si el conductor paga dentro del plazo en días.",
            ),
        ),

        # ── Infraccion: trazabilidad del descuento aplicado ──
        migrations.AddField(
            model_name="infraccion",
            name="monto_pagado",
            field=models.DecimalField(
                max_digits=10, decimal_places=2, null=True, blank=True,
                verbose_name="Monto efectivamente cobrado",
                help_text="Monto cobrado al conductor. Puede diferir de 'monto' si hubo descuento.",
            ),
        ),
        migrations.AddField(
            model_name="infraccion",
            name="descuento_pct_aplicado",
            field=models.DecimalField(
                max_digits=5, decimal_places=2, null=True, blank=True,
                verbose_name="Descuento aplicado (%)",
            ),
        ),
        migrations.AddField(
            model_name="infraccion",
            name="descuento_motivo",
            field=models.CharField(
                max_length=100, blank=True, default="",
                verbose_name="Motivo del descuento",
                help_text="Ej: 'Pago dentro de 2h'. Vacío si no hubo descuento.",
            ),
        ),
    ]
