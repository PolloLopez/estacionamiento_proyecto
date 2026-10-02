from django.db import migrations, models


class Migration(migrations.Migration):
    """
    Agrega Rendicion.numero_ticket_tesoreria: referencia interna del municipio
    (folio, expediente, número de ticket) para trazabilidad hacia tesorería.
    Campo opcional — las rendiciones existentes quedan con string vacío.
    """

    dependencies = [
        ("app_estacionamiento", "0104_numero_acta_config"),
    ]

    operations = [
        migrations.AddField(
            model_name="rendicion",
            name="numero_ticket_tesoreria",
            field=models.CharField(
                blank=True,
                default="",
                max_length=100,
                verbose_name="Número de ticket / expediente municipal",
                help_text="Referencia interna del municipio para esta rendición (folio, expediente, etc.). Opcional.",
            ),
        ),
    ]
