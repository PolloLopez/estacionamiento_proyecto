from django.db import migrations, models


class Migration(migrations.Migration):

    dependencies = [
        ("app_estacionamiento", "0095_subcuadra_intersecciones"),
    ]

    operations = [
        # ── UsuarioCustom: domicilio electrónico ───────────────────────────────
        migrations.AddField(
            model_name="usuario",
            name="domicilio_electronico",
            field=models.EmailField(
                blank=True,
                default="",
                help_text="Email declarado para notificaciones oficiales del municipio (distinto al correo de acceso).",
                verbose_name="Domicilio electrónico",
            ),
        ),
        # ── Municipio: flags de geolocalización por rol ────────────────────────
        migrations.AddField(
            model_name="municipio",
            name="geoloc_conductor_activa",
            field=models.BooleanField(
                default=False,
                help_text="Si está habilitado, se captura y guarda la ubicación GPS del conductor al estacionar.",
                verbose_name="Geolocalización del conductor activa",
            ),
        ),
        migrations.AddField(
            model_name="municipio",
            name="geoloc_inspector_activa",
            field=models.BooleanField(
                default=False,
                help_text="Si está habilitado, se captura y guarda la ubicación GPS del inspector al infraccionar.",
                verbose_name="Geolocalización del inspector activa",
            ),
        ),
        # ── Subcuadra: precio custom por hora ──────────────────────────────────
        migrations.AddField(
            model_name="subcuadra",
            name="precio_por_hora_custom",
            field=models.DecimalField(
                blank=True,
                decimal_places=2,
                help_text="Si se configura, reemplaza la tarifa general del municipio para esta subcuadra.",
                max_digits=10,
                null=True,
                verbose_name="Precio/hora custom",
            ),
        ),
        # ── Estacionamiento: coords GPS del conductor ──────────────────────────
        migrations.AddField(
            model_name="estacionamiento",
            name="gps_lat",
            field=models.DecimalField(
                blank=True,
                decimal_places=6,
                max_digits=9,
                null=True,
                verbose_name="Latitud GPS (conductor)",
            ),
        ),
        migrations.AddField(
            model_name="estacionamiento",
            name="gps_lon",
            field=models.DecimalField(
                blank=True,
                decimal_places=6,
                max_digits=9,
                null=True,
                verbose_name="Longitud GPS (conductor)",
            ),
        ),
    ]
