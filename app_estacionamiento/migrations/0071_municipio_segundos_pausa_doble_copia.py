from django.db import migrations, models


class Migration(migrations.Migration):

    dependencies = [
        ("app_estacionamiento", "0070_sugerencia_eliminacion_cuenta"),
    ]

    operations = [
        migrations.AddField(
            model_name="municipio",
            name="segundos_pausa_doble_copia",
            field=models.PositiveIntegerField(
                default=0,
                verbose_name="Pausa entre copias (segundos, 0=confirmar)",
                help_text="0 = el inspector confirma antes de la segunda copia. Mayor que 0 = pausa automática en segundos.",
            ),
        ),
    ]
