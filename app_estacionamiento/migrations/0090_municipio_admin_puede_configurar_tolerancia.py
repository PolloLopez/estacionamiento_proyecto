from django.db import migrations, models


class Migration(migrations.Migration):

    dependencies = [
        ("app_estacionamiento", "0089_municipio_mapa_infracciones_activo"),
    ]

    operations = [
        migrations.AddField(
            model_name="municipio",
            name="admin_puede_configurar_tolerancia",
            field=models.BooleanField(
                default=True,
                help_text="Si está activo, el admin municipal puede editar los minutos de gracia de la tolerancia de multa desde /admin-tarifas/. Si está inactivo, solo el superadmin puede modificarlo.",
                verbose_name="Admin puede configurar tolerancia de multa",
            ),
        ),
    ]
