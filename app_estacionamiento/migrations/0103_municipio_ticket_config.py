"""
Migración 0103 — Configuración del ticket de infracción por municipio.

Agrega dos campos a Municipio:
  - ticket_fuente_size: controla el tamaño base del texto ESC/POS (1-3).
  - ticket_qr_size:     controla el módulo QR ESC/POS (1-8).

Ambos tienen default, así que no requieren datos previos.
"""

from django.db import migrations, models


class Migration(migrations.Migration):

    dependencies = [
        ("app_estacionamiento", "0102_alter_subcuadra_help_text_verbose_name"),
    ]

    operations = [
        migrations.AddField(
            model_name="municipio",
            name="ticket_fuente_size",
            field=models.PositiveSmallIntegerField(
                default=2,
                help_text="1=normal · 2=doble alto (recomendado 58mm) · 3=doble alto+ancho (80mm)",
                verbose_name="Tamaño de fuente del ticket (1-3)",
            ),
        ),
        migrations.AddField(
            model_name="municipio",
            name="ticket_qr_size",
            field=models.PositiveSmallIntegerField(
                default=4,
                help_text="Módulo QR ESC/POS. 3=pequeño · 4=normal · 6=grande. Default: 4.",
                verbose_name="Tamaño del módulo QR del ticket (1-8)",
            ),
        ),
    ]
