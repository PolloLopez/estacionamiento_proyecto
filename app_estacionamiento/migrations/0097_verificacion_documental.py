from django.db import migrations, models
import django.db.models.deletion


class Migration(migrations.Migration):

    dependencies = [
        ("app_estacionamiento", "0096_geoloc_flags_precio_subcuadra_domicilio_electronico"),
    ]

    operations = [
        # ── Municipio: flag del módulo ─────────────────────────────────────────
        migrations.AddField(
            model_name="municipio",
            name="modulo_verificacion_documental_activo",
            field=models.BooleanField(
                default=False,
                help_text="Permite al conductor adjuntar documentos de identidad/domicilio/vehículos para verificación formal.",
                verbose_name="Módulo verificación documental activo",
            ),
        ),
        # ── SolicitudVerificacion: aceptación de domicilio electrónico ─────────
        migrations.AddField(
            model_name="solicitudverificacion",
            name="acepta_domicilio_electronico",
            field=models.BooleanField(
                default=False,
                help_text="El conductor declaró su domicilio electrónico como válido para notificaciones oficiales.",
                verbose_name="Acepta domicilio electrónico",
            ),
        ),
        # ── ConfigDocumentoVerificacion ────────────────────────────────────────
        migrations.CreateModel(
            name="ConfigDocumentoVerificacion",
            fields=[
                ("id", models.BigAutoField(auto_created=True, primary_key=True, serialize=False, verbose_name="ID")),
                ("nombre", models.CharField(
                    max_length=120,
                    verbose_name="Nombre del documento",
                    help_text="Ej: 'DNI (frente)', 'Cédula verde', 'Constancia de domicilio'.",
                )),
                ("tipo_predefinido", models.CharField(
                    choices=[
                        ("dni_frente",   "DNI (frente)"),
                        ("dni_dorso",    "DNI (dorso)"),
                        ("cedula_verde", "Cédula verde / título del vehículo"),
                        ("domicilio",    "Comprobante de domicilio"),
                        ("licencia",     "Licencia de conducir"),
                        ("custom",       "Documento personalizado"),
                    ],
                    default="custom",
                    max_length=30,
                    verbose_name="Tipo predefinido",
                    help_text="Permite identificar el documento en el flujo de verificación.",
                )),
                ("obligatorio", models.BooleanField(
                    default=True,
                    verbose_name="Obligatorio",
                    help_text="Si está marcado, el conductor no puede enviar la solicitud sin adjuntar este documento.",
                )),
                ("orden", models.PositiveSmallIntegerField(
                    default=0,
                    verbose_name="Orden de aparición",
                )),
                ("activo", models.BooleanField(
                    default=True,
                    verbose_name="Activo",
                    help_text="Documentos inactivos no aparecen en el formulario pero se conservan en las solicitudes previas.",
                )),
                ("municipio", models.ForeignKey(
                    on_delete=django.db.models.deletion.CASCADE,
                    related_name="configs_documentos_verificacion",
                    to="app_estacionamiento.municipio",
                )),
            ],
            options={
                "verbose_name": "Configuración de documento de verificación",
                "verbose_name_plural": "Configuraciones de documentos de verificación",
                "ordering": ["orden", "id"],
            },
        ),
        # ── DocumentoVerificacion ──────────────────────────────────────────────
        migrations.CreateModel(
            name="DocumentoVerificacion",
            fields=[
                ("id", models.BigAutoField(auto_created=True, primary_key=True, serialize=False, verbose_name="ID")),
                ("archivo", models.FileField(
                    upload_to="verificacion_documental/",
                    verbose_name="Archivo",
                    help_text="PDF o imagen (JPG/PNG). Máximo 5 MB.",
                )),
                ("subido_en", models.DateTimeField(auto_now_add=True)),
                ("config", models.ForeignKey(
                    on_delete=django.db.models.deletion.PROTECT,
                    related_name="documentos",
                    to="app_estacionamiento.configdocumentoverificacion",
                    verbose_name="Tipo de documento",
                )),
                ("solicitud", models.ForeignKey(
                    on_delete=django.db.models.deletion.CASCADE,
                    related_name="documentos",
                    to="app_estacionamiento.solicitudverificacion",
                )),
            ],
            options={
                "verbose_name": "Documento de verificación",
                "verbose_name_plural": "Documentos de verificación",
                "ordering": ["config__orden", "subido_en"],
            },
        ),
    ]
