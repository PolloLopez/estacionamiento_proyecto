"""
Migración 0082: Descuento para conductores verificados en Municipio.

Agrega:
  - descuento_verificados_pct: porcentaje de descuento (null = desactivado)
  - descuento_solo_vecinos:    si es True, solo aplica a vecinos verificados
"""

from django.db import migrations, models


class Migration(migrations.Migration):

    dependencies = [
        ("app_estacionamiento", "0081_notificacion_tipo_usuario_notif_prefs"),
    ]

    operations = [
        migrations.AddField(
            model_name="municipio",
            name="descuento_verificados_pct",
            field=models.DecimalField(
                blank=True,
                decimal_places=2,
                help_text=(
                    "Porcentaje de descuento sobre el costo de estacionamiento "
                    "para conductores con identidad verificada. "
                    "Vacío = descuento desactivado."
                ),
                max_digits=5,
                null=True,
                verbose_name="Descuento para verificados (%)",
            ),
        ),
        migrations.AddField(
            model_name="municipio",
            name="descuento_solo_vecinos",
            field=models.BooleanField(
                default=False,
                help_text=(
                    "Si está activo, el descuento solo aplica a conductores verificados "
                    "que además estén marcados como vecinos del municipio. "
                    "Si está inactivo, aplica a todos los conductores verificados."
                ),
                verbose_name="Solo vecinos del municipio",
            ),
        ),
    ]
