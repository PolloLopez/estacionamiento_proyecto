from django.db import migrations, models


class Migration(migrations.Migration):

    dependencies = [
        ("app_estacionamiento", "0090_municipio_admin_puede_configurar_tolerancia"),
    ]

    operations = [
        migrations.AddField(
            model_name="subcuadra",
            name="calles_entre",
            field=models.CharField(
                blank=True,
                default="",
                help_text="Opcional. Ej: 'Entre Av. 14 y Av. 16'. Ayuda a los conductores que no conocen la altura.",
                max_length=200,
                verbose_name="Entre calles",
            ),
        ),
    ]
