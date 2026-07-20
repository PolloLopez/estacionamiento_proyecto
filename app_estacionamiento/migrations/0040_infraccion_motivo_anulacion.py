from django.db import migrations, models


class Migration(migrations.Migration):

    dependencies = [
        ('app_estacionamiento', '0039_abonoMensual_saldo'),
    ]

    operations = [
        migrations.AddField(
            model_name='infraccion',
            name='motivo_anulacion',
            field=models.TextField(blank=True, default=''),
        ),
    ]
