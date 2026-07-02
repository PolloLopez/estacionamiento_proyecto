from django.db import migrations, models


class Migration(migrations.Migration):
    """
    Cambia precio_por_hora_moto a null=True/blank=True.
    null = "usar tarifa de auto" (más claro que default=0).
    """

    dependencies = [
        ("app_estacionamiento", "0036_rename_duracion_min_a_duracion_horas"),
    ]

    operations = [
        migrations.AlterField(
            model_name="tarifa",
            name="precio_por_hora_moto",
            field=models.DecimalField(
                max_digits=6,
                decimal_places=2,
                null=True,
                blank=True,
                verbose_name="Precio/hora moto",
                help_text="Tarifa por hora para motos. Vacío = igual que autos.",
            ),
        ),
    ]
