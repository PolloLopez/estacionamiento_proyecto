from django.db import migrations, models


class Migration(migrations.Migration):

    dependencies = [
        ("app_estacionamiento", "0024_remove_infraccion_created_at_remove_infraccion_fecha_and_more"),
    ]

    operations = [
        migrations.AddField(
            model_name="usuario",
            name="saldo_limite",
            field=models.DecimalField(
                decimal_places=2,
                default=0,
                help_text="Límite de deuda antes de bloquear al usuario. 0 = sin límite.",
                max_digits=10,
            ),
        ),
        migrations.AddField(
            model_name="usuario",
            name="porcentaje_ganancia",
            field=models.DecimalField(
                decimal_places=2,
                default=0,
                help_text="Porcentaje del total cobrado que el usuario retiene como ganancia.",
                max_digits=5,
            ),
        ),
        migrations.AddField(
            model_name="usuario",
            name="periodicidad_rendicion",
            field=models.CharField(
                choices=[
                    ("diaria", "Diaria"),
                    ("semanal", "Semanal"),
                    ("mensual", "Mensual"),
                ],
                default="semanal",
                help_text="Con qué frecuencia debe rendir cuentas al municipio.",
                max_length=10,
            ),
        ),
    ]
