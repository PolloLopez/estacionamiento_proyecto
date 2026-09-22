from django.db import migrations, models


class Migration(migrations.Migration):

    dependencies = [
        ("app_estacionamiento", "0085_billetera_conductor"),
    ]

    operations = [
        migrations.AddField(
            model_name="municipio",
            name="modulo_informes_activo",
            field=models.BooleanField(
                default=False,
                verbose_name="Módulo de informes por mail",
                help_text=(
                    "Activa el tab 'Informes' en /admin-rendiciones/ para que el admin "
                    "configure destinatarios y envíe resúmenes periódicos por mail. "
                    "Por defecto desactivado — el superadmin lo habilita por municipio."
                ),
            ),
        ),
    ]
