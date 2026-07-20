from django.db import migrations, models
import django.db.models.deletion


class Migration(migrations.Migration):

    dependencies = [
        ('app_estacionamiento', '0040_infraccion_motivo_anulacion'),
    ]

    operations = [
        migrations.CreateModel(
            name='DestinatarioInforme',
            fields=[
                ('id', models.BigAutoField(auto_created=True, primary_key=True, serialize=False, verbose_name='ID')),
                ('nombre', models.CharField(max_length=200, verbose_name='Nombre / cargo')),
                ('correo', models.EmailField(verbose_name='Email')),
                ('activo', models.BooleanField(default=True, help_text='Desactivar para excluir sin borrar el registro.')),
                ('creado_en', models.DateTimeField(auto_now_add=True)),
                ('municipio', models.ForeignKey(
                    on_delete=django.db.models.deletion.CASCADE,
                    related_name='destinatarios_informe',
                    to='app_estacionamiento.municipio',
                )),
            ],
            options={
                'verbose_name': 'Destinatario de informe',
                'verbose_name_plural': 'Destinatarios de informes',
                'ordering': ['nombre'],
            },
        ),
        migrations.AddConstraint(
            model_name='destinatarioinforme',
            constraint=models.UniqueConstraint(
                fields=['municipio', 'correo'],
                name='unique_destinatario_municipio',
            ),
        ),
    ]
