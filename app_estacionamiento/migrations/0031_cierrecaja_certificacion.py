"""
Migración 0031 — Creada manualmente

Agrega campos de certificación al modelo CierreCaja:
  - certificado       BooleanField (el admin auditó el cierre)
  - certificado_en    DateTimeField (cuándo lo certificó)
  - certificado_por   ForeignKey → Usuario (quién lo certificó)
"""

from django.db import migrations, models
import django.db.models.deletion


class Migration(migrations.Migration):

    dependencies = [
        ("app_estacionamiento", "0030_solicitud_exencion"),
    ]

    operations = [

        migrations.AddField(
            model_name="cierrecaja",
            name="certificado",
            field=models.BooleanField(
                default=False,
                help_text="El admin auditó y certificó este cierre.",
                verbose_name="Certificado",
            ),
        ),

        migrations.AddField(
            model_name="cierrecaja",
            name="certificado_en",
            field=models.DateTimeField(
                blank=True,
                null=True,
                help_text="Fecha en que el admin certificó el cierre.",
                verbose_name="Fecha de certificación",
            ),
        ),

        migrations.AddField(
            model_name="cierrecaja",
            name="certificado_por",
            field=models.ForeignKey(
                blank=True,
                null=True,
                on_delete=django.db.models.deletion.SET_NULL,
                related_name="cierres_certificados",
                to="app_estacionamiento.usuario",
                help_text="Admin que certificó el cierre.",
                verbose_name="Certificado por",
            ),
        ),

        # Agregar ordering a CierreCaja
        migrations.AlterModelOptions(
            name="cierrecaja",
            options={"ordering": ["-fecha_cierre"]},
        ),

    ]
