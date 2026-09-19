from django.db import migrations, models


class Migration(migrations.Migration):

    dependencies = [
        ('app_estacionamiento', '0080_infraccion_gps_lat_gps_lon_gps_acc'),
    ]

    operations = [
        # Campo tipo en Notificacion (vacío = sin clasificar, compatible con registros existentes)
        migrations.AddField(
            model_name='notificacion',
            name='tipo',
            field=models.CharField(
                blank=True, default='', max_length=20,
                choices=[
                    ('verificacion', 'Verificación de identidad'),
                    ('exencion',     'Exención'),
                    ('sugerencia',   'Sugerencia'),
                ],
            ),
        ),
        # Preferencias de notificaciones del conductor en Usuario
        migrations.AddField(
            model_name='usuario',
            name='notif_verificacion',
            field=models.BooleanField(
                default=True,
                verbose_name='Notificaciones de verificación de identidad',
                help_text='Avisa cuando el admin aprueba o rechaza tu solicitud de verificación.',
            ),
        ),
        migrations.AddField(
            model_name='usuario',
            name='notif_exencion',
            field=models.BooleanField(
                default=True,
                verbose_name='Notificaciones de exención',
                help_text='Avisa cuando el admin aprueba o rechaza tu solicitud de exención.',
            ),
        ),
        migrations.AddField(
            model_name='usuario',
            name='notif_sugerencia',
            field=models.BooleanField(
                default=True,
                verbose_name='Notificaciones de sugerencias',
                help_text='Avisa cuando el superadmin actualiza el estado de una sugerencia tuya.',
            ),
        ),
    ]
