"""
Migración 0047: idempotencia MP con campo dedicado en MovimientoCaja.

Agrega mp_payment_id (CharField, null, unique) para verificar que un pago de
MercadoPago no se acredite dos veces, reemplazando la búsqueda por texto
(descripcion__contains="MP:...") que era frágil ante cambios de formato.
"""
from django.db import migrations, models


class Migration(migrations.Migration):

    dependencies = [
        ("app_estacionamiento", "0046_rendicion_cierrecaja_liquidacion_medios_pago"),
    ]

    operations = [
        migrations.AddField(
            model_name="movimientocaja",
            name="mp_payment_id",
            field=models.CharField(
                blank=True,
                help_text="ID del pago en MercadoPago. Garantiza idempotencia: no se puede acreditar el mismo payment_id dos veces.",
                max_length=50,
                null=True,
                unique=True,
                verbose_name="ID de pago MercadoPago",
            ),
        ),
    ]
