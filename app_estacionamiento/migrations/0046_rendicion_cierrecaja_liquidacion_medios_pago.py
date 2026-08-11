"""
Migración 0046: rediseño del módulo de rendiciones y medios de pago.

Cambios:
- MovimientoCaja.medio_pago: agrega transferencia, débito, crédito, QR
- CierreCaja: agrega desglose por medio de pago + FK a Rendicion
- Rendicion: elimina total_comisiones, agrega comprobante_archivo
- LiquidacionComision: agrega factura_presentada y factura_archivo
"""
import django.db.models.deletion
from django.conf import settings
from django.db import migrations, models


class Migration(migrations.Migration):

    dependencies = [
        ('app_estacionamiento', '0045_superadmin_y_modulos_municipio'),
    ]

    operations = [

        # ── MovimientoCaja: expandir medios de pago ───────────────────────
        migrations.AlterField(
            model_name='movimientocaja',
            name='medio_pago',
            field=models.CharField(
                choices=[
                    ('efectivo',      'Efectivo'),
                    ('transferencia', 'Transferencia bancaria'),
                    ('debito',        'Débito'),
                    ('credito',       'Crédito'),
                    ('qr',            'QR'),
                    ('mercadopago',   'MercadoPago'),
                ],
                default='efectivo',
                max_length=20,
                verbose_name='Medio de pago',
            ),
        ),

        # ── CierreCaja: desglose por medio de pago ───────────────────────
        migrations.AddField(
            model_name='cierrecaja',
            name='total_efectivo',
            field=models.DecimalField(
                decimal_places=2, default=0,
                help_text='Total cobrado en efectivo.',
                max_digits=12,
            ),
        ),
        migrations.AddField(
            model_name='cierrecaja',
            name='total_transferencia',
            field=models.DecimalField(
                decimal_places=2, default=0,
                help_text='Total cobrado por transferencia bancaria.',
                max_digits=12,
            ),
        ),
        migrations.AddField(
            model_name='cierrecaja',
            name='total_digital',
            field=models.DecimalField(
                decimal_places=2, default=0,
                help_text='Total cobrado por débito/crédito/QR (va directo a tesorería).',
                max_digits=12,
            ),
        ),

        # ── CierreCaja: FK a Rendicion ────────────────────────────────────
        migrations.AddField(
            model_name='cierrecaja',
            name='rendicion',
            field=models.ForeignKey(
                blank=True,
                help_text='Rendición en la que se incluyó este cierre. Null = pendiente de rendir.',
                null=True,
                on_delete=django.db.models.deletion.SET_NULL,
                related_name='cierres',
                to='app_estacionamiento.rendicion',
            ),
        ),

        # ── Rendicion: eliminar total_comisiones ──────────────────────────
        migrations.RemoveField(
            model_name='rendicion',
            name='total_comisiones',
        ),

        # ── Rendicion: actualizar help_texts ─────────────────────────────
        migrations.AlterField(
            model_name='rendicion',
            name='total_digital',
            field=models.DecimalField(
                decimal_places=2, default=0,
                help_text='Total no efectivo (transferencia + débito + crédito + QR) de los cierres incluidos.',
                max_digits=12,
            ),
        ),
        migrations.AlterField(
            model_name='rendicion',
            name='total_neto',
            field=models.DecimalField(
                decimal_places=2, default=0,
                help_text='Total a rendir = efectivo + digital. Las comisiones las gestiona tesorería aparte.',
                max_digits=12,
            ),
        ),

        # ── Rendicion: comprobante de transferencia ───────────────────────
        migrations.AddField(
            model_name='rendicion',
            name='comprobante_archivo',
            field=models.FileField(
                blank=True,
                help_text='Comprobante de transferencia bancaria (si aplica).',
                null=True,
                upload_to='comprobantes_rendicion/',
            ),
        ),

        # ── LiquidacionComision: factura del vendedor ─────────────────────
        migrations.AddField(
            model_name='liquidacioncomision',
            name='factura_presentada',
            field=models.BooleanField(
                default=False,
                help_text='El vendedor presentó factura por sus comisiones.',
            ),
        ),
        migrations.AddField(
            model_name='liquidacioncomision',
            name='factura_archivo',
            field=models.FileField(
                blank=True,
                help_text='Archivo de la factura presentada.',
                null=True,
                upload_to='facturas_comision/',
            ),
        ),
    ]
