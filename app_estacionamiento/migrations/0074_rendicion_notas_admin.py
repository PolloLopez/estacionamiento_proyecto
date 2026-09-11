from django.db import migrations, models


class Migration(migrations.Migration):
    """
    Agrega el campo notas_admin a Rendicion para que el admin pueda
    responder a una observación del tesorero y reenviar la rendición.
    """

    dependencies = [
        ('app_estacionamiento', '0073_usuario_puede_cobrar_infraccion'),
    ]

    operations = [
        migrations.AddField(
            model_name='rendicion',
            name='notas_admin',
            field=models.TextField(blank=True, verbose_name='Respuesta del admin'),
        ),
    ]
