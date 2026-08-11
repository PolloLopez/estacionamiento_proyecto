"""
Migración 0049: modelo PlantillaDocumento.

El superadmin configura el texto de encabezado/cuerpo/pie de cada tipo de
comprobante/acta por municipio.  Si no hay plantilla, el sistema usa los
textos hardcodeados actuales (fallback sin romper nada).
"""
from django.db import migrations, models
import django.db.models.deletion


class Migration(migrations.Migration):

    dependencies = [
        ("app_estacionamiento", "0048_subcuadra_lat_lon"),
    ]

    operations = [
        migrations.CreateModel(
            name="PlantillaDocumento",
            fields=[
                ("id", models.BigAutoField(auto_created=True, primary_key=True, serialize=False, verbose_name="ID")),
                ("tipo", models.CharField(
                    choices=[
                        ("acta",             "Acta de infracción"),
                        ("cobro_hora",       "Comprobante cobro por hora"),
                        ("abono",            "Comprobante abono mensual"),
                        ("cobro_infraccion", "Comprobante pago de infracción"),
                        ("anulacion",        "Comprobante anulación de infracción"),
                    ],
                    max_length=20,
                )),
                ("encabezado", models.TextField(blank=True, verbose_name="Encabezado")),
                ("cuerpo",     models.TextField(blank=True, verbose_name="Cuerpo / base legal")),
                ("pie",        models.TextField(blank=True, verbose_name="Pie / instrucciones")),
                ("actualizado_en", models.DateTimeField(auto_now=True)),
                ("municipio", models.ForeignKey(
                    on_delete=django.db.models.deletion.CASCADE,
                    related_name="plantillas_documento",
                    to="app_estacionamiento.municipio",
                )),
            ],
            options={
                "verbose_name":        "Plantilla de documento",
                "verbose_name_plural": "Plantillas de documentos",
                "ordering":            ["municipio", "tipo"],
            },
        ),
        migrations.AddConstraint(
            model_name="plantilladocumento",
            constraint=models.UniqueConstraint(
                fields=["municipio", "tipo"],
                name="unique_plantilla_municipio_tipo",
            ),
        ),
    ]
