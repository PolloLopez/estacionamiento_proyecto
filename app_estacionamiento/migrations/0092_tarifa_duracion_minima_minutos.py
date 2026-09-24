from django.db import migrations, models


class Migration(migrations.Migration):

    dependencies = [
        ("app_estacionamiento", "0091_subcuadra_calles_entre"),
    ]

    operations = [
        migrations.AddField(
            model_name="tarifa",
            name="duracion_minima_minutos",
            field=models.IntegerField(
                default=30,
                verbose_name="Duración mínima (min)",
                help_text="Mínimo de minutos que puede comprar un conductor. Múltiplo de 30. El máximo lo define el horario de cierre.",
            ),
        ),
    ]
