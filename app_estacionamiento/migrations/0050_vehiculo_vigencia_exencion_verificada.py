"""
Migración 0050: vigencia_exencion y exencion_verificada en Vehiculo.

- vigencia_exencion: fecha hasta la que rige la exención (null = indefinida).
- exencion_verificada: False en vehículos importados desde Excel (pendientes de
  que el admin contacte al titular para completar email, condición, etc.).
  Los vehículos ya existentes quedan con True (admin los cargó manualmente).
"""
from django.db import migrations, models


class Migration(migrations.Migration):

    dependencies = [
        ("app_estacionamiento", "0049_plantilla_documento"),
    ]

    operations = [
        migrations.AddField(
            model_name="vehiculo",
            name="vigencia_exencion",
            field=models.DateField(
                blank=True,
                null=True,
                verbose_name="Vigencia de exención",
                help_text="Fecha hasta la que rige la exención. Vacío = sin vencimiento.",
            ),
        ),
        migrations.AddField(
            model_name="vehiculo",
            name="exencion_verificada",
            field=models.BooleanField(
                default=True,
                verbose_name="Exención verificada",
                help_text="False = importado, pendiente de verificación por el admin.",
            ),
        ),
    ]
