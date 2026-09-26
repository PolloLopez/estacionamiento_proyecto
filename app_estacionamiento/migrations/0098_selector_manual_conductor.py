from django.db import migrations, models


class Migration(migrations.Migration):

    dependencies = [
        ("app_estacionamiento", "0097_verificacion_documental"),
    ]

    operations = [
        migrations.AddField(
            model_name="municipio",
            name="selector_manual_conductor_activo",
            field=models.BooleanField(
                default=True,
                verbose_name="Selector manual de subcuadra activo (conductor)",
                help_text="Si está desactivado, el conductor solo puede usar el GPS para indicar su ubicación.",
            ),
        ),
    ]
