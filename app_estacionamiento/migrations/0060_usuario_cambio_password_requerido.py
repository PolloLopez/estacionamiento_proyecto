# Migración manual — 2026-09-01
# Agrega cambio_password_requerido (BooleanField) en Usuario.
# Cuando el admin establece una contraseña temporal, este flag
# fuerza al usuario a cambiarla en su próximo login.

from django.db import migrations, models


class Migration(migrations.Migration):

    dependencies = [
        ('app_estacionamiento', '0059_usuario_puede_vender_abono_domicilio'),
    ]

    operations = [
        migrations.AddField(
            model_name='usuario',
            name='cambio_password_requerido',
            field=models.BooleanField(
                default=False,
                verbose_name='Debe cambiar contraseña al próximo login',
                help_text='El admin lo activa al establecer una contraseña temporal.',
            ),
        ),
    ]
