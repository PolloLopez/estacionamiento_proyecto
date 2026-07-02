from django.db import migrations


class Migration(migrations.Migration):
    """
    Renombra Estacionamiento.duracion_min → duracion_horas.
    El campo siempre almacenó horas (no minutos) — el nombre era engañoso.
    """

    dependencies = [
        ("app_estacionamiento", "0035_nuevos_modelos_y_campos"),
    ]

    operations = [
        migrations.RenameField(
            model_name="estacionamiento",
            old_name="duracion_min",
            new_name="duracion_horas",
        ),
    ]
