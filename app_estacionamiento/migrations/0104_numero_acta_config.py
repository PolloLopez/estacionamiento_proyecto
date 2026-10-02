from django.db import migrations, models


class Migration(migrations.Migration):
    """
    Agrega campos para la numeración correlativa de actas de infracción:
    - Infraccion.numero_acta: número del acta (null para infracciones viejas)
    - Municipio.proximo_numero_acta: superadmin lo ajusta para continuar numeración anterior
    - Municipio.mostrar_inspector_en_ticket: superadmin decide si se imprime el nombre
    """

    dependencies = [
        ("app_estacionamiento", "0103_municipio_ticket_config"),
    ]

    operations = [
        migrations.AddField(
            model_name="infraccion",
            name="numero_acta",
            field=models.PositiveIntegerField(
                blank=True,
                null=True,
                verbose_name="Número de acta",
                help_text="Número correlativo del acta. Asignado automáticamente al crear la infracción.",
            ),
        ),
        migrations.AddField(
            model_name="municipio",
            name="proximo_numero_acta",
            field=models.PositiveIntegerField(
                default=1,
                verbose_name="Próximo número de acta",
                help_text="Número que se asignará al próximo acta creada.",
            ),
        ),
        migrations.AddField(
            model_name="municipio",
            name="mostrar_inspector_en_ticket",
            field=models.BooleanField(
                default=True,
                verbose_name="Mostrar inspector en ticket",
                help_text="Si está activo, el nombre del inspector aparece en el acta impresa.",
            ),
        ),
    ]
