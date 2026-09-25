from django.db import migrations, models


class Migration(migrations.Migration):

    dependencies = [
        ("app_estacionamiento", "0094_usuario_nombre_negocio"),
    ]

    operations = [
        migrations.AddField(
            model_name="subcuadra",
            name="interseccion_1",
            field=models.CharField(
                blank=True,
                default="",
                help_text="Primera calle de la intersección. Ej: Av. San Martín",
                max_length=100,
                verbose_name="Intersección 1",
            ),
        ),
        migrations.AddField(
            model_name="subcuadra",
            name="interseccion_2",
            field=models.CharField(
                blank=True,
                default="",
                help_text="Segunda calle de la intersección. Ej: Belgrano",
                max_length=100,
                verbose_name="Intersección 2",
            ),
        ),
    ]
