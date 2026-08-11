"""
Migración 0048: coordenadas GPS en Subcuadra.

Agrega lat y lon (DecimalField, null, blank) para almacenar el centroide
de cada cuadra. Con estas coordenadas, el inspector puede preseleccionar
automáticamente su subcuadra desde verificar.html usando la geolocalización
del navegador, reduciendo errores humanos en la evaluación de exenciones.

Los campos son opcionales: subcuadras sin coordenadas siguen funcionando
con selección manual, igual que antes.
"""
from django.db import migrations, models


class Migration(migrations.Migration):

    dependencies = [
        ("app_estacionamiento", "0047_movimientocaja_mp_payment_id"),
    ]

    operations = [
        migrations.AddField(
            model_name="subcuadra",
            name="lat",
            field=models.DecimalField(
                blank=True,
                decimal_places=6,
                max_digits=9,
                null=True,
                verbose_name="Latitud",
            ),
        ),
        migrations.AddField(
            model_name="subcuadra",
            name="lon",
            field=models.DecimalField(
                blank=True,
                decimal_places=6,
                max_digits=9,
                null=True,
                verbose_name="Longitud",
            ),
        ),
    ]
