from django.db import migrations, models


class Migration(migrations.Migration):

    dependencies = [
        ("app_estacionamiento", "0033_tarifa_monto_infraccion"),
    ]

    operations = [
        migrations.AddField(
            model_name="usuario",
            name="telefono",
            field=models.CharField(blank=True, default="", max_length=30, verbose_name="Teléfono de contacto"),
        ),
        migrations.AddField(
            model_name="usuario",
            name="numero_dni",
            field=models.CharField(blank=True, default="", max_length=20, verbose_name="Número de DNI"),
        ),
        migrations.AddField(
            model_name="usuario",
            name="numero_legajo",
            field=models.CharField(blank=True, default="", help_text="Opcional", max_length=30, verbose_name="Número de legajo"),
        ),
        migrations.AddField(
            model_name="usuario",
            name="nombre_propietario",
            field=models.CharField(blank=True, default="", max_length=200, verbose_name="Nombre del propietario"),
        ),
        migrations.AddField(
            model_name="usuario",
            name="documento_cuil",
            field=models.CharField(blank=True, default="", max_length=20, verbose_name="Documento / CUIL"),
        ),
        migrations.AddField(
            model_name="usuario",
            name="horario_atencion",
            field=models.CharField(blank=True, default="", help_text="Ej: Lun-Vie 9-18, Sáb 9-13", max_length=200, verbose_name="Horarios de atención"),
        ),
    ]
