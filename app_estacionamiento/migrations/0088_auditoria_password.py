from django.db import migrations, models
import django.db.models.deletion


class Migration(migrations.Migration):

    dependencies = [
        ('app_estacionamiento', '0087_municipio_puede_gestionar_subcuadras'),
    ]

    operations = [
        migrations.CreateModel(
            name='AuditoriaPassword',
            fields=[
                ('id', models.BigAutoField(auto_created=True, primary_key=True, serialize=False, verbose_name='ID')),
                ('tipo', models.CharField(
                    max_length=20,
                    choices=[('dni', 'Reset al DNI'), ('personalizada', 'Contraseña personalizada')],
                    verbose_name='Tipo de cambio',
                )),
                ('ip', models.GenericIPAddressField(
                    null=True, blank=True,
                    verbose_name='IP del admin',
                )),
                ('fecha', models.DateTimeField(auto_now_add=True)),
                ('admin', models.ForeignKey(
                    null=True,
                    on_delete=django.db.models.deletion.SET_NULL,
                    related_name='auditorias_password_realizadas',
                    to='app_estacionamiento.usuario',
                    verbose_name='Admin que realizó el cambio',
                )),
                ('conductor', models.ForeignKey(
                    on_delete=django.db.models.deletion.CASCADE,
                    related_name='auditorias_password_recibidas',
                    to='app_estacionamiento.usuario',
                    verbose_name='Conductor afectado',
                )),
                ('municipio', models.ForeignKey(
                    null=True,
                    on_delete=django.db.models.deletion.SET_NULL,
                    related_name='auditorias_password',
                    to='app_estacionamiento.municipio',
                )),
            ],
            options={
                'verbose_name': 'Auditoría de contraseña',
                'verbose_name_plural': 'Auditorías de contraseñas',
                'ordering': ['-fecha'],
            },
        ),
    ]
