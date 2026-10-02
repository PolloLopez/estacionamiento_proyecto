from django.db import migrations, models


class Migration(migrations.Migration):

    dependencies = [
        ("app_estacionamiento", "0105_rendicion_ticket_tesoreria"),
    ]

    operations = [
        migrations.AddField(
            model_name="municipio",
            name="altura_solo_numeros",
            field=models.BooleanField(
                default=True,
                verbose_name="Alturas solo numéricas (inspector)",
                help_text=(
                    "Si está activo, el teclado del celular muestra solo números al ingresar "
                    "la altura en el selector de subcuadra del inspector. "
                    "Desactivar si el municipio usa alturas alfanuméricas (ej: Km 3.5, 150 bis)."
                ),
            ),
        ),
    ]
