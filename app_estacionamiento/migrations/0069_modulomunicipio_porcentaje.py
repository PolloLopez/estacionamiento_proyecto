from django.db import migrations, models


class Migration(migrations.Migration):

    dependencies = [
        ("app_estacionamiento", "0068_liquidacion_plataforma"),
    ]

    operations = [
        migrations.AddField(
            model_name="modulomunicipio",
            name="porcentaje_modulo",
            field=models.DecimalField(
                decimal_places=2,
                default=0,
                help_text="Porcentaje adicional sobre recaudación por este módulo. Se suma al % base de la plataforma.",
                max_digits=5,
            ),
        ),
    ]
