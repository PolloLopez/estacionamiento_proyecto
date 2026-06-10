"""
Migración 0028 — Creada manualmente

Corrige las diferencias entre la migración 0027 (creada manualmente con
help_texts abreviados) y el estado actual de models.py.

Cambios:
  - Municipio.logo:           help_text completo con recomendación de altura
  - Municipio.color_primario: help_text descriptivo con contexto de uso
  - Municipio.color_secundario: help_text con contexto de uso
  - Municipio.nombre_sistema: agrega help_text (faltaba en 0027)
  - HorarioEstacionamiento.id: verbose_name="ID" (Django 5.x default)
  - DiaEspecial.id:            verbose_name="ID" (Django 5.x default)
"""

from django.db import migrations, models


class Migration(migrations.Migration):

    dependencies = [
        ("app_estacionamiento", "0027_municipio_branding"),
    ]

    operations = [

        # ── Corregir help_text de Municipio.logo ──────────────────────────────
        migrations.AlterField(
            model_name="municipio",
            name="logo",
            field=models.ImageField(
                blank=True,
                null=True,
                upload_to="municipios/logos/",
                verbose_name="Logo del municipio",
                help_text="Imagen PNG\\SVG con fondo transparente. Altura recomendada: 80px.",
            ),
        ),

        # ── Corregir help_text de Municipio.color_primario ───────────────────
        migrations.AlterField(
            model_name="municipio",
            name="color_primario",
            field=models.CharField(
                max_length=7,
                default="#1a7a3c",
                verbose_name="Color primario",
                help_text="Color principal de la barra de navegación y botones (ej: #1a7a3c).",
            ),
        ),

        # ── Corregir help_text de Municipio.color_secundario ─────────────────
        migrations.AlterField(
            model_name="municipio",
            name="color_secundario",
            field=models.CharField(
                max_length=7,
                default="#155f2e",
                verbose_name="Color secundario",
                help_text="Color de hover y acento (ej: #155f2e). Suele ser el primario más oscuro.",
            ),
        ),

        # ── Agregar help_text a Municipio.nombre_sistema ─────────────────────
        migrations.AlterField(
            model_name="municipio",
            name="nombre_sistema",
            field=models.CharField(
                blank=True,
                max_length=200,
                default="Estacionamiento Medido",
                verbose_name="Nombre del sistema",
                help_text="Texto que aparece en la barra de navegación si no hay logo.",
            ),
        ),

        # ── verbose_name="ID" en HorarioEstacionamiento (Django 5.x default) ─
        migrations.AlterField(
            model_name="horarioestacionamiento",
            name="id",
            field=models.BigAutoField(
                auto_created=True,
                primary_key=True,
                serialize=False,
                verbose_name="ID",
            ),
        ),

        # ── verbose_name="ID" en DiaEspecial (Django 5.x default) ────────────
        migrations.AlterField(
            model_name="diaespecial",
            name="id",
            field=models.BigAutoField(
                auto_created=True,
                primary_key=True,
                serialize=False,
                verbose_name="ID",
            ),
        ),

    ]
