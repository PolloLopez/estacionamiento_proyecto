from django.db import migrations, models


class Migration(migrations.Migration):

    dependencies = [
        ("app_estacionamiento", "0038_cierrecaja_periodo"),
    ]

    operations = [
        migrations.AlterField(
            model_name="abonomensual",
            name="medio_pago",
            field=models.CharField(
                choices=[
                    ("efectivo", "Efectivo"),
                    ("mercadopago", "MercadoPago"),
                    ("saldo", "Saldo digital"),
                ],
                default="efectivo",
                max_length=20,
            ),
        ),
    ]
