"""
Migración 0027 — Creada manualmente

Cambios:
  - Municipio: agrega logo, color_primario, color_secundario, nombre_sistema
    para soportar branding personalizado por municipio.
"""

from django.db import migrations, models


class Migration(migrations.Migration):

    dependencies = [
        ("app_estacionamiento", "0026_horarios_exenciones_tipo"),
    ]

    operations = [
        migrations.AddField(
            model_name="municipio",
            name="logo",
            field=models.ImageField(
                blank=True,
                null=True,
                upload_to="municipios/logos/",
                verbose_name="Logo del municipio",
                help_text="Imagen PNG/SVG con fondo transparente.",
            ),
        ),
        migrations.AddField(
            model_name="municipio",
            name="color_primario",
            field=models.CharField(
                default="#1a7a3c",
                max_length=7,
                verbose_name="Color primario",
                help_text="Color principal en hex (ej: #1a7a3c).",
            ),
        ),
        migrations.AddField(
            model_name="municipio",
            name="color_secundario",
            field=models.CharField(
                default="#155f2e",
                max_length=7,
                verbose_name="Color secundario",
                help_text="Color hover/acento en hex (ej: #155f2e).",
            ),
        ),
        migrations.AddField(
            model_name="municipio",
            name="nombre_sistema",
            field=models.CharField(
                blank=True,
                default="Estacionamiento Medido",
                max_length=200,
                verbose_name="Nombre del sistema",
            ),
        ),
    ]
