from django.db import migrations, models


class Migration(migrations.Migration):

    dependencies = [
        ("app_estacionamiento", "0032_cierrecaja_comision"),
    ]

    operations = [
        migrations.AddField(
            model_name="tarifa",
            name="monto_infraccion",
            field=models.DecimalField(
                decimal_places=2,
                default=0,
                help_text="Monto fijo cobrado por cada infracción.",
                max_digits=10,
            ),
        ),
    ]
