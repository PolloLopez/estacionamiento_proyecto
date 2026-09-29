import django.db.models.deletion
from django.conf import settings
from django.db import migrations, models


class Migration(migrations.Migration):

    dependencies = [
        ("app_estacionamiento", "0098_selector_manual_conductor"),
    ]

    operations = [
        # ── Municipio: minutos de alerta antes del vencimiento ────────────────
        migrations.AddField(
            model_name="municipio",
            name="minutos_alerta_push",
            field=models.PositiveIntegerField(
                default=10,
                verbose_name="Minutos de alerta antes del vencimiento (push)",
                help_text=(
                    "Cuántos minutos antes del vencimiento del estacionamiento se envía "
                    "la notificación push al conductor. 0 = desactivado."
                ),
            ),
        ),

        # ── Infraccion: trazabilidad del acuse de anulación ───────────────────
        migrations.AddField(
            model_name="infraccion",
            name="notificado_anulacion_en",
            field=models.DateTimeField(
                null=True,
                blank=True,
                verbose_name="Conductor notificado de anulación el",
            ),
        ),
        migrations.AddField(
            model_name="infraccion",
            name="notificado_anulacion_ip",
            field=models.GenericIPAddressField(
                null=True,
                blank=True,
                verbose_name="IP del acuse de anulación",
            ),
        ),

        # ── SuscripcionPush: suscripciones Web Push por usuario ───────────────
        migrations.CreateModel(
            name="SuscripcionPush",
            fields=[
                ("id", models.BigAutoField(auto_created=True, primary_key=True, serialize=False, verbose_name="ID")),
                (
                    "usuario",
                    models.ForeignKey(
                        on_delete=django.db.models.deletion.CASCADE,
                        related_name="suscripciones_push",
                        to=settings.AUTH_USER_MODEL,
                    ),
                ),
                ("endpoint", models.TextField(unique=True)),
                ("p256dh",   models.TextField()),
                ("auth",     models.TextField()),
                ("creado_en", models.DateTimeField(auto_now_add=True)),
            ],
            options={
                "verbose_name":        "Suscripción push",
                "verbose_name_plural": "Suscripciones push",
            },
        ),
    ]
