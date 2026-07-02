from django.db import migrations, models


class Migration(migrations.Migration):

    dependencies = [
        ("app_estacionamiento", "0037_tarifa_precio_moto_null"),
    ]

    operations = [
        migrations.AddField(
            model_name="cierrecaja",
            name="periodo",
            field=models.CharField(
                blank=True,
                choices=[("diario", "Diario"), ("semanal", "Semanal"), ("mensual", "Mensual")],
                default="",
                max_length=10,
                verbose_name="Período",
            ),
        ),
    ]
