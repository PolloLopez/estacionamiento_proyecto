from django.db import migrations, models
import django.db.models.deletion


class Migration(migrations.Migration):

    dependencies = [
        ("app_estacionamiento", "0067_impugnacion_transferenciasaldo"),
    ]

    operations = [
        # ── Nuevos campos en Municipio (facturación de la plataforma) ──────────
        migrations.AddField(
            model_name="municipio",
            name="cuota_mantenimiento_mensual",
            field=models.DecimalField(
                blank=True, decimal_places=2, max_digits=10, null=True,
                verbose_name="Cuota mensual de mantenimiento ($)",
            ),
        ),
        migrations.AddField(
            model_name="municipio",
            name="porcentaje_plataforma",
            field=models.DecimalField(
                blank=True, decimal_places=2, max_digits=5, null=True,
                verbose_name="Porcentaje sobre recaudación (%)",
            ),
        ),
        migrations.AddField(
            model_name="municipio",
            name="dia_cierre_liquidacion",
            field=models.PositiveSmallIntegerField(
                default=1,
                verbose_name="Día de cierre de liquidación",
            ),
        ),
        migrations.AddField(
            model_name="municipio",
            name="concepto_recaudacion",
            field=models.CharField(
                choices=[
                    ("cierre_caja", "Total de cierres de caja (neto municipio)"),
                    ("rendiciones", "Solo rendiciones validadas"),
                    ("manual",      "Monto ingresado manualmente"),
                ],
                default="cierre_caja",
                max_length=20,
                verbose_name="Base de cálculo para el porcentaje",
            ),
        ),

        # ── Nuevo modelo LiquidacionPlataforma ────────────────────────────────
        migrations.CreateModel(
            name="LiquidacionPlataforma",
            fields=[
                ("id", models.BigAutoField(auto_created=True, primary_key=True, serialize=False)),
                ("municipio", models.ForeignKey(
                    on_delete=django.db.models.deletion.PROTECT,
                    related_name="liquidaciones_plataforma",
                    to="app_estacionamiento.municipio",
                    verbose_name="Municipio",
                )),
                ("periodo_inicio",  models.DateField(verbose_name="Inicio del período")),
                ("periodo_fin",     models.DateField(verbose_name="Fin del período")),
                ("recaudacion_base", models.DecimalField(decimal_places=2, default=0, max_digits=12, verbose_name="Recaudación del período")),
                ("monto_fijo",      models.DecimalField(decimal_places=2, default=0, max_digits=10, verbose_name="Monto fijo (mantenimiento)")),
                ("monto_variable",  models.DecimalField(decimal_places=2, default=0, max_digits=10, verbose_name="Monto variable (% recaudación)")),
                ("monto_total",     models.DecimalField(decimal_places=2, default=0, max_digits=10, verbose_name="Total a pagar")),
                ("estado", models.CharField(
                    choices=[
                        ("borrador",            "Borrador"),
                        ("pendiente_pago",      "Pendiente de pago (factura emitida)"),
                        ("comprobante_enviado", "Comprobante enviado por municipio"),
                        ("aprobada",            "Aprobada — pago confirmado"),
                        ("observada",           "Observada — hay consultas pendientes"),
                    ],
                    default="borrador", max_length=30,
                )),
                ("iniciado_por", models.CharField(
                    choices=[("superadmin", "Superadmin"), ("tesorero", "Tesorero")],
                    default="superadmin", max_length=15,
                )),
                ("factura",          models.FileField(blank=True, null=True, upload_to="liquidaciones_plataforma/facturas/", verbose_name="Factura (PDF o imagen)")),
                ("comprobante_pago", models.FileField(blank=True, null=True, upload_to="liquidaciones_plataforma/comprobantes/", verbose_name="Comprobante de transferencia")),
                ("notas_superadmin", models.TextField(blank=True, default="")),
                ("notas_tesorero",   models.TextField(blank=True, default="")),
                ("creado_en",      models.DateTimeField(auto_now_add=True)),
                ("actualizado_en", models.DateTimeField(auto_now=True)),
                ("aprobada_en",    models.DateTimeField(blank=True, null=True)),
            ],
            options={
                "ordering": ["-periodo_fin", "-creado_en"],
                "verbose_name": "Liquidación de plataforma",
                "verbose_name_plural": "Liquidaciones de plataforma",
            },
        ),
    ]
