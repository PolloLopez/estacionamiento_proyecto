from django.db import migrations, models


class Migration(migrations.Migration):
    """
    Agrega configuración de formato para el pie del ticket de infracción
    (secciones 'Leyenda de horarios' y 'Marco legal / Ordenanza'):
      - ticket_pie_fuente_size: tamaño de fuente (1=normal, 2=doble alto, 3=doble alto+ancho)
      - ticket_pie_negrita: si el texto se imprime en negrita
    """

    dependencies = [
        ("app_estacionamiento", "0106_municipio_altura_solo_numeros"),
    ]

    operations = [
        migrations.AddField(
            model_name="municipio",
            name="ticket_pie_fuente_size",
            field=models.PositiveSmallIntegerField(
                default=1,
                verbose_name="Tamaño de fuente del pie (leyenda + ordenanza)",
                help_text="1=normal (recomendado) · 2=doble alto · 3=doble alto+ancho",
            ),
        ),
        migrations.AddField(
            model_name="municipio",
            name="ticket_pie_negrita",
            field=models.BooleanField(
                default=False,
                verbose_name="Negrita en el pie (leyenda + ordenanza)",
                help_text="Activo: imprime en negrita la leyenda de horarios y el marco legal.",
            ),
        ),
    ]
