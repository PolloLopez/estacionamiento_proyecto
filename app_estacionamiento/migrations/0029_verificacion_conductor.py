"""
Migración 0029 — Creada manualmente

Agrega el sistema de verificación de identidad para conductores.

Cambios:
  - Usuario.es_verificado: nuevo BooleanField (default=False)
  - SolicitudVerificacion: nuevo modelo con nombre, apellido, dni,
    telefono, fecha_solicitud, estado, notas_admin
"""

from django.conf import settings
from django.db import migrations, models
import django.db.models.deletion


class Migration(migrations.Migration):

    dependencies = [
        ("app_estacionamiento", "0028_corregir_help_texts"),
    ]

    operations = [

        # ── Nuevo campo en Usuario ────────────────────────────────────────────
        migrations.AddField(
            model_name="usuario",
            name="es_verificado",
            field=models.BooleanField(
                default=False,
                help_text="El admin verificó la identidad del conductor.",
            ),
        ),

        # ── Nuevo modelo SolicitudVerificacion ────────────────────────────────
        migrations.CreateModel(
            name="SolicitudVerificacion",
            fields=[
                (
                    "id",
                    models.BigAutoField(
                        auto_created=True,
                        primary_key=True,
                        serialize=False,
                        verbose_name="ID",
                    ),
                ),
                (
                    "usuario",
                    models.OneToOneField(
                        on_delete=django.db.models.deletion.CASCADE,
                        related_name="solicitud_verificacion",
                        to=settings.AUTH_USER_MODEL,
                    ),
                ),
                ("nombre",   models.CharField(max_length=100, verbose_name="Nombre")),
                ("apellido", models.CharField(max_length=100, verbose_name="Apellido")),
                ("dni",      models.CharField(max_length=20,  verbose_name="DNI")),
                (
                    "telefono",
                    models.CharField(
                        blank=True,
                        max_length=30,
                        verbose_name="Teléfono",
                    ),
                ),
                (
                    "fecha_solicitud",
                    models.DateTimeField(auto_now_add=True),
                ),
                (
                    "estado",
                    models.CharField(
                        choices=[
                            ("pendiente",  "Pendiente"),
                            ("aprobada",   "Aprobada"),
                            ("rechazada",  "Rechazada"),
                        ],
                        default="pendiente",
                        max_length=20,
                    ),
                ),
                (
                    "notas_admin",
                    models.TextField(
                        blank=True,
                        verbose_name="Notas del admin",
                        help_text="Motivo de rechazo u observaciones para el conductor.",
                    ),
                ),
            ],
            options={
                "verbose_name": "Solicitud de verificación",
                "verbose_name_plural": "Solicitudes de verificación",
                "ordering": ["-fecha_solicitud"],
            },
        ),

    ]
