from django.conf import settings
from django.db import migrations, models
import django.db.models.deletion


class Migration(migrations.Migration):

    dependencies = [
        ("app_estacionamiento", "0066_municipio_tv_estadisticas_cobrador"),
    ]

    operations = [
        migrations.CreateModel(
            name="Impugnacion",
            fields=[
                ("id", models.BigAutoField(auto_created=True, primary_key=True, serialize=False, verbose_name="ID")),
                ("motivo",      models.TextField(verbose_name="Motivo de la impugnación")),
                ("evidencia",   models.ImageField(blank=True, null=True, upload_to="impugnaciones/", verbose_name="Evidencia fotográfica")),
                ("estado",      models.CharField(max_length=20, choices=[
                    ("pendiente", "Pendiente de revisión"),
                    ("aceptada",  "Aceptada — infracción anulada"),
                    ("rechazada", "Rechazada"),
                ], default="pendiente")),
                ("resolucion",  models.TextField(blank=True, default="", verbose_name="Resolución / motivo del admin")),
                ("creado_en",   models.DateTimeField(auto_now_add=True)),
                ("resuelto_en", models.DateTimeField(blank=True, null=True)),
                ("infraccion",  models.ForeignKey(
                    on_delete=django.db.models.deletion.PROTECT,
                    related_name="impugnaciones",
                    to="app_estacionamiento.infraccion",
                )),
                ("conductor",   models.ForeignKey(
                    on_delete=django.db.models.deletion.PROTECT,
                    related_name="impugnaciones",
                    to=settings.AUTH_USER_MODEL,
                )),
                ("municipio",   models.ForeignKey(
                    on_delete=django.db.models.deletion.PROTECT,
                    related_name="impugnaciones",
                    to="app_estacionamiento.municipio",
                )),
                ("resuelto_por", models.ForeignKey(
                    blank=True, null=True,
                    on_delete=django.db.models.deletion.SET_NULL,
                    related_name="impugnaciones_resueltas",
                    to=settings.AUTH_USER_MODEL,
                )),
            ],
            options={"ordering": ["-creado_en"]},
        ),
        migrations.CreateModel(
            name="TransferenciaSaldo",
            fields=[
                ("id", models.BigAutoField(auto_created=True, primary_key=True, serialize=False, verbose_name="ID")),
                ("monto",         models.DecimalField(max_digits=10, decimal_places=2)),
                ("estado",        models.CharField(max_length=20, choices=[
                    ("pendiente",  "Esperando respuesta"),
                    ("aceptada",   "Completada"),
                    ("rechazada",  "Rechazada por el receptor"),
                    ("expirada",   "Expiró sin respuesta"),
                    ("cancelada",  "Cancelada por el emisor"),
                ], default="pendiente")),
                ("creado_en",     models.DateTimeField(auto_now_add=True)),
                ("expira_en",     models.DateTimeField()),
                ("respondido_en", models.DateTimeField(blank=True, null=True)),
                ("emisor",    models.ForeignKey(
                    on_delete=django.db.models.deletion.PROTECT,
                    related_name="transferencias_enviadas",
                    to=settings.AUTH_USER_MODEL,
                )),
                ("receptor",  models.ForeignKey(
                    on_delete=django.db.models.deletion.PROTECT,
                    related_name="transferencias_recibidas",
                    to=settings.AUTH_USER_MODEL,
                )),
                ("municipio", models.ForeignKey(
                    on_delete=django.db.models.deletion.PROTECT,
                    related_name="transferencias_saldo",
                    to="app_estacionamiento.municipio",
                )),
            ],
            options={"ordering": ["-creado_en"]},
        ),
    ]
