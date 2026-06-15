from django.db import migrations, models


class Migration(migrations.Migration):

    dependencies = [
        ("app_estacionamiento", "0031_cierrecaja_certificacion"),
    ]

    operations = [
        migrations.AddField(
            model_name="cierrecaja",
            name="porcentaje_ganancia_aplicado",
            field=models.DecimalField(
                decimal_places=2,
                default=0,
                help_text="Porcentaje de ganancia del usuario al momento del cierre.",
                max_digits=5,
            ),
        ),
        migrations.AddField(
            model_name="cierrecaja",
            name="ganancia_usuario",
            field=models.DecimalField(
                decimal_places=2,
                default=0,
                help_text="Monto que retiene el usuario (comisión).",
                max_digits=10,
            ),
        ),
        migrations.AddField(
            model_name="cierrecaja",
            name="monto_municipio",
            field=models.DecimalField(
                decimal_places=2,
                default=0,
                help_text="Monto neto que le corresponde al municipio.",
                max_digits=10,
            ),
        ),
    ]
