from django.conf import settings
from django.db import migrations, models
import django.db.models.deletion


class Migration(migrations.Migration):

    dependencies = [
        ("app_estacionamiento", "0069_modulomunicipio_porcentaje"),
    ]

    operations = [
        migrations.CreateModel(
            name="SugerenciaMejora",
            fields=[
                ("id", models.BigAutoField(auto_created=True, primary_key=True, serialize=False, verbose_name="ID")),
                ("rol_usuario", models.CharField(choices=[("conductor","Conductor"),("inspector","Inspector"),("vendedor","Vendedor"),("admin","Admin municipio"),("tesorero","Tesorero"),("superadmin","Superadmin")], default="conductor", max_length=20)),
                ("area", models.CharField(choices=[("conductor","Experiencia del conductor"),("inspector","Herramientas del inspector"),("vendedor","Flujo de cobro / vendedor"),("admin","Panel de administración"),("tesorero","Tesorería y liquidaciones"),("general","General / otro")], default="general", max_length=20)),
                ("criticidad", models.CharField(choices=[("cosmetico","🎨 Cosmético — cambio visual o de texto"),("funcional","⚙️ Funcional — algo no funciona como debería"),("bloqueante","🚨 Bloqueante — detiene o rompe un proceso")], default="funcional", max_length=15)),
                ("titulo", models.CharField(max_length=200)),
                ("descripcion", models.TextField()),
                ("estado", models.CharField(choices=[("recibida","Recibida"),("en_revision","En revisión"),("implementada","Implementada"),("descartada","Descartada")], default="recibida", max_length=20)),
                ("respuesta", models.TextField(blank=True, default="", help_text="Respuesta o comentario del superadmin al usuario.")),
                ("notificado", models.BooleanField(default=True, help_text="False cuando el superadmin cambió el estado y el usuario todavía no lo vio.")),
                ("creado_en", models.DateTimeField(auto_now_add=True)),
                ("actualizado_en", models.DateTimeField(auto_now=True)),
                ("usuario", models.ForeignKey(blank=True, null=True, on_delete=django.db.models.deletion.SET_NULL, related_name="sugerencias", to=settings.AUTH_USER_MODEL)),
                ("municipio", models.ForeignKey(blank=True, null=True, on_delete=django.db.models.deletion.CASCADE, related_name="sugerencias", to="app_estacionamiento.municipio", help_text="Municipio del usuario al enviar la sugerencia.")),
            ],
            options={
                "verbose_name": "Sugerencia de mejora",
                "verbose_name_plural": "Sugerencias de mejora",
                "ordering": ["-creado_en"],
            },
        ),
        migrations.CreateModel(
            name="SolicitudEliminacionCuenta",
            fields=[
                ("id", models.BigAutoField(auto_created=True, primary_key=True, serialize=False, verbose_name="ID")),
                ("estado", models.CharField(choices=[("pendiente","Pendiente de confirmación"),("completada","Cuenta eliminada"),("cancelada","Cancelada por el usuario")], default="pendiente", max_length=15)),
                ("motivo", models.TextField(blank=True, default="")),
                ("creado_en", models.DateTimeField(auto_now_add=True)),
                ("resuelto_en", models.DateTimeField(blank=True, null=True)),
                ("usuario", models.OneToOneField(on_delete=django.db.models.deletion.CASCADE, related_name="solicitud_eliminacion", to=settings.AUTH_USER_MODEL)),
            ],
            options={
                "verbose_name": "Solicitud de eliminación de cuenta",
                "verbose_name_plural": "Solicitudes de eliminación de cuenta",
            },
        ),
    ]
