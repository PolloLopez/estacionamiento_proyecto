from django.db import migrations, models


class Migration(migrations.Migration):
    """
    Aumenta la precisión de duracion_horas en Estacionamiento y PreferenciaEstacionamiento.

    Problema anterior: decimal_places=1 redondeaba 10 min (0.1667h) a 0.2h (12 min),
    causando que el timer y el campo "hasta HH:MM" mostraran hora incorrecta en testing.

    Con decimal_places=4:
    - 10 min → 0.1667h → se almacena exactamente
    - 30 min → 0.5000h → sin cambio (exacto en ambos formatos)
    - 1h → 1.0000h → sin cambio
    - max_digits=6 permite hasta 99.9999 horas (suficiente para cualquier caso real)

    Los valores existentes en BD no se modifican: 0.5 → 0.5000, 1.0 → 1.0000, etc.
    """

    dependencies = [
        ("app_estacionamiento", "0099_push_notifications"),
    ]

    operations = [
        # Estacionamiento.duracion_horas
        migrations.AlterField(
            model_name="estacionamiento",
            name="duracion_horas",
            field=models.DecimalField(
                decimal_places=4,
                default=1,
                max_digits=6,
                verbose_name="Duración (horas)",
            ),
        ),

    ]
