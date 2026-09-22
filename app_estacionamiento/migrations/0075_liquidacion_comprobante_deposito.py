from django.db import migrations, models


class Migration(migrations.Migration):

    dependencies = [
        ('app_estacionamiento', '0074_rendicion_notas_admin'),
    ]

    operations = [
        migrations.AddField(
            model_name='liquidacioncomision',
            name='numero_comprobante',
            field=models.CharField(
                blank=True,
                help_text='Número o referencia de la transferencia/pago al vendedor.',
                max_length=100,
            ),
        ),
        migrations.AddField(
            model_name='liquidacioncomision',
            name='comprobante_archivo',
            field=models.FileField(
                blank=True,
                null=True,
                upload_to='comprobantes_deposito/',
                help_text='Archivo del comprobante bancario (imagen o PDF).',
            ),
        ),
    ]
