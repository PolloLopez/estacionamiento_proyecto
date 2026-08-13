# Generated manually — agrega el modelo PagoPublico para pagos anónimos vía MP

from django.db import migrations, models
import django.db.models.deletion


class Migration(migrations.Migration):

    dependencies = [
        ("app_estacionamiento", "0050_vehiculo_vigencia_exencion_verificada"),
    ]

    operations = [
        migrations.CreateModel(
            name="PagoPublico",
            fields=[
                ("id", models.BigAutoField(auto_created=True, primary_key=True, serialize=False, verbose_name="ID")),
                ("tipo",             models.CharField(choices=[("infraccion", "Infracción"), ("estacionamiento", "Estacionamiento"), ("abono", "Abono mensual")], max_length=20)),
                ("estado",           models.CharField(choices=[("pendiente", "Pendiente de pago"), ("aprobado", "Pagado"), ("fallido", "Fallido o cancelado")], default="pendiente", max_length=20)),
                ("patente",          models.CharField(max_length=10, verbose_name="Patente del vehículo")),
                ("monto",            models.DecimalField(decimal_places=2, max_digits=10)),
                ("email_contacto",   models.CharField(blank=True, default="", max_length=254, verbose_name="Email para comprobante (opcional)")),
                ("mp_preference_id", models.CharField(blank=True, default="", max_length=100, verbose_name="ID preferencia MercadoPago")),
                ("mp_payment_id",    models.CharField(blank=True, max_length=50, null=True, unique=True, verbose_name="ID pago MercadoPago")),
                ("creado_en",        models.DateTimeField(auto_now_add=True)),
                ("procesado_en",     models.DateTimeField(blank=True, null=True, verbose_name="Fecha de procesamiento por MP")),
                ("duracion_horas",   models.DecimalField(blank=True, decimal_places=1, max_digits=4, null=True)),
                ("mes_abono",        models.DateField(blank=True, null=True, verbose_name="Mes del abono (primer día)")),
                ("municipio",        models.ForeignKey(on_delete=django.db.models.deletion.PROTECT, related_name="pagos_publicos", to="app_estacionamiento.municipio")),
                ("infraccion",       models.ForeignKey(blank=True, null=True, on_delete=django.db.models.deletion.SET_NULL, related_name="pagos_publicos", to="app_estacionamiento.infraccion")),
                ("estacionamiento",  models.ForeignKey(blank=True, null=True, on_delete=django.db.models.deletion.SET_NULL, related_name="pagos_publicos", to="app_estacionamiento.estacionamiento")),
                ("abono",            models.ForeignKey(blank=True, null=True, on_delete=django.db.models.deletion.SET_NULL, related_name="pagos_publicos", to="app_estacionamiento.abonoMensual")),
                ("subcuadra",        models.ForeignKey(blank=True, null=True, on_delete=django.db.models.deletion.SET_NULL, to="app_estacionamiento.subcuadra")),
            ],
            options={
                "verbose_name": "Pago público",
                "verbose_name_plural": "Pagos públicos",
                "ordering": ["-creado_en"],
            },
        ),
        migrations.AddIndex(
            model_name="pagopublico",
            index=models.Index(fields=["patente", "estado"], name="idx_pagopub_patente_estado"),
        ),
        migrations.AddIndex(
            model_name="pagopublico",
            index=models.Index(fields=["mp_payment_id"], name="idx_pagopub_payment_id"),
        ),
    ]
