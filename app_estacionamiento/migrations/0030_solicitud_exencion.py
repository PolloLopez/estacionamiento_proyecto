"""
Migración 0030 — Creada manualmente

Extiende SolicitudVerificacion con campos para solicitud de exención:

  - solicita_exencion       BooleanField
  - tipo_exencion_solicitado CharField (discapacidad / vecino_frentista)
  - vehiculo                ForeignKey → Vehiculo (nullable)
  - documento_1             FileField (CUD o licencia, según tipo)
  - documento_2             FileField (cédula de domicilio, solo frentista)
  - estado_exencion         CharField (pendiente / aprobada / rechazada / "")
  - notas_exencion_admin    TextField
"""

from django.db import migrations, models
import django.db.models.deletion


class Migration(migrations.Migration):

    dependencies = [
        ("app_estacionamiento", "0029_verificacion_conductor"),
    ]

    operations = [

        migrations.AddField(
            model_name="solicitudverificacion",
            name="solicita_exencion",
            field=models.BooleanField(default=False, verbose_name="¿Solicita exención?"),
        ),

        migrations.AddField(
            model_name="solicitudverificacion",
            name="tipo_exencion_solicitado",
            field=models.CharField(
                blank=True,
                choices=[
                    ("discapacidad",     "Discapacidad (CUD)"),
                    ("vecino_frentista", "Vecino frentista"),
                ],
                max_length=30,
                verbose_name="Tipo de exención solicitada",
            ),
        ),

        migrations.AddField(
            model_name="solicitudverificacion",
            name="vehiculo",
            field=models.ForeignKey(
                blank=True,
                null=True,
                on_delete=django.db.models.deletion.SET_NULL,
                related_name="solicitudes_exencion",
                to="app_estacionamiento.vehiculo",
                verbose_name="Vehículo a exentar",
            ),
        ),

        migrations.AddField(
            model_name="solicitudverificacion",
            name="documento_1",
            field=models.FileField(
                blank=True,
                null=True,
                upload_to="solicitudes_verificacion/",
                verbose_name="Documento principal",
            ),
        ),

        migrations.AddField(
            model_name="solicitudverificacion",
            name="documento_2",
            field=models.FileField(
                blank=True,
                null=True,
                upload_to="solicitudes_verificacion/",
                verbose_name="Cédula / domicilio (solo frentista)",
            ),
        ),

        migrations.AddField(
            model_name="solicitudverificacion",
            name="estado_exencion",
            field=models.CharField(
                blank=True,
                choices=[
                    ("pendiente",  "Pendiente"),
                    ("aprobada",   "Aprobada"),
                    ("rechazada",  "Rechazada"),
                ],
                default="",
                max_length=20,
                verbose_name="Estado de la exención",
            ),
        ),

        migrations.AddField(
            model_name="solicitudverificacion",
            name="notas_exencion_admin",
            field=models.TextField(
                blank=True,
                help_text="Motivo de rechazo de la exención.",
                verbose_name="Notas del admin (exención)",
            ),
        ),

        # Actualizar el verbose_name del campo notas_admin existente para claridad
        migrations.AlterField(
            model_name="solicitudverificacion",
            name="notas_admin",
            field=models.TextField(
                blank=True,
                help_text="Motivo de rechazo de identidad u observaciones.",
                verbose_name="Notas del admin (identidad)",
            ),
        ),

    ]
